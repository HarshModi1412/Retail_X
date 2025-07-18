import streamlit as st
import pandas as pd
import json
import chardet
import requests
import re
from io import BytesIO
import plotly.express as px

# --- Configuration ---
# --- Gemini API Setup ---
GEMINI_API_KEY = "AIzaSyD9DfnqPz7vMgh5aUHaMAVjeJbg20VZMvU"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

# --- Gemini API Call ---
def ask_llm(prompt):
    headers = {"Content-Type": "application/json", "X-Goog-Api-Key": GEMINI_API_KEY}
    body = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        res = requests.post(GEMINI_URL, headers=headers, json=body)
        res.raise_for_status()
        result = res.json()
        if "candidates" not in result:
            return ""
        return result["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        st.error(f"❌ Gemini Error: {e}")
        return ""

# --- Extract JSON Safely ---
def extract_json_from_text(text):
    try:
        match = re.search(r"```json(.*?)```", text, re.DOTALL)
        if match:
            return match.group(1).strip()
        match = re.search(r"\[.*\]|\{.*\}", text, re.DOTALL)
        if match:
            return match.group(0).strip()
        if text.strip().startswith("[") or text.strip().startswith("{"):
            return text.strip()
    except Exception as e:
        st.warning(f"⚠️ extract_json_from_text error: {e}")
    return ""

# --- Load File ---
def load_file(file):
    raw = file.read()
    if file.name.endswith(".csv"):
        encoding = chardet.detect(raw)["encoding"] or "utf-8"
        return pd.read_csv(BytesIO(raw), encoding=encoding)
    elif file.name.endswith(".xlsx"):
        return pd.read_excel(BytesIO(raw), engine="openpyxl")
    else:
        st.error("Unsupported format.")
        return pd.DataFrame()

# --- Fuzzy Column Matching Helper ---
def fuzzy_match(col, candidates):
    col = col.lower().replace(" ", "")
    for candidate in candidates:
        if col in candidate.lower().replace(" ", ""):
            return candidate
    return None

# --- Get KPI List ---
def get_kpi_list(data_preview, industry, scale, goal):
    prompt = f"""
You are an expert business analyst.

The uploaded dataset is from the **{industry}** industry, business scale: **{scale}**, with a goal to: **{goal}**.

Available columns:
{data_preview.splitlines()[0]}

You need to generate a list of KPIs that are:
1. Relevant to the goal and industry.
2. Can be calculated using the dataset.
3. Structured clearly to help an analytics engine calculate them correctly.

For each KPI, return JSON using this structure:

[
  {{
    "name": "KPI Name",
    "operation": "SUM / COUNT / AVERAGE / custom logic",
    "aggregation_map": {{
        "Column A": "SUM",
        "Column B": "COUNT_DISTINCT",
        ...
    }},
    "group_by": ["Column X"],  // Optional, can be empty list
    "filter": {{
        "column": "Offer Type",
        "value": "Yes"
    }},  // Optional, can be null
    "why": "Why this KPI is important"
  }}
]

🛑 Do NOT include formulas as strings like "SUM(X) / COUNT(Y)" — instead, break it down into "aggregation_map" and "operation" as shown above.

✅ Do NOT include markdown, explanation, or commentary. Return JSON only.
"""
    raw = ask_llm(prompt)
    #st.subheader("🔍 Gemini Raw Response")
    #st.code(raw)
    cleaned = extract_json_from_text(raw)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        st.warning(f"⚠️ JSON decode failed: {e}")
        st.code(cleaned)
        return []


# --- Calculate KPIs with Fuzzy Matching & Parsing ---
import numpy as np

def calculate_kpis(df, kpi_definitions):
    results = []

    for kpi in kpi_definitions:
        try:
            temp_df = df.copy()

            # Step 1: Apply filter if defined
            filter_info = kpi.get("filter")
            if filter_info:
                filter_col = fuzzy_match(filter_info["column"], df.columns)
                if filter_col:
                    temp_df = temp_df[temp_df[filter_col] == filter_info["value"]]
                else:
                    raise ValueError(f"Filter column '{filter_info['column']}' not found")

            # Step 2: Apply aggregation to each required column
            agg_results = {}
            for col_key, agg_type in kpi["aggregation_map"].items():
                actual_col = fuzzy_match(col_key, df.columns)
                if not actual_col:
                    raise ValueError(f"Column '{col_key}' not found")

                if agg_type == "SUM":
                    agg_results[col_key] = temp_df[actual_col].sum()
                elif agg_type == "COUNT":
                    agg_results[col_key] = temp_df[actual_col].count()
                elif agg_type == "COUNT_DISTINCT":
                    agg_results[col_key] = temp_df[actual_col].nunique()
                elif agg_type == "AVERAGE":
                    agg_results[col_key] = temp_df[actual_col].mean()
                else:
                    raise ValueError(f"Unsupported aggregation: {agg_type}")

            # Step 3: Combine values based on 'operation'
            op = kpi["operation"].upper()

            if op == "SUM":
                # If only one key, return it directly
                val = list(agg_results.values())[0]
            elif op == "AVERAGE":
                val = list(agg_results.values())[0]
            elif op == "COUNT" or op == "COUNT_DISTINCT":
                val = list(agg_results.values())[0]
            elif op == "DIVIDE":
                keys = list(agg_results.keys())
                val = agg_results[keys[0]] / agg_results[keys[1]] if agg_results[keys[1]] != 0 else 0
            elif op == "MULTIPLY":
                keys = list(agg_results.keys())
                val = agg_results[keys[0]] * agg_results[keys[1]]
            elif op == "RATIO":
                keys = list(agg_results.keys())
                val = agg_results[keys[0]] / agg_results[keys[1]] if agg_results[keys[1]] != 0 else 0
            else:
                raise ValueError(f"Unsupported operation: {op}")

            # Finalize value
            kpi["value"] = round(val, 2) if isinstance(val, (int, float, np.float64)) else val

        except Exception as e:
            kpi["value"] = "❌"
            kpi["error"] = str(e)

        results.append(kpi)

    return results

# --- Get Benchmarks ---
def get_mock_benchmarks(kpis):
    for kpi in kpis:
        try:
            val = float(kpi["value"])
            kpi["benchmark"] = round(val * 1.1, 2)
        except:
            kpi["benchmark"] = "N/A"
    return kpis

# --- Get Insights ---
def get_comparative_insights(kpi_list, industry, scale, goal):
    prompt = f"""
You are a McKinsey consultant. Based on these KPIs for a company in {industry}, scale {scale}, goal: {goal}, give 3-5 insights.
Each should include:
- kpi_name
- company_value
- benchmark_value
- observation
- decision
- action
- estimated impact
Return as JSON.
KPIs:
{kpi_list}
"""
    raw = ask_llm(prompt)
    #st.subheader("🔍 Gemini Raw Insight Response")
    #st.code(raw)
    cleaned = extract_json_from_text(raw)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        st.warning(f"⚠️ Insight JSON decode failed: {e}")
        st.code(cleaned)
        return []

# --- Plot KPI Comparison ---
def plot_kpi_comparison(kpis):
    try:
        df_plot = pd.DataFrame([
            {"KPI": k["name"], "Type": "Company", "Value": k["value"]} for k in kpis if isinstance(k["value"], (int, float))
        ] + [
            {"KPI": k["name"], "Type": "Benchmark", "Value": k["benchmark"]} for k in kpis if isinstance(k["benchmark"], (int, float))
        ])
        return px.bar(df_plot, x="KPI", y="Value", color="Type", barmode="group", title="KPI Comparison")
    except Exception as e:
        st.error(f"Chart error: {e}")
        return None

# --- Streamlit UI ---
def run_kpi_analyst(ai_context):
    st.title("📊 AI KPI Analyst with Benchmarking")

    if not ai_context or "txns_df" not in ai_context:
        st.warning("⚠️ No data available. Please upload and map your files first.")
        return

    df = ai_context["txns_df"]

    st.subheader("🔍 Data Preview")
    st.dataframe(df.head(15))

    industry = st.text_input("Industry", placeholder="e.g., Retail, SaaS, Manufacturing")
    scale = st.text_input("Business Scale", placeholder="e.g., Small, Mid-size, Enterprise")
    goal = st.text_area("Business Goal or Problem Statement")

    if industry and scale and goal:
        kpi_defs = get_kpi_list(df.head(15).to_string(index=False), industry, scale, goal)
        if not kpi_defs:
            st.warning("⚠️ No KPI definitions found.")
            return

        st.subheader("✅ Calculated KPIs")
        kpi_with_values = calculate_kpis(df, kpi_defs)
        kpi_with_benchmarks = get_mock_benchmarks(kpi_with_values)
        st.dataframe(pd.DataFrame(kpi_with_benchmarks))

        st.subheader("📈 KPI Comparison")
        fig = plot_kpi_comparison(kpi_with_benchmarks)
        if fig:
            st.plotly_chart(fig, use_container_width=True)

        st.subheader("💡 Insights & Recommendations")
        insights = get_comparative_insights(kpi_with_benchmarks, industry, scale, goal)
        for ins in insights:
            st.markdown(f"### 🔍 KPI: {ins.get('kpi_name')}")
            st.markdown(f"- **Observation:** {ins.get('observation')}")
            st.markdown(f"- **Decision:** {ins.get('decision')}")
            st.markdown(f"- **Action:** {ins.get('action')}")
            st.markdown(f"- **Estimated Impact:** {ins.get('estimated impact')}")

if __name__ == "__main__":
    run_kpi_analyst()
