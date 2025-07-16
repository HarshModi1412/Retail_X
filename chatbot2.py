import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import json
import re
from io import BytesIO
import chardet

# --- Gemini API Config ---
GEMINI_API_KEY = "AIzaSyD9DfnqPz7vMgh5aUHaMAVjeJbg20VZMvU"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

# --- Gemini API Call ---
def ask_gemini(messages):
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GEMINI_API_KEY
    }
    payload = {"contents": messages}
    try:
        res = requests.post(GEMINI_URL, headers=headers, json=payload)
        res.raise_for_status()
        return res.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        return f"❌ Gemini API error: {e}"

# --- File Loader ---
def load_file(file):
    raw = file.read()
    if file.name.endswith(".csv"):
        encoding = chardet.detect(raw)["encoding"] or "utf-8"
        return pd.read_csv(BytesIO(raw), encoding=encoding)
    elif file.name.endswith(".xlsx"):
        return pd.read_excel(BytesIO(raw), engine="openpyxl")
    return pd.DataFrame()

# --- Try Plotting Based on Chat Output ---
def try_plot_instruction(text, df):
    try:
        match = re.search(r"([A-Za-z0-9_ ]+)\s+vs\s+([A-Za-z0-9_ ]+)", text)
        if match:
            x_col = match.group(1).strip()
            y_col = match.group(2).strip()
            x_match = next((col for col in df.columns if x_col.lower().replace(" ", "") in col.lower().replace(" ", "")), None)
            y_match = next((col for col in df.columns if y_col.lower().replace(" ", "") in col.lower().replace(" ", "")), None)
            if x_match and y_match:
                return px.scatter(df, x=x_match, y=y_match, title=f"{y_match} vs {x_match}")
    except:
        return None
    return None

# --- Run Streamlit Chatbot ---
def run_chat():
    st.set_page_config(page_title="Smart Business Consultant 📊", layout="wide")
    st.title("Gemini-Powered Business Consultant")

    uploaded_files = st.file_uploader("📁 Upload your business files (CSV or Excel)", type=["csv", "xlsx"], accept_multiple_files=True)

    if "dataframes" not in st.session_state:
        st.session_state.dataframes = []

    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "used_initial_prompt" not in st.session_state:
        st.session_state.used_initial_prompt = False

    if uploaded_files:
        st.session_state.dataframes = [load_file(file) for file in uploaded_files]

    # Show chat history
    for msg in st.session_state.messages:
        st.chat_message(msg["role"]).markdown(msg["parts"][0]["text"])

    user_input = st.chat_input("Ask something about your business...")

    if user_input:
        st.chat_message("user").markdown(user_input)
        st.session_state.messages.append({"role": "user", "parts": [{"text": user_input}]})

        df_context = ""
        if st.session_state.dataframes:
            df_combined = pd.concat(st.session_state.dataframes, ignore_index=True)
            preview_json = df_combined.head(30).to_json(orient="records")
            df_context = f"Here is sample business data:\n{preview_json}"

        # Add system prompt once
        if "system_prompt_added" not in st.session_state:
            system_message = {
                "role": "user",
                "parts": [{
                    "text": """You are a smart business consultant. Always give short, practical tips in simple language. Remember the user's previous context and provide follow-up suggestions if asked."""
                }]
            }
            st.session_state.messages.insert(0, system_message)
            st.session_state.system_prompt_added = True

        # First question: custom format
        if not st.session_state.used_initial_prompt:
            first_prompt = f"""
You're a business consultant.

Give 3 short, practical tips to increase revenue or profit using uploaded data below.

Format:
- 📌 Tip 1: ...
- 📌 Tip 2: ...
(Chart: X vs Y) ← only if needed.

Avoid long answers. Simple language.

{df_context}
"""
            st.session_state.messages.append({"role": "user", "parts": [{"text": first_prompt}]})
            st.session_state.used_initial_prompt = True

        # Send full history to Gemini
        messages = st.session_state.messages.copy()

        with st.spinner("Thinking..."):
            raw_response = ask_gemini(messages)

        response = re.sub(r"```(json)?", "", raw_response, flags=re.DOTALL).strip("` \n")

        st.chat_message("assistant").markdown(response)
        st.session_state.messages.append({"role": "assistant", "parts": [{"text": response}]})

        # Try auto chart
        if st.session_state.dataframes:
            fig = try_plot_instruction(response, df_combined)
            if fig:
                st.plotly_chart(fig, use_container_width=True)

# --- Run App ---
if __name__ == "__main__":
    run_chat()
