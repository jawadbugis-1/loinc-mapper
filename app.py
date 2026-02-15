import os
import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text

st.set_page_config(page_title="LOINC Mapper", layout="wide")

# اتصال قاعدة البيانات
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    st.error("DATABASE_URL is missing. Please set it in environment variables.")
    st.stop()

db_url = DATABASE_URL

# Render يعطي DATABASE_URL بصيغة postgresql://
# SQLAlchemy مع psycopg3 يحتاج postgresql+psycopg://
if db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)

engine = create_engine(db_url, pool_pre_ping=True)


def loinc_search(query: str, limit: int = 10):
    """بحث سريع داخل جدول loinc_terms بالاسم الطويل."""
    if not query or not query.strip():
        return []
    q = f"%{query.strip()}%"
    sql = text("""
        SELECT "LOINC_NUM", "LONG_COMMON_NAME"
        FROM loinc_terms
        WHERE "LONG_COMMON_NAME" ILIKE :q
        LIMIT :limit
    """)
    with engine.connect() as conn:
        rows = conn.execute(sql, {"q": q, "limit": limit}).fetchall()
    return rows

def is_missing_loinc(x) -> bool:
    """اعتبار الكود ناقص إذا كان NaN أو 0 أو فارغ."""
    if pd.isna(x):
        return True
    s = str(x).strip()
    return s == "" or s in ("0", "0.0", "nan", "None")

st.title("🔎 LOINC Mapper (KAH Hospital)")

st.markdown("### 1) ارفع ملف التحاليل (CSV)")
uploaded = st.file_uploader("Upload CSV", type=["csv"])

if uploaded is None:
    st.info("ارفع ملف CSV للبدء.")
    st.stop()

df = pd.read_csv(uploaded)

st.markdown("### 2) معاينة الملف")
st.write("عدد السجلات:", len(df))
st.dataframe(df.head(20), use_container_width=True)

# تحديد السجلات الناقصة
missing_inv_mask = df["Investigation_Loinc"].apply(is_missing_loinc)
missing_param_mask = df["parameter_Loinc"].apply(is_missing_loinc)

st.markdown("### 3) السجلات التي تحتاج اقتراح LOINC")
col1, col2 = st.columns(2)
with col1:
    st.metric("Missing Investigation_Loinc", int(missing_inv_mask.sum()))
with col2:
    st.metric("Missing parameter_Loinc", int(missing_param_mask.sum()))

tab1, tab2 = st.tabs(["Investigation (ناقص)", "Parameter (ناقص)"])

with tab1:
    st.subheader("اقتراح LOINC لـ Investigation الناقصة")
    missing_inv = df[missing_inv_mask].copy()
    st.dataframe(missing_inv[["Section", "Investigation", "Investigation_Loinc"]].head(50), use_container_width=True)

    st.markdown("#### جرّب بحث سريع")
    inv_query = st.text_input("اكتب اسم Investigation للبحث (مثال: Glucose)", value="")
    if inv_query:
        results = loinc_search(inv_query, limit=10)
        st.write("Top results:")
        st.table(results)

with tab2:
    st.subheader("اقتراح LOINC لـ Parameter الناقصة")
    missing_param = df[missing_param_mask].copy()
    st.dataframe(missing_param[["Investigation", "Parameter", "parameter_Loinc"]].head(50), use_container_width=True)

    st.markdown("#### جرّب بحث سريع")
    param_query = st.text_input("اكتب اسم Parameter للبحث (مثال: Creatinine)", value="")
    if param_query:
        results = loinc_search(param_query, limit=10)
        st.write("Top results:")
        st.table(results)

st.markdown("---")
st.markdown("### 4) تصدير الملف (بدون تعديل الآن)")
st.download_button(
    label="Download CSV as-is",
    data=df.to_csv(index=False).encode("utf-8-sig"),
    file_name="kah_loinc_mapping_export.csv",
    mime="text/csv",
)
