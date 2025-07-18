import streamlit as st
import pandas as pd
from collections import defaultdict
import chardet

# --- Read CSV with encoding detection ---
def read_csv_with_encoding(file):
    raw_bytes = file.read()
    encoding = chardet.detect(raw_bytes)["encoding"] or "utf-8"
    file.seek(0)
    return pd.read_csv(file, encoding=encoding, encoding_errors="replace")

# --- Canonical Field Mapping ---
REQUIRED_FIELDS = {
    "Transactions": {
        "Invoice ID": ["invoice_id", "bill_no", "invoice number", "InvoiceNo", "Invoice No", "orderid", "order id", "order_id"],
        "Date": ["date", "invoice_date", "purchase_date", "Invoicedate", "orderdate", "order date"],
        "Sub Category": ["subcat", "product_type", "subcategory", "sub-category"],
        "Invoice Total": ["amount", "invoice_amount", "total_amount", "grand_total"],
        "Quantity": ["qty", "units", "number of items"],
        "Discount": ["discount_amt", "disc", "offer_discount", "discount"],
        "Description": ["offer", "promo_desc", "discount name", "description"],
        "Transaction Type": ["transaction_type", "type", "return"],
        "Production Cost": ["cost", "production_cost", "item_cost"],
        "Unit Cost": ["unit_cost", "unit cost", "cost per unit"],
        "Product ID": ["prod_id", "item_code", "stockcode", "ProductID"],
        "Customer ID": ["customer", "cust_id", "cust number", "client_id", "CustomerID"],
        "Unit Price": ["unit", "price", "unit_price", "product price", "unitprice"]
    },
    "Customers": {
        "Customer ID": ["customer", "cust_id", "cust number", "client_id", "CustomerID"],
        "Gender": ["sex", "customer_gender"],
        "Name": ["name", "NAME", "customer_name"],
        "Telephone": ["telephone", "phone", "number"],
        "Email": ["email", "mail"],
        "Date Of Birth": ["date_of_birth", "dob"]
    },
    "Products": {
        "Product ID": ["prod_id", "item_code", "stockcode", "ProductID"],
        "Sub Category": ["subcategory", "subcat", "product_type", "catagory"],
        "Category": ["cat", "product_cat", "segment"]
    },
    "Promotions": {
        "Description": ["offer_desc", "campaign_desc", "promotion_name"],
        "Start": ["start", "from_date", "campaign_start", "start_date"],
        "End": ["end", "to_date", "campaign_end", "end_date"],
        "Discont": ["discount_value", "discount_rate", "disc"]
    }
}

# --- Normalization ---
def normalize(col: str) -> str:
    return col.strip().lower().replace(" ", "_")

# --- Build inventory of columns across files ---
def build_column_inventory(files):
    inventory = defaultdict(list)
    file_dfs = []

    for file in files:
        try:
            ext = file.name.lower().split('.')[-1]
            if ext == "csv":
                df = read_csv_with_encoding(file)
            elif ext in ("xls", "xlsx"):
                df = pd.read_excel(file, engine="openpyxl")
            else:
                st.warning(f"Unsupported file format: {file.name}")
                continue

            file_dfs.append((file.name, df))
            for col in df.columns:
                inventory[normalize(col)].append((file.name, col, df[col]))

        except Exception as e:
            st.error(f"❌ Failed to read {file.name}: {e}")

    return inventory, file_dfs

# --- Auto-map fields using aliases ---
def auto_map_fields(role, inventory):
    mapping = {}
    for field, aliases in REQUIRED_FIELDS[role].items():
        for alias in [normalize(field)] + [normalize(a) for a in aliases]:
            if alias in inventory:
                mapping[field] = inventory[alias][0]
                break
    return mapping

# --- Build final DataFrame from mapped fields ---
def build_dataframe_from_mapping(mapping, required_fields):
    columns = {}
    max_len = 0
    for field, (_, _, series) in mapping.items():
        s = series.reset_index(drop=True)
        columns[field] = s
        max_len = max(max_len, len(s))

    df = pd.DataFrame({field: columns.get(field, pd.Series([pd.NA] * max_len))
                       for field in required_fields})

    if "Invoice Total" in required_fields and df["Invoice Total"].isnull().all():
        if "Unit Price" in df.columns and "Quantity" in df.columns:
            df["Invoice Total"] = (
                pd.to_numeric(df["Unit Price"], errors="coerce") *
                pd.to_numeric(df["Quantity"], errors="coerce")
            )

    if "Production Cost" in required_fields:
        missing = df.get("Production Cost", pd.Series()).isnull().all()
        if missing and "Unit Cost" in df.columns and "Quantity" in df.columns:
            df["Production Cost"] = (
                pd.to_numeric(df["Unit Cost"], errors="coerce") *
                pd.to_numeric(df["Quantity"], errors="coerce")
            )

    return df

# --- Main function to classify, map, and return data ---
def classify_and_extract_data(uploaded_files):
    inventory, file_dfs = build_column_inventory(uploaded_files)
    final_data = {}
    all_mappings = {}
    confirmed = False

    for role in REQUIRED_FIELDS:
        st.markdown(f"### 📄 Mapping for `{role}`")
        auto_mapping = auto_map_fields(role, inventory)
        manual_mapping = {}
        missing = [f for f in REQUIRED_FIELDS[role] if f not in auto_mapping]

        if missing:
            st.warning(f"Manual mapping needed for `{role}`: {', '.join(missing)}")
            all_cols = sorted({col for _, df in file_dfs for col in df.columns})
            for field in missing:
                selected_col = st.selectbox(f"Select column for `{field}`", ["--"] + all_cols, key=f"{role}_{field}")
                if selected_col and selected_col != "--":
                    for fname, df in file_dfs:
                        if selected_col in df.columns:
                            manual_mapping[field] = (fname, selected_col, df[selected_col])
                            break

        all_mappings[role] = {**auto_mapping, **manual_mapping}

    # Display confirm button and only return when clicked
    if st.button("✅ Confirm and Start Analytics"):
        confirmed = True

    if confirmed:
        for role, mapping in all_mappings.items():
            fields = list(REQUIRED_FIELDS[role].keys())
            df = build_dataframe_from_mapping(mapping, fields)
            final_data[role] = df

        ai_data = {
            "txns_df": final_data.get("Transactions"),
            "customers_df": final_data.get("Customers"),
            "products_df": final_data.get("Products"),
            "promotions_df": final_data.get("Promotions"),
        }

        return final_data, ai_data

    return None, None
