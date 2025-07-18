import streamlit as st
import pandas as pd
from collections import defaultdict

# Module Imports
from modules.rfm import calculate_rfm, get_campaign_targets, generate_personal_offer
from modules.profiler import generate_customer_profile
from modules.customer_journey import map_customer_journey_and_affinity, generate_behavioral_recommendation_with_impact
from modules.discount import generate_discount_insights, assign_offer_codes
from modules.personalization import compute_customer_preferences
from modules.sales_analytics import render_sales_analytics,render_subcategory_trends,generate_sales_insights
from modules.mapper import classify_and_extract_data
from modules.smart_insights import generate_dynamic_insights
import BA
import KPI_analyst
import chatbot2

import streamlit as st

hide_ui = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    a[href*="github.com"] {visibility: hidden;}
    .css-1lsmgbg.e1fqkh3o5 {display: none;}
    </style>
"""
st.markdown(hide_ui, unsafe_allow_html=True)



# ✅ Correct and safe set_page_config
st.set_page_config(
    page_title="RetailX Dashboard",
    page_icon="📊",
    layout="wide",
    menu_items={
        "Get Help": None,
        "Report a bug": None,
        "About": None
    }
)



# Branding + styling
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
    st.warning("📤 Files uploaded. Go to the **🗂️ File Mapping** tab to proceed.")
elif st.session_state["files_mapped"]:
    st.success("✅ Files loaded and mapped. You're ready to explore insights!")

# --- Load File Data from Session ---
txns_df = st.session_state.get("txns_df")
cust_df = st.session_state.get("cust_df")
prod_df = st.session_state.get("prod_df")
promo_df = st.session_state.get("promo_df")

# --- Build AI Context Early ---
ai_context = None
if st.session_state.get("files_mapped", False):
    ai_context = {
        "txns_df": st.session_state.get("ai_txns_df"),
        "cust_df": st.session_state.get("ai_cust_df"),
        "prod_df": st.session_state.get("ai_prod_df"),
        "promo_df": st.session_state.get("ai_promo_df")
    }


tabs = st.tabs([
    "📘 Instructions", 
    "🗂️ File Mapping",
    "📊 Sales Analytics", 
    "🔍 Sub-Category Drilldown Analysis",                               
    "📊 RFM Segmentation", 
    "🤖 Business Analyst AI (BETA)",
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
            mapped_data, ai_data = classify_and_extract_data(uploaded_files)


            if mapped_data:
                # Only now save to session
                st.session_state['txns_df'] = mapped_data.get("Transactions")
                st.session_state['cust_df'] = mapped_data.get("Customers")
                st.session_state['prod_df'] = mapped_data.get("Products")
                st.session_state['promo_df'] = mapped_data.get("Promotions")
                st.session_state['ai_txns_df'] = ai_data.get("Transactions")
                st.session_state['ai_cust_df'] = ai_data.get("Customers")
                st.session_state['ai_prod_df'] = ai_data.get("Products")
                st.session_state['ai_promo_df'] = ai_data.get("Promotions")

                st.session_state["files_mapped"] = True
                st.rerun()
        else:
            # Preview mapped data
            with st.expander("📄 Transactions Sample"):
                st.dataframe(st.session_state["txns_df"].head(10) if st.session_state["txns_df"] is not None else "⚠️ Transactions data not mapped.")
            with st.expander("📄 Customers Sample"):
                st.dataframe(st.session_state["cust_df"].head(10) if st.session_state["cust_df"] is not None else "⚠️ Customers data not mapped.")
            with st.expander("📄 Products Sample"):
                st.dataframe(st.session_state["prod_df"].head(10) if st.session_state["prod_df"] is not None else "⚠️ Products data not mapped.")
            with st.expander("📄 Promotions Sample"):
                st.dataframe(st.session_state["promo_df"].head(10) if st.session_state["promo_df"] is not None else "⚠️ Promotions data not mapped.")

    else:
        st.info("👈 Please upload your CSV files from the sidebar to start mapping.")

# TAB 3: Sales Analytics
with tabs[2]:
    st.subheader("📊 Sales Analytics Overview")
    
    if txns_df is None:
        st.warning("📂 Please upload the Transactions CSV file to begin.")
    else:
        if "start_sales_analysis" not in st.session_state:
            st.session_state.start_sales_analysis = False

        if not st.session_state.start_sales_analysis:
            if st.button("▶️ Start Sales Analytics"):
                st.session_state.start_sales_analysis = True
                st.rerun()
        else:
            render_sales_analytics(txns_df)

            # Add dynamic insights section (from TAB 9)
            st.markdown("---")
            st.subheader("💡 Smart Narrative & Dynamic Insights")
            insights = generate_sales_insights(txns_df)
            generate_dynamic_insights(insights)


# After successful mapping in Tab 2
if st.session_state["files_mapped"]:
    ai_context = {
        "txns_df": st.session_state.get("ai_txns_df"),
        "cust_df": st.session_state.get("ai_cust_df"),
        "prod_df": st.session_state.get("ai_prod_df"),
        "promo_df": st.session_state.get("ai_promo_df")
    }
else:
    ai_context = None

# TAB 4: Sub-Category Drilldown Analysis
with tabs[3]:
    st.subheader("🔍 Sub-Category Drilldown Analysis")

    if txns_df is None:
        st.warning("📂 Please upload your Transactions file to proceed.")
    else:
        if "start_subcat_analysis" not in st.session_state:
            st.session_state.start_subcat_analysis = False

        if st.session_state.start_subcat_analysis:
            render_subcategory_trends(txns_df)
        else:
            st.info("Click the button below to begin analyzing sub-category trends.")
            if st.button("▶️ Start Sub-Category Analysis"):
                st.session_state.start_subcat_analysis = True
                st.rerun()

# TAB 5: RFM Segmentation
with tabs[4]:
    st.subheader("🚦 RFM Segmentation Analysis")
    if txns_df is None:
        st.warning("⚠️ Please upload the Transactions CSV file to proceed.")
    else:
        if "run_rfm" not in st.session_state:
            st.session_state.run_rfm = False

        if not st.session_state.run_rfm:
            if st.button("▶️ Run RFM Analysis"):
                st.session_state.run_rfm = True
                st.rerun()

        if st.session_state.run_rfm:
            with st.spinner("Running RFM segmentation..."):
                rfm_df = calculate_rfm(txns_df)
                st.session_state['rfm_df'] = rfm_df
            st.success("✅ RFM Analysis Completed!")
            st.dataframe(rfm_df.head(10), use_container_width=True)
            st.download_button("📥 Download RFM Output", rfm_df.to_csv(index=False), "rfm_output.csv")

            if st.button("🚀 Get Campaign Target List"):
                campaign_df = get_campaign_targets(rfm_df)
                st.session_state['campaign_df'] = campaign_df
                st.success(f"🎯 Found {len(campaign_df)} campaign-ready customers.")
                st.dataframe(campaign_df.head(10), use_container_width=True)
                st.download_button("📥 Download Campaign Target List", campaign_df.to_csv(index=False), "campaign_targets.csv")

            if st.button("💬 Send Personalized Message"):
                try:
                    campaign_df = st.session_state.get('campaign_df')
                    if campaign_df is None or campaign_df.empty:
                        st.warning("⚠️ No campaign targets found. Please run RFM and generate the campaign list first.")
                    else:
                        message = generate_personal_offer(txns_df, cust_df)
                        if "No eligible customers" in message:
                            st.warning(message)
                        else:
                            st.success("📨 Message Generated:")
                            st.markdown(message)
                except Exception as e:
                    st.error(f"⚠️ Error generating message: {e}")

# Combined TAB 6: Business Analyst + KPI Analyst AI
with tabs[5]:
    st.subheader("🧠 Business Analyst AI + KPI Analyst")

    if ai_context is None or ai_context["txns_df"] is None:
        st.warning("📂 Please upload and map your files to access AI features.")
    else:
        BA.run_business_analyst_tab(ai_context)
        st.markdown("---")
        KPI_analyst.run_kpi_analyst(ai_context)

# TAB 7: Business Chatbot AI
with tabs[6]:
    st.subheader("🤖 Business Chatbot AI")

    if ai_context is None or ai_context["txns_df"] is None:
        st.warning("📂 Please upload and map your files to use the AI chatbot.")
    else:
        chatbot2.run_chat(ai_context)


# Sidebar Reset
if st.sidebar.button("🔄 Reset App"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()
