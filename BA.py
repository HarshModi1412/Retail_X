def run_business_analyst_tab(ai_context):
    import streamlit as st
    import pandas as pd
    import json
    import plotly.express as px
    import requests

    # --- Gemini API Setup ---
    GEMINI_API_KEY = "AIzaSyD9DfnqPz7vMgh5aUHaMAVjeJbg20VZMvU"
    GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

    df = ai_context.get("txns_df")
    if df is None or df.empty:
        st.warning("⚠️ No transactional data found.")
        return

    # --- Ask Gemini API ---
    def ask_llm(prompt):
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": GEMINI_API_KEY
        }
        body = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        try:
            response = requests.post(GEMINI_URL, headers=headers, json=body)
            response.raise_for_status()
            result = response.json()
            return result["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            return f"❌ Gemini Error: {e}"

    # --- Generate Business Insights ---
    def get_insights_list(df):
        preview = df.head(15).to_string(index=False)
        prompt = f"""
        You are a McKinsey-level business consultant.
        Give 3–5 business insights in JSON:
        - decision
        - observation
        - why_it_matters
        - action
        - impact (with numbers)

        Focus on profitability, revenue vs. cost, root causes, and smart actionables.
        Normalize using average/median where relevant. Use judgment for whether to show total, average, or ratio.

        Data:
        {preview}
        """
        raw = ask_llm(prompt)
        raw = raw.split("```json")[-1].split("```")[0] if "```" in raw else raw
        try:
            return json.loads(raw)
        except Exception as e:
            st.warning(f"⚠️ Failed to parse insights JSON: {e}")
            return []

    # --- Recommend a Chart for Each Insight ---
    def get_chart_spec_from_insight(df, insight_text):
        column_list = ", ".join(df.columns.tolist())
        prompt = f"""
        You are a data visualization expert.
        Based on the insight below and dataset columns: {column_list}

        Insight: "{insight_text}"

        Return JSON:
        {{
            "chart_type": "bar" or "line" or "pie" or "scatter",
            "x": "column_name",
            "y": "column_name or list of column names",
            "title": "Insight chart title"
        }}
        Only return valid JSON using actual column names.
        """
        response = ask_llm(prompt)
        try:
            if "```json" in response:
                response = response.split("```json")[-1]
            if "```" in response:
                response = response.split("```")[0]
            return json.loads(response)
        except Exception as e:
            st.warning(f"⚠️ Failed to parse chart spec: {e}")
            return None

    # --- Generate Chart ---
    def generate_chart(df, spec):
        try:
            chart_type = spec.get("chart_type", "").lower()
            x = spec["x"]
            y = spec["y"]
            title = spec.get("title", "Chart")

            if isinstance(y, str) and "/" in y:
                num_col, denom_col = map(str.strip, y.split("/"))
                if num_col in df.columns and denom_col in df.columns:
                    df[y] = df[num_col] / df[denom_col]
                else:
                    return None

            if isinstance(y, list):
                df_plot = df[[x] + y].dropna()
                df_melted = df_plot.melt(id_vars=x, value_vars=y, var_name="Series", value_name="Value")
                if chart_type == "line":
                    fig = px.line(df_melted, x=x, y="Value", color="Series", title=title)
                elif chart_type == "bar":
                    fig = px.bar(df_melted, x=x, y="Value", color="Series", title=title, barmode="group")
                elif chart_type == "scatter":
                    fig = px.scatter(df_melted, x=x, y="Value", color="Series", title=title)
                else:
                    return None
            else:
                df_plot = df[[x, y]].dropna()
                if chart_type == "bar":
                    fig = px.bar(df_plot, x=x, y=y, title=title)
                elif chart_type == "line":
                    fig = px.line(df_plot, x=x, y=y, title=title)
                elif chart_type == "pie":
                    fig = px.pie(df_plot, names=x, values=y, title=title)
                elif chart_type == "scatter":
                    fig = px.scatter(df_plot, x=x, y=y, title=title)
                else:
                    return None

            fig.update_layout(margin=dict(l=20, r=20, t=50, b=60), xaxis_tickangle=-45)
            return fig
        except Exception as e:
            st.error(f"Chart error: {e}")
            return None

    # --- UI ---
    st.subheader("🧠 Business Analyst AI")

    st.markdown("#### 📊 Data Preview")
    st.dataframe(df.head(20), use_container_width=True)

    st.markdown("#### 💡 Insights and Recommendations")
    with st.spinner("Analyzing with AI..."):
        insights = get_insights_list(df)

    for i, ins in enumerate(insights):
        st.markdown(f"### 🔍 Insight {i+1}: {ins.get('decision')}")
        st.markdown(f"- **Observation:** {ins.get('observation')}")
        st.markdown(f"- **Why it matters:** {ins.get('why_it_matters')}")
        st.markdown(f"- **Action:** {ins.get('action')}")
        st.markdown(f"- **Impact:** {ins.get('impact')}")

        with st.spinner("🔧 Generating Chart..."):
            spec = get_chart_spec_from_insight(df, ins.get("decision"))
            if spec:
                fig = generate_chart(df, spec)
                if fig:
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("⚠️ Couldn't generate chart.")
            else:
                st.warning("⚠️ No chart spec returned.")
