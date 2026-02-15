import os
from sqlalchemy import create_engine, text

engine = create_engine(os.environ["DATABASE_URL"])

with engine.connect() as conn:
    # 1) عدد الصفوف
    n = conn.execute(text("select count(*) from loinc_terms")).scalar()
    print("Rows:", n)

    # 2) اختبار بحث
    rows = conn.execute(
        text('select "LOINC_NUM","LONG_COMMON_NAME" from loinc_terms where "LONG_COMMON_NAME" ilike :q limit 5'),
        {"q": "%glucose%"}
    ).fetchall()

    print("Sample:", rows[:5])
