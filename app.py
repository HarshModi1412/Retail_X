import streamlit as st
import pandas as pd

# Module Imports
from modules.rfm import calculate_rfm, get_campaign_targets, generate_personal_offer
from modules.profiler import generate_customer_profile
from modules.customer_journey import map_customer_journey_and_affinity, generate_behavioral_recommendation_with_impact
from modules.discount import generate_discount_insights, assign_offer_codes
from modules.personalization import compute_customer_preferences
from modules.sales_analytics import render_sales_analytics, render_subcategory_trends, generate_sales_insights
from modules.mapper import classify_and_extract_data
from modules.smart_insights import generate_dynamic_insights
import BA
import KPI_analyst
import chatbot2

# --- Hide Streamlit UI Elements ---
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    a[href*="github.com"] {visibility: hidden;}
    .css-1lsmgbg.e1fqkh3o5 {display: none;}
    </style>
""", unsafe_allow_html=True)

# --- Page Config ---
st.set_page_config(
    page_title="RetailX Dashboard",
    page_icon="📊",
    layout="wide",
    menu_items={"Get Help": None, "Report a bug": None, "About": None}
)

# --- Branding ---
st.markdown("""
<style>
    .block-container {
        padding-top: 1rem;
        padding-bottom: 0rem;
    }
</style>
<h1 style='text-align: left; color: #FFFFFF; font-size: 3em; margin: 0;'>RetailX</h1>
<hr style='margin: 0.5rem auto 1rem auto; border: 1px solid #ccc; width: 100%;' />
""", unsafe_allow_html=True)

# --- Sidebar Upload ---
st.sidebar.title("📁 Upload Your CSV Files")
uploaded_files = st.sidebar.file_uploader(
    "Upload 1–4 CSV files (Transactions, Customers, Products, Promotions)",
    type=["csv", "xlsx"],
    accept_multiple_files=True
)

# --- Session State Initialization ---
for key in ['uploaded_files', 'files_mapped', 'txns_df', 'cust_df', 'prod_df', 'promo_df']:
    if key not in st.session_state:
        st.session_state[key] = None if key.endswith('_df') else False

# --- Store Files Temporarily in Session ---
if uploaded_files:
    st.session_state["uploaded_files"] = uploaded_files

# --- User Feedback ---
if not uploaded_files and not st.session_state["files_mapped"]:
    st.info("👈 Please upload your CSV files from the sidebar to get started.")
elif uploaded_files and not st.session_state["files_mapped"]:
    st.warning("📄 Files uploaded. Go to the **🗂️ File Mapping** tab to proceed.")
elif st.session_state["files_mapped"]:
    st.success("✅ Files loaded and mapped. You're ready to explore insights!")

# --- Build AI Context Early ---
ai_context = None
if st.session_state.get("files_mapped"):
    ai_txns_df = st.session_state.get("ai_txns_df")
    ai_cust_df = st.session_state.get("ai_cust_df")
    ai_prod_df = st.session_state.get("ai_prod_df")
    ai_promo_df = st.session_state.get("ai_promo_df")

    if all([ai_txns_df is not None, ai_cust_df is not None, ai_prod_df is not None, ai_promo_df is not None]):
        ai_context = {
            "txns_df": ai_txns_df,
            "cust_df": ai_cust_df,
            "prod_df": ai_prod_df,
            "promo_df": ai_promo_df
        }

# --- Tabs ---
tabs = st.tabs([
    "📘 Instructions", 
    "🗂️ File Mapping",
    "📊 Sales Analytics", 
    "🔍 Sub-Category Drilldown Analysis",                               
    "📊 RFM Segmentation", 
    "🧠 Business Analyst AI (BETA)",
    "🤖 Chatbot"
])

# TAB 1: Instructions
with tabs[0]:
    st.subheader("📘 Instructions & User Guide")
    st.markdown("""
        Welcome to the **Retail Analytics Dashboard**. Please follow the steps below:
        - 📁 Upload your data files from the **sidebar**
        - Navigate through tabs to run analysis
        - Use buttons to trigger specific modules
        - Download results wherever applicable
    """)

# TAB 2: File Mapping
with tabs[1]:
    st.subheader("🗂️ File Mapping & Confirmation")

    if uploaded_files:
        st.markdown("### 🧩 Column Mapping for Each File")

        if not st.session_state.get("files_mapped"):
            mapped_data, new_ai_context = classify_and_extract_data(uploaded_files)

            if mapped_data and new_ai_context:
                st.session_state['txns_df'] = mapped_data.get("Transactions")
                st.session_state['cust_df'] = mapped_data.get("Customers")
                st.session_state['prod_df'] = mapped_data.get("Products")
                st.session_state['promo_df'] = mapped_data.get("Promotions")
                st.session_state['ai_txns_df'] = new_ai_context.get("txns_df")
                st.session_state['ai_cust_df'] = new_ai_context.get("cust_df")
                st.session_state['ai_prod_df'] = new_ai_context.get("prod_df")
                st.session_state['ai_promo_df'] = new_ai_context.get("promo_df")
                st.session_state["files_mapped"] = True
                st.rerun()

        else:
            # Preview mapped data
            with st.expander("📄 Transactions Sample"):
                txns_df = st.session_state.get("txns_df")
                if txns_df is not None:
                    st.dataframe(txns_df.head(10))
                else:
                    st.warning("⚠️ Transactions data not mapped.")

            with st.expander("📄 Customers Sample"):
                cust_df = st.session_state.get("cust_df")
                if cust_df is not None:
                    st.dataframe(cust_df.head(10))
                else:
                    st.warning("⚠️ Customers data not mapped.")

            with st.expander("📄 Products Sample"):
                prod_df = st.session_state.get("prod_df")
                if prod_df is not None:
                    st.dataframe(prod_df.head(10))
                else:
                    st.warning("⚠️ Products data not mapped.")

            with st.expander("📄 Promotions Sample"):
                promo_df = st.session_state.get("promo_df")
                if promo_df is not None:
                    st.dataframe(promo_df.head(10))
                else:
                    st.warning("⚠️ Promotions data not mapped.")

    else:
        st.info("👈 Please upload your CSV files from the sidebar to start mapping.")

# TAB 3: Sales Analytics
with tabs[2]:
    st.subheader("📊 Sales Analytics Overview")
    txns_df = st.session_state.get("txns_df")
    if txns_df is None:
        st.warning("📂 Please upload the Transactions CSV file to begin.")
    else:
        if st.button("▶️ Start Sales Analytics"):
            render_sales_analytics(txns_df)
            st.markdown("---")
            st.subheader("💡 Smart Narrative & Dynamic Insights")
            insights = generate_sales_insights(txns_df)
            generate_dynamic_insights(insights)

# TAB 4: Sub-Category Drilldown Analysis
with tabs[3]:
    st.subheader("🔍 Sub-Category Drilldown Analysis")
    txns_df = st.session_state.get("txns_df")
    if txns_df is not None:
        render_subcategory_trends(txns_df)
    else:
        st.warning("📂 Please upload your Transactions file to proceed.")

# TAB 5: RFM Segmentation
with tabs[4]:
    st.subheader("🚦 RFM Segmentation Analysis")
    txns_df = st.session_state.get("txns_df")
    cust_df = st.session_state.get("cust_df")
    if txns_df is not None:
        if st.button("▶️ Run RFM Analysis"):
            rfm_df = calculate_rfm(txns_df)
            st.dataframe(rfm_df.head(10))
            st.download_button("📥 Download RFM Output", rfm_df.to_csv(index=False), "rfm_output.csv")
            if st.button("🚀 Get Campaign Target List"):
                campaign_df = get_campaign_targets(rfm_df)
                st.dataframe(campaign_df.head(10))
            if st.button("💬 Send Personalized Message"):
                msg = generate_personal_offer(txns_df, cust_df)
                st.markdown(msg)
    else:
        st.warning("⚠️ Please upload the Transactions CSV file to proceed.")

# TAB 6: Business Analyst + KPI Analyst AI
with tabs[5]:
    st.subheader("🧠 Business Analyst AI + KPI Analyst")
    if ai_context is not None and ai_context.get("txns_df") is not None:
        BA.run_business_analyst_tab(ai_context)
        st.markdown("---")
        KPI_analyst.run_kpi_analyst(ai_context)
    else:
        st.warning("📂 Please upload and map your files to access AI features.")

# TAB 7: Business Chatbot AI
with tabs[6]:
    st.subheader("🤖 Business Chatbot AI")
    if ai_context is not None and ai_context.get("txns_df") is not None:
        chatbot2.run_chat(ai_context)
    else:
        st.warning("📂 Please upload and map your files to use the AI chatbot.")

# --- Sidebar Reset Button ---
if st.sidebar.button("🔄 Reset App"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()
