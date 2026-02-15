import os
import pandas as pd
from sqlalchemy import create_engine, text

DATABASE_URL = os.environ.get("DATABASE_URL")
LOINC_CSV = os.environ.get("LOINC_CSV", "data/loinc.csv")
TABLE_NAME = os.environ.get("LOINC_TABLE", "loinc_terms")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is missing. Set it as an environment variable.")

engine = create_engine(DATABASE_URL)

def main():
    # 1) قراءة جزء صغير لمعرفة الأعمدة
    sample = pd.read_csv(LOINC_CSV, nrows=50)
    cols = list(sample.columns)

    print(f"Found {len(cols)} columns in LOINC CSV.")
    print("Creating table ... (replace if exists)")

    # 2) احذف الجدول إذا كان موجود (اختياري)
    with engine.begin() as conn:
        conn.execute(text(f'DROP TABLE IF EXISTS {TABLE_NAME};'))

    # 3) أنشئ الجدول تلقائيًا عبر to_sql لأول chunk
    chunksize = 50000  # ارفع/خفّض حسب قوة جهازك
    first = True

    for chunk in pd.read_csv(LOINC_CSV, chunksize=chunksize, dtype=str, low_memory=False):
        # اجعل كل شيء نص لتجنب مشاكل أنواع البيانات
        chunk = chunk.fillna("")
        chunk.to_sql(TABLE_NAME, engine, if_exists="replace" if first else "append", index=False)
        first = False
        print(f"Loaded chunk with {len(chunk)} rows...")

    print("Creating indexes...")

    # 4) فهارس مهمة للبحث السريع
    #    (تأكد أن أسماء الأعمدة موجودة في ملفك)
    with engine.begin() as conn:
        # فهرس على LOINC_NUM
        if "LOINC_NUM" in cols:
            conn.execute(text(f'CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_loinc_num ON {TABLE_NAME} ("LOINC_NUM");'))

        # فهرس بحث نصي على أسماء شائعة
        # LONG_COMMON_NAME / COMPONENT / SYSTEM / PROPERTY / METHOD_TYP
        # قد تختلف الأسماء حسب الإصدار، لذلك نتحقق قبل الإنشاء
        for c in ["LONG_COMMON_NAME", "COMPONENT", "SYSTEM", "PROPERTY", "METHOD_TYP", "SHORTNAME"]:
            if c in cols:
                conn.execute(text(f'CREATE INDEX IF NOT EXISTS idx_{TABLE_NAME}_{c.lower()} ON {TABLE_NAME} ("{c}");'))

        # تفعيل pg_trgm لبحث مشابهة النص (اختياري لكنه قوي)
        conn.execute(text('CREATE EXTENSION IF NOT EXISTS pg_trgm;'))
        if "LONG_COMMON_NAME" in cols:
            conn.execute(text(
                f'CREATE INDEX IF NOT EXISTS trgm_{TABLE_NAME}_lcn ON {TABLE_NAME} USING gin ("LONG_COMMON_NAME" gin_trgm_ops);'
            ))

    print("✅ Done. LOINC is loaded and indexed.")

if __name__ == "__main__":
    main()
