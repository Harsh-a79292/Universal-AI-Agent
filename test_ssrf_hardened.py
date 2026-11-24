"""
Comprehensive Hardened SSRF Test Suite
Tests:
- 127.0.0.1
- 10.0.0.1
- 172.16.0.1
- 172.31.255.254
- 192.168.1.1
- 169.254.169.254 (Cloud metadata)
- ::1 (IPv6 loopback)
- fc00::1 (IPv6 unique-local)
- fe80::1 (IPv6 link-local)
- Decimal and hexadecimal localhost representations
- Public hostname resolving to a private IP (DNS rebinding)
- Public URL redirecting to localhost
- Public URL redirecting to a private IPv6 address
- Normal public HTTP/HTTPS URLs (structure/interface compatibility)
"""
import sys
import os
import socket
from unittest.mock import patch, MagicMock
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tools.web_extractor import extract_website_content, is_ip_prohibited, validate_and_resolve_host
import ipaddress

PASS = "✅ PASS"
FAIL = "❌ FAIL"
results = []

def run_test(name, fn):
    try:
        msg = fn()
        results.append((PASS, name, msg or ""))
    except Exception as e:
        results.append((FAIL, name, str(e)))

print("\n" + "="*60)
print("SSRF HARDENING TEST SUITE")
print("="*60)

# 1. 127.0.0.1 (IPv4 Loopback)
def test_127_0_0_1():
    r = extract_website_content("http://127.0.0.1:8080/secret")
    assert not r["success"], "Should block 127.0.0.1"
    assert "blocked" in r["error"].lower() or "safety" in r["error"].lower()
    return f"Blocked: {r['error']}"
run_test("SSRF: 127.0.0.1 (Loopback)", test_127_0_0_1)

# 2. 10.0.0.1 (Private Class A)
def test_10_0_0_1():
    r = extract_website_content("http://10.0.0.1/admin")
    assert not r["success"], "Should block 10.0.0.1"
    assert "blocked" in r["error"].lower() or "safety" in r["error"].lower()
    return f"Blocked: {r['error']}"
run_test("SSRF: 10.0.0.1 (Private 10/8)", test_10_0_0_1)

# 3. 172.16.0.1 (Private Class B start)
def test_172_16_0_1():
    r = extract_website_content("http://172.16.0.1/api")
    assert not r["success"], "Should block 172.16.0.1"
    assert "blocked" in r["error"].lower() or "safety" in r["error"].lower()
    return f"Blocked: {r['error']}"
run_test("SSRF: 172.16.0.1 (Private 172.16/12 start)", test_172_16_0_1)

# 4. 172.31.255.254 (Private Class B end)
def test_172_31_255_254():
    r = extract_website_content("http://172.31.255.254:5000")
    assert not r["success"], "Should block 172.31.255.254"
    assert "blocked" in r["error"].lower() or "safety" in r["error"].lower()
    return f"Blocked: {r['error']}"
run_test("SSRF: 172.31.255.254 (Private 172.16/12 end)", test_172_31_255_254)

# 5. 192.168.1.1 (Private Class C)
def test_192_168_1_1():
    r = extract_website_content("http://192.168.1.1/router")
    assert not r["success"], "Should block 192.168.1.1"
    assert "blocked" in r["error"].lower() or "safety" in r["error"].lower()
    return f"Blocked: {r['error']}"
run_test("SSRF: 192.168.1.1 (Private 192.168/16)", test_192_168_1_1)

# 6. 169.254.169.254 (Cloud metadata link-local)
def test_169_254_169_254():
    r = extract_website_content("http://169.254.169.254/latest/meta-data/")
    assert not r["success"], "Should block cloud metadata endpoint"
    assert "blocked" in r["error"].lower() or "safety" in r["error"].lower()
    return f"Blocked: {r['error']}"
run_test("SSRF: 169.254.169.254 (Cloud Metadata / Link-Local)", test_169_254_169_254)

# 7. ::1 (IPv6 Loopback)
def test_ipv6_loopback():
    r = extract_website_content("http://[::1]:8080/")
    assert not r["success"], "Should block IPv6 loopback ::1"
    assert "blocked" in r["error"].lower() or "safety" in r["error"].lower()
    return f"Blocked: {r['error']}"
run_test("SSRF: ::1 (IPv6 Loopback)", test_ipv6_loopback)

# 8. fc00::1 (IPv6 Unique Local)
def test_ipv6_unique_local():
    r = extract_website_content("http://[fc00::1]:80/")
    assert not r["success"], "Should block IPv6 unique local fc00::1"
    assert "blocked" in r["error"].lower() or "safety" in r["error"].lower()
    return f"Blocked: {r['error']}"
run_test("SSRF: fc00::1 (IPv6 Unique-Local fc00::/7)", test_ipv6_unique_local)

# 9. fe80::1 (IPv6 Link-Local)
def test_ipv6_link_local():
    r = extract_website_content("http://[fe80::1]/")
    assert not r["success"], "Should block IPv6 link-local fe80::1"
    assert "blocked" in r["error"].lower() or "safety" in r["error"].lower()
    return f"Blocked: {r['error']}"
run_test("SSRF: fe80::1 (IPv6 Link-Local fe80::/10)", test_ipv6_link_local)

# 10. Decimal representation of 127.0.0.1 (http://2130706433)
def test_decimal_ip():
    r = extract_website_content("http://2130706433/")
    assert not r["success"], "Should block integer representation of 127.0.0.1"
    assert "blocked" in r["error"].lower() or "safety" in r["error"].lower()
    return f"Blocked: {r['error']}"
run_test("SSRF: Decimal representation (2130706433 -> 127.0.0.1)", test_decimal_ip)

# 11. Hexadecimal representation of 127.0.0.1 (http://0x7f000001)
def test_hex_ip():
    r = extract_website_content("http://0x7f000001/")
    assert not r["success"], "Should block hexadecimal 0x7f000001"
    assert "blocked" in r["error"].lower() or "safety" in r["error"].lower()
    return f"Blocked: {r['error']}"
run_test("SSRF: Hex representation (0x7f000001 -> 127.0.0.1)", test_hex_ip)

# 12. Public Hostname resolving to a private IP (DNS Rebinding)
def test_dns_rebinding_to_private():
    # Mock DNS resolution of public-looking hostname 'evil-rebinding.com' to 192.168.1.50
    mock_addr = [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('192.168.1.50', 80))]
    with patch("socket.getaddrinfo", return_value=mock_addr):
        r = extract_website_content("http://evil-rebinding.com/steal")
        assert not r["success"], "Should block public domain resolving to private IP"
        assert "private" in r["error"].lower() or "blocked" in r["error"].lower()
    return f"Blocked DNS rebinding to private: {r['error']}"
run_test("SSRF: Public hostname resolving to private IP (DNS Rebinding)", test_dns_rebinding_to_private)

# 13. Public URL redirecting to localhost (302 Redirect Attack)
def test_redirect_to_localhost():
    mock_addr = [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('93.184.216.34', 80))] # example.com
    # First response: 302 redirecting to http://127.0.0.1:8000/internal
    redirect_resp = MagicMock()
    redirect_resp.is_redirect = True
    redirect_resp.status_code = 302
    redirect_resp.headers = {"Location": "http://127.0.0.1:8000/internal"}
    
    with patch("socket.getaddrinfo", return_value=mock_addr):
        with patch("requests.Session.get", return_value=redirect_resp):
            r = extract_website_content("http://example.com/redirect-to-local")
            assert not r["success"], "Should block redirect target resolving to localhost"
            assert "blocked" in r["error"].lower() or "safety" in r["error"].lower()
    return f"Blocked redirect to localhost: {r['error']}"
run_test("SSRF: Public URL redirecting to localhost (302 Redirect)", test_redirect_to_localhost)

# 14. Public URL redirecting to a private IPv6 address (fc00::1)
def test_redirect_to_private_ipv6():
    mock_addr = [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('93.184.216.34', 80))]
    redirect_resp = MagicMock()
    redirect_resp.is_redirect = True
    redirect_resp.status_code = 301
    redirect_resp.headers = {"Location": "http://[fc00::1]:8080/data"}
    
    with patch("socket.getaddrinfo", return_value=mock_addr):
        with patch("requests.Session.get", return_value=redirect_resp):
            r = extract_website_content("http://example.com/redirect-to-ipv6")
            assert not r["success"], "Should block redirect target pointing to IPv6 unique-local"
            assert "blocked" in r["error"].lower() or "safety" in r["error"].lower()
    return f"Blocked redirect to private IPv6: {r['error']}"
run_test("SSRF: Public URL redirecting to private IPv6 (fc00::1)", test_redirect_to_private_ipv6)

# 15. Scheme Check (Non-HTTP/HTTPS schemes)
def test_scheme_validation():
    for bad_scheme in ["ftp://files.example.com", "file:///etc/passwd", "gopher://127.0.0.1:70"]:
        r = extract_website_content(bad_scheme)
        assert not r["success"], f"Should block scheme: {bad_scheme}"
        assert "scheme" in r["error"].lower()
    return "Non-HTTP/HTTPS schemes strictly rejected"
run_test("SSRF: Non-HTTP/HTTPS schemes (ftp, file, gopher)", test_scheme_validation)

# 16. Normal Public URL (Interface structure & parsing check)
def test_public_url_simulation():
    mock_addr = [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('93.184.216.34', 80))]
    success_resp = MagicMock()
    success_resp.is_redirect = False
    success_resp.status_code = 200
    success_resp.text = "<html><head><title>Example Domain</title></head><body><h1>Welcome</h1><p>Public Content</p></body></html>"
    
    with patch("socket.getaddrinfo", return_value=mock_addr):
        with patch("requests.Session.get", return_value=success_resp):
            r = extract_website_content("http://example.com")
            assert r["success"], f"Public URL should succeed: {r.get('error')}"
            assert r["title"] == "Example Domain"
            assert "Public Content" in r["content"]
            assert r["char_count"] > 0
    return f"Normal public site extracted: title='{r['title']}', content_len={r['char_count']}"
run_test("SSRF: Normal public site extraction compatibility", test_public_url_simulation)

print("\n" + "="*60)
print("TEST SUMMARY")
print("="*60)
passed = [r for r in results if r[0] == PASS]
failed = [r for r in results if r[0] == FAIL]
print(f"Total: {len(results)}   PASS: {len(passed)}   FAIL: {len(failed)}")
print("="*60)

for status, name, msg in results:
    print(f"{status}  {name}")
    if msg:
        print(f"      {msg[:100]}")

if failed:
    print("\nFAILED:")
    for _, name, msg in failed:
        print(f"FAIL: {name} -> {msg}")
    sys.exit(1)

print("\nALL SSRF HARDENING TESTS PASSED!")
