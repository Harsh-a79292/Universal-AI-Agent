import io
from typing import Dict, Any, Optional
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from models.llm_service import query_llm_with_fallback

def load_tabular_file(file_bytes: bytes, filename: str) -> Dict[str, Any]:
    """Load an uploaded CSV or XLSX file into a pandas DataFrame."""
    try:
        if filename.lower().endswith('.csv'):
            try:
                df = pd.read_csv(io.BytesIO(file_bytes))
            except UnicodeDecodeError:
                df = pd.read_csv(io.BytesIO(file_bytes), encoding='latin1')
        elif filename.lower().endswith(('.xlsx', '.xls')):
            df = pd.read_excel(io.BytesIO(file_bytes))
        else:
            return {"success": False, "error": "Unsupported file format. Please upload .csv or .xlsx files.", "df": None}

        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        summary_stats = {}
        for col in numeric_cols:
            summary_stats[col] = {
                "sum": float(df[col].sum()),
                "mean": float(df[col].mean()),
                "min": float(df[col].min()),
                "max": float(df[col].max()),
                "count": int(df[col].count())
            }

        return {
            "success": True,
            "filename": filename,
            "rows": len(df),
            "columns": df.columns.tolist(),
            "numeric_columns": numeric_cols,
            "missing_values": int(df.isnull().sum().sum()),
            "summary_stats": summary_stats,
            "df": df,
            "error": None
        }
    except Exception as e:
        return {"success": False, "error": f"Failed to parse tabular file: {str(e)}", "df": None}

def answer_tabular_question(df: pd.DataFrame, question: str, preferred_model: str = "auto") -> Dict[str, Any]:
    """Analyze tabular data and answer questions about it using LLM reasoning."""
    numeric_summary = df.describe().to_string()
    sample_rows = df.head(5).to_string()
    columns_info = str(df.dtypes.to_dict())

    prompt = f"""Dataset Information:
Columns & Types: {columns_info}
Total Rows: {len(df)}
Numeric Summary Statistics:
{numeric_summary}

First 5 Rows Sample:
{sample_rows}

User Question about the data:
"{question}"

Analyze the dataset and provide a clear, accurate, and structured answer:"""
    system_instruction = "You are a senior data analyst. Provide precise data insights."
    return query_llm_with_fallback(prompt, system_instruction, preferred_model=preferred_model)

def generate_data_chart(df: pd.DataFrame, x_col: str, y_col: str, chart_type: str = "bar") -> Dict[str, Any]:
    """Generate a clean matplotlib figure for Streamlit rendering."""
    try:
        fig, ax = plt.subplots(figsize=(8, 4.5))
        # Styling for dark theme compatibility
        fig.patch.set_facecolor('#161b22')
        ax.set_facecolor('#0d1117')
        ax.tick_params(colors='#e6edf3')
        ax.xaxis.label.set_color('#e6edf3')
        ax.yaxis.label.set_color('#e6edf3')
        ax.title.set_color('#ffffff')
        for spine in ax.spines.values():
            spine.set_color('#30363d')

        # Limit to top 15 rows for readable plotting if categorical
        plot_df = df.dropna(subset=[x_col, y_col]).head(15)

        if chart_type == "bar":
            ax.bar(plot_df[x_col].astype(str), plot_df[y_col], color='#e63946', edgecolor='#ff6b77', alpha=0.9)
            plt.xticks(rotation=45, ha='right')
        elif chart_type == "line":
            ax.plot(plot_df[x_col].astype(str), plot_df[y_col], color='#58a6ff', marker='o', linewidth=2)
            plt.xticks(rotation=45, ha='right')
        elif chart_type == "scatter":
            ax.scatter(plot_df[x_col], plot_df[y_col], color='#38bdf8', s=60, alpha=0.8)
        else:
            return {"success": False, "error": f"Unsupported chart type: {chart_type}", "fig": None}

        ax.set_xlabel(x_col)
        ax.set_ylabel(y_col)
        ax.set_title(f"{chart_type.title()} Chart: {y_col} vs {x_col}")
        plt.tight_layout()

        return {"success": True, "fig": fig, "error": None}
    except Exception as e:
        return {"success": False, "error": f"Failed to generate chart: {str(e)}", "fig": None}

