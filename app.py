import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from pathlib import Path

st.set_page_config(
    page_title="GNCIPL | Data Analytics Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------- Styling ----------
st.markdown("""
<style>
    .main-title {font-size: 2.2rem; font-weight: 700; margin-bottom: 0.1rem;}
    .subtitle {color: #6b7280; margin-bottom: 1.5rem;}
    div[data-testid="stMetric"] {
        border: 1px solid rgba(128,128,128,.25);
        padding: 14px;
        border-radius: 12px;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">📊 GNCIPL Data Analytics Dashboard</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtitle">Interactive analytics dashboard for internship project data</div>',
    unsafe_allow_html=True
)

# ---------- Data loading ----------
@st.cache_data
def load_file(path):
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix in [".xlsx", ".xls"]:
        return pd.read_excel(path)
    return None

def find_data_files():
    extensions = {".csv", ".xlsx", ".xls"}
    roots = [Path("."), Path("data"), Path("dataset"), Path("datasets")]
    found = []
    for root in roots:
        if root.exists():
            for p in root.rglob("*"):
                if p.is_file() and p.suffix.lower() in extensions:
                    if p not in found:
                        found.append(p)
    return sorted(found)

data_files = find_data_files()

with st.sidebar:
    st.header("Data Source")
    uploaded = st.file_uploader(
        "Upload CSV or Excel",
        type=["csv", "xlsx", "xls"]
    )

if uploaded is not None:
    if uploaded.name.lower().endswith(".csv"):
        df = pd.read_csv(uploaded)
    else:
        df = pd.read_excel(uploaded)
    source_name = uploaded.name
elif data_files:
    selected = st.sidebar.selectbox(
        "Select repository dataset",
        data_files,
        format_func=lambda x: str(x)
    )
    df = load_file(selected)
    source_name = str(selected)
else:
    st.info(
        "No CSV/Excel file was found in the repository. "
        "Add your dataset to the repository (preferably in a `data` folder), "
        "or upload it using the sidebar."
    )
    st.stop()

# ---------- Cleaning ----------
df = df.copy()
df.columns = [str(c).strip() for c in df.columns]
df = df.dropna(how="all")

numeric_cols = df.select_dtypes(include=np.number).columns.tolist()
text_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()

# Try to identify common business columns automatically
def find_col(keywords):
    for col in df.columns:
        name = str(col).lower().replace("_", " ").replace("-", " ")
        if any(k in name for k in keywords):
            return col
    return None

date_col = find_col(["date", "month", "period"])
sales_value_col = find_col(["sales value", "revenue", "sales amount", "amount", "value"])
quantity_col = find_col(["sales quantity", "quantity", "units", "unit sold", "volume"])
product_col = find_col(["sku", "product", "item", "material"])
category_col = find_col(["category", "segment", "type"])

# ---------- Sidebar filters ----------
with st.sidebar:
    st.header("Filters")
    filtered = df.copy()

    if category_col and filtered[category_col].nunique(dropna=True) <= 100:
        categories = st.multiselect(
            str(category_col),
            sorted(filtered[category_col].dropna().astype(str).unique())
        )
        if categories:
            filtered = filtered[filtered[category_col].astype(str).isin(categories)]

    if product_col and filtered[product_col].nunique(dropna=True) <= 200:
        products = st.multiselect(
            str(product_col),
            sorted(filtered[product_col].dropna().astype(str).unique())
        )
        if products:
            filtered = filtered[filtered[product_col].astype(str).isin(products)]

# ---------- KPIs ----------
st.subheader("Executive Overview")

k1, k2, k3, k4 = st.columns(4)

with k1:
    st.metric("Records", f"{len(filtered):,}")

with k2:
    if quantity_col:
        value = pd.to_numeric(filtered[quantity_col], errors="coerce").sum()
        st.metric("Total Units", f"{value:,.0f}")
    else:
        st.metric("Numeric Fields", f"{len(numeric_cols)}")

with k3:
    if sales_value_col:
        value = pd.to_numeric(filtered[sales_value_col], errors="coerce").sum()
        st.metric("Total Sales", f"₹{value:,.0f}")
    else:
        st.metric("Columns", f"{len(filtered.columns)}")

with k4:
    if product_col:
        st.metric("Products / SKUs", f"{filtered[product_col].nunique():,}")
    elif category_col:
        st.metric("Categories", f"{filtered[category_col].nunique():,}")
    else:
        st.metric("Missing Values", f"{int(filtered.isna().sum().sum()):,}")

# ---------- Charts ----------
st.divider()
left, right = st.columns(2)

with left:
    st.subheader("Performance Distribution")
    if category_col and sales_value_col:
        chart_df = (
            filtered.groupby(category_col, dropna=False)[sales_value_col]
            .sum()
            .reset_index()
            .sort_values(sales_value_col, ascending=False)
            .head(15)
        )
        fig = px.bar(
            chart_df,
            x=sales_value_col,
            y=category_col,
            orientation="h",
            title="Sales by Category"
        )
        fig.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig, use_container_width=True)
    elif product_col and quantity_col:
        chart_df = (
            filtered.groupby(product_col, dropna=False)[quantity_col]
            .sum()
            .reset_index()
            .sort_values(quantity_col, ascending=False)
            .head(15)
        )
        fig = px.bar(
            chart_df,
            x=quantity_col,
            y=product_col,
            orientation="h",
            title="Top Products by Units"
        )
        fig.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig, use_container_width=True)
    elif numeric_cols:
        st.bar_chart(filtered[numeric_cols].head(20))
    else:
        st.info("No suitable numeric field was detected for this chart.")

with right:
    st.subheader("Trend Analysis")
    if date_col and (sales_value_col or quantity_col):
        trend_col = sales_value_col or quantity_col
        trend = filtered[[date_col, trend_col]].copy()
        trend[trend_col] = pd.to_numeric(trend[trend_col], errors="coerce")
        trend = trend.dropna()
        trend[date_col] = trend[date_col].astype(str)
        trend = trend.groupby(date_col, as_index=False)[trend_col].sum()

        fig = px.line(
            trend,
            x=date_col,
            y=trend_col,
            markers=True,
            title=f"{trend_col} Trend"
        )
        st.plotly_chart(fig, use_container_width=True)
    elif len(numeric_cols) >= 1:
        col = st.selectbox("Numeric metric", numeric_cols, key="trend_metric")
        st.line_chart(filtered[col].reset_index(drop=True))
    else:
        st.info("Add a date/month field or numeric field to show a trend.")

# ---------- Product analysis ----------
if product_col:
    st.divider()
    st.subheader("Product / SKU Analysis")

    metric = sales_value_col or quantity_col
    if metric:
        analysis = (
            filtered.groupby(product_col, dropna=False)[metric]
            .sum()
            .reset_index()
            .sort_values(metric, ascending=False)
        )

        a, b = st.columns(2)

        with a:
            fig = px.bar(
                analysis.head(10),
                x=metric,
                y=product_col,
                orientation="h",
                title=f"Top 10 Products by {metric}"
            )
            fig.update_layout(yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(fig, use_container_width=True)

        with b:
            fig = px.bar(
                analysis.tail(10),
                x=metric,
                y=product_col,
                orientation="h",
                title=f"Bottom 10 Products by {metric}"
            )
            fig.update_layout(yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(fig, use_container_width=True)

# ---------- Data table ----------
st.divider()
st.subheader("Filtered Dataset")
st.caption(f"Source: {source_name}")

st.dataframe(
    filtered,
    use_container_width=True,
    height=350
)

csv = filtered.to_csv(index=False).encode("utf-8")
st.download_button(
    "⬇️ Download Filtered Data",
    data=csv,
    file_name="filtered_gncipL_data.csv",
    mime="text/csv"
)

# ---------- Automatic insights ----------
st.divider()
st.subheader("Key Business Insights")

insights = []

if sales_value_col:
    sales = pd.to_numeric(filtered[sales_value_col], errors="coerce")
    if sales.notna().any():
        insights.append(f"Total sales in the selected view are ₹{sales.sum():,.0f}.")

if quantity_col:
    qty = pd.to_numeric(filtered[quantity_col], errors="coerce")
    if qty.notna().any():
        insights.append(f"Total units represented in the selected view are {qty.sum():,.0f}.")

if product_col and sales_value_col:
    temp = filtered.copy()
    temp[sales_value_col] = pd.to_numeric(temp[sales_value_col], errors="coerce")
    top = temp.groupby(product_col)[sales_value_col].sum().sort_values(ascending=False)
    if len(top):
        insights.append(f"Highest-sales product/SKU: {top.index[0]} (₹{top.iloc[0]:,.0f}).")

if category_col and sales_value_col:
    temp = filtered.copy()
    temp[sales_value_col] = pd.to_numeric(temp[sales_value_col], errors="coerce")
    top_cat = temp.groupby(category_col)[sales_value_col].sum().sort_values(ascending=False)
    if len(top_cat):
        insights.append(f"Highest-sales category: {top_cat.index[0]} (₹{top_cat.iloc[0]:,.0f}).")

if not insights:
    insights.append("The dashboard is ready. Add business-specific field names to enable richer automated insights.")

for item in insights:
    st.write("•", item)

st.caption("Built with Streamlit • Pandas • Plotly")
