import re
import socket
import ipaddress
from typing import Dict, Any, Tuple, Optional
from urllib.parse import urlparse, urljoin
import requests
from requests.adapters import HTTPAdapter
from urllib3.connection import HTTPConnection, HTTPSConnection
from urllib3.connectionpool import HTTPConnectionPool, HTTPSConnectionPool
from bs4 import BeautifulSoup

def is_ip_prohibited(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> Tuple[bool, str]:
    """
    Check if an IPv4 or IPv6 address is non-public or dangerous.
    Blocks private, loopback, link-local, reserved, multicast, unspecified,
    CGNAT (100.64.0.0/10), 172.16.0.0/12, 169.254.0.0/16, and IPv6 unique-local (fc00::/7).
    """
    # Standard ipaddress checks
    if ip.is_loopback:
        return True, "Loopback addresses are blocked."
    if ip.is_private:
        return True, "Private network addresses are blocked."
    if ip.is_link_local:
        return True, "Link-local addresses (including cloud metadata) are blocked."
    if ip.is_multicast:
        return True, "Multicast addresses are blocked."
    if ip.is_reserved:
        return True, "Reserved addresses are blocked."
    if ip.is_unspecified:
        return True, "Unspecified addresses (0.0.0.0/::) are blocked."

    # IPv4 specific checks
    if isinstance(ip, ipaddress.IPv4Address):
        # 169.254.0.0/16 (Cloud metadata e.g. AWS/GCP/Azure)
        if ip in ipaddress.IPv4Network("169.254.0.0/16"):
            return True, "Link-local cloud metadata addresses are blocked."
        # 172.16.0.0/12 (Docker / Container networks)
        if ip in ipaddress.IPv4Network("172.16.0.0/12"):
            return True, "Private 172.16.0.0/12 addresses are blocked."
        # 100.64.0.0/10 (Carrier-Grade NAT)
        if ip in ipaddress.IPv4Network("100.64.0.0/10"):
            return True, "Carrier-grade NAT addresses are blocked."
        # 0.0.0.0/8 (Current network)
        if ip in ipaddress.IPv4Network("0.0.0.0/8"):
            return True, "Current network addresses are blocked."

    # IPv6 specific checks
    if isinstance(ip, ipaddress.IPv6Address):
        # Unique Local Address (fc00::/7, covers fc00:: and fd00::)
        if ip in ipaddress.IPv6Network("fc00::/7"):
            return True, "IPv6 unique-local addresses are blocked."
        # Link-local IPv6 (fe80::/10)
        if ip in ipaddress.IPv6Network("fe80::/10"):
            return True, "IPv6 link-local addresses are blocked."
        # IPv4-mapped IPv6 (::ffff:0:0/96)
        if ip.ipv4_mapped:
            return is_ip_prohibited(ip.ipv4_mapped)

    # General global check
    if not ip.is_global:
        return True, "Non-global addresses are blocked."

    return False, ""

def validate_and_resolve_host(hostname: str, port: int) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Resolve hostname to IP address, validating all representations and DNS results.
    Returns (is_valid, resolved_ip, error_message).
    """
    clean_host = hostname.strip().strip("[]").lower()

    # Block common lexical localhost and internal aliases (including 127.0.0.1, 192.168., 10., etc.)
    if clean_host in ("localhost", "0.0.0.0", "127.0.0.1", "::1", "localtest.me") or clean_host.startswith("192.168.") or clean_host.startswith("10.") or clean_host.endswith(".local") or clean_host.endswith(".internal"):
        return False, None, "Safety Restriction: Access to local/private network addresses is blocked."

    # Check if host is direct integer/hex notation (e.g. 2130706433, 0x7f000001, 0177.0.0.1)
    try:
        if clean_host.isdigit():
            # Integer representation of IPv4
            int_val = int(clean_host)
            if 0 <= int_val <= 0xFFFFFFFF:
                ip_obj = ipaddress.IPv4Address(int_val)
                prohibited, reason = is_ip_prohibited(ip_obj)
                if prohibited:
                    return False, None, f"Safety Restriction: {reason}"
                return True, str(ip_obj), None
        elif clean_host.startswith("0x") or clean_host.startswith("0X"):
            int_val = int(clean_host, 16)
            if 0 <= int_val <= 0xFFFFFFFF:
                ip_obj = ipaddress.IPv4Address(int_val)
                prohibited, reason = is_ip_prohibited(ip_obj)
                if prohibited:
                    return False, None, f"Safety Restriction: {reason}"
                return True, str(ip_obj), None
    except Exception:
        pass

    # Check if already a valid IP literal
    try:
        ip_obj = ipaddress.ip_address(clean_host)
        prohibited, reason = is_ip_prohibited(ip_obj)
        if prohibited:
            return False, None, f"Safety Restriction: {reason}"
        return True, str(ip_obj), None
    except ValueError:
        pass  # It is a hostname that requires DNS resolution

    # Resolve hostname via DNS
    try:
        addr_info = socket.getaddrinfo(clean_host, port, family=socket.AF_UNSPEC, type=socket.SOCK_STREAM)
        if not addr_info:
            return False, None, f"Failed to resolve hostname: {hostname}"

        resolved_ips = []
        for entry in addr_info:
            sockaddr = entry[4]
            ip_str = sockaddr[0]
            resolved_ips.append(ip_str)

        # Validate EVERY resolved IP address (critical against dual-homed DNS rebinding)
        for ip_str in resolved_ips:
            try:
                ip_obj = ipaddress.ip_address(ip_str)
                prohibited, reason = is_ip_prohibited(ip_obj)
                if prohibited:
                    return False, None, f"Safety Restriction: Domain resolves to private/prohibited address ({ip_str}). {reason}"
            except ValueError:
                return False, None, f"Invalid IP resolved: {ip_str}"

        # Return the first validated IP
        return True, resolved_ips[0], None
    except socket.gaierror as e:
        return False, None, f"DNS resolution failed for '{hostname}': {str(e)}"
    except Exception as e:
        return False, None, f"Host validation error for '{hostname}': {str(e)}"

class PinningHTTPConnection(HTTPConnection):
    """HTTPConnection that connects directly to pre-validated IP while preserving Host header."""
    dest_ip = None
    def _new_conn(self):
        return socket.create_connection((self.dest_ip, self.port), self.timeout, self.source_address)

class PinningHTTPSConnection(HTTPSConnection):
    """HTTPSConnection that connects directly to pre-validated IP while preserving SNI and TLS cert validation."""
    dest_ip = None
    def _new_conn(self):
        # Connect socket directly to validated IP (prevents DNS rebinding during second resolve)
        sock = socket.create_connection((self.dest_ip, self.port), self.timeout, self.source_address)
        # Wrap socket using original hostname for SNI and full certificate verification
        return self._connect_tls_proxy(self.hostname, sock) if getattr(self, "_connect_tls_proxy", None) else sock

class PinningAdapter(HTTPAdapter):
    """Custom requests HTTPAdapter that binds to pre-validated IP to eliminate DNS rebinding."""
    def __init__(self, dest_ip: str, *args, **kwargs):
        self.dest_ip = dest_ip
        super().__init__(*args, **kwargs)

    def init_poolmanager(self, *args, **kwargs):
        dest_ip = self.dest_ip
        class BoundHTTPConnectionPool(HTTPConnectionPool):
            ConnectionCls = type("BoundHTTPConn", (PinningHTTPConnection,), {"dest_ip": dest_ip})
        class BoundHTTPSConnectionPool(HTTPSConnectionPool):
            ConnectionCls = type("BoundHTTPSConn", (PinningHTTPSConnection,), {"dest_ip": dest_ip})

        super().init_poolmanager(*args, **kwargs)
        self.poolmanager.pool_classes_by_scheme["http"] = BoundHTTPConnectionPool
        self.poolmanager.pool_classes_by_scheme["https"] = BoundHTTPSConnectionPool

def extract_website_content(url: str, max_chars: int = 4000, max_redirects: int = 4) -> Dict[str, Any]:
    """
    Safely extract readable text and metadata from a public website URL.
    Hardened against SSRF, DNS rebinding, redirect attacks, and IPv4/IPv6 private ranges.
    Preserves TLS certificate verification.
    """
    current_url = url.strip()
    redirect_count = 0

    while True:
        # 1. Scheme Check (strictly HTTP / HTTPS)
        parsed = urlparse(current_url)
        if parsed.scheme.lower() not in ("http", "https"):
            return {
                "success": False,
                "url": current_url,
                "error": "Invalid URL scheme. Only HTTP and HTTPS URLs are permitted.",
                "title": "",
                "content": ""
            }

        hostname = parsed.hostname
        if not hostname:
            return {
                "success": False,
                "url": current_url,
                "error": "Invalid URL: missing hostname.",
                "title": "",
                "content": ""
            }

        default_port = 443 if parsed.scheme.lower() == "https" else 80
        port = parsed.port or default_port

        # 2. DNS Resolution & Comprehensive IP Validation
        is_valid, dest_ip, err_msg = validate_and_resolve_host(hostname, port)
        if not is_valid:
            return {
                "success": False,
                "url": current_url,
                "error": err_msg or "Safety Restriction: Access to this address is blocked.",
                "title": "",
                "content": ""
            }

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }

        # 3. HTTP Request without automatic redirects + DNS-rebinding protection adapter
        session = requests.Session()
        session.mount(f"{parsed.scheme}://", PinningAdapter(dest_ip=dest_ip))

        try:
            response = session.get(
                current_url,
                headers=headers,
                timeout=10,
                allow_redirects=False,
                verify=True  # TLS certificate and hostname verification preserved
            )

            # 4. Handle HTTP Redirects safely
            if response.is_redirect or response.status_code in (301, 302, 303, 307, 308):
                redirect_count += 1
                if redirect_count > max_redirects:
                    return {
                        "success": False,
                        "url": current_url,
                        "error": "Too many HTTP redirects encountered.",
                        "title": "",
                        "content": ""
                    }

                location = response.headers.get("Location")
                if not location:
                    return {
                        "success": False,
                        "url": current_url,
                        "error": "Redirect response missing Location header.",
                        "title": "",
                        "content": ""
                    }

                # Resolve relative redirect URLs against current URL
                redirected_url = urljoin(current_url, location)
                current_url = redirected_url
                continue  # Re-run full validation on redirect destination

            response.raise_for_status()

            # 5. Parse Content with BeautifulSoup
            soup = BeautifulSoup(response.text, "html.parser")
            for element in soup(["script", "style", "nav", "footer", "header", "noscript", "svg", "form"]):
                element.decompose()

            title = soup.title.string.strip() if soup.title and soup.title.string else parsed.netloc

            text = soup.get_text(separator="\n")
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            cleaned_text = "\n".join(lines)

            if len(cleaned_text) > max_chars:
                cleaned_text = cleaned_text[:max_chars] + f"\n\n... [Content truncated at {max_chars} characters]"

            return {
                "success": True,
                "url": current_url,
                "title": title,
                "content": cleaned_text,
                "char_count": len(cleaned_text),
                "error": None
            }

        except requests.exceptions.SSLError as e:
            return {
                "success": False,
                "url": current_url,
                "error": f"TLS/SSL certificate verification failed: {str(e)}",
                "title": "",
                "content": ""
            }
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "url": current_url,
                "error": "Request timed out while connecting to the website.",
                "title": "",
                "content": ""
            }
        except Exception as e:
            return {
                "success": False,
                "url": current_url,
                "error": f"Failed to extract content: {str(e)}",
                "title": "",
                "content": ""
            }
        finally:
            session.close()


