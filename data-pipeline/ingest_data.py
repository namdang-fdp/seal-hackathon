"""
ETL Script: CSV → PostgreSQL
=============================
Đọc 2 file CSV từ thư mục dataset/ và đẩy vào PostgreSQL (database: seal).
- nhat_ky_dong_goi_lai.csv  → bảng nhat_ky_dong_goi_lai
- theo_doi_giao_noi_dia.csv → bảng theo_doi_giao_noi_dia

Usage:
    cd data-pipeline && source venv/bin/activate && python ingest_data.py
"""

import sys
import pandas as pd
from sqlalchemy import create_engine, text as sa_text
from sqlalchemy.types import (
    VARCHAR, INTEGER, NUMERIC, TIMESTAMP, DATE, TEXT
)

# ============================================================
# CONFIG
# ============================================================
DB_CONNECTION = "postgresql://postgres:123456@52.220.77.141:5432/se"

FILE_REPACK = "../dataset/nhat_ky_dong_goi_lai.csv"
FILE_DELIVERY = "../dataset/theo_doi_giao_noi_dia.csv"

TABLE_REPACK = "nhat_ky_dong_goi_lai"
TABLE_DELIVERY = "theo_doi_giao_noi_dia"


def log(step: str, msg: str):
    """Simple logger for terminal tracking."""
    print(f"[{step}] {msg}")


# ============================================================
# 1. READ CSV FILES
# ============================================================
def read_repack(filepath: str) -> pd.DataFrame:
    """Đọc file nhật ký đóng gói lại."""
    log("READ", f"Đang đọc file: {filepath}")
    df = pd.read_csv(filepath, encoding="utf-8")
    log("READ", f"  ✓ Đọc xong: {len(df)} rows × {len(df.columns)} columns")
    log("READ", f"  Columns: {list(df.columns)}")
    return df


def read_delivery(filepath: str) -> pd.DataFrame:
    """Đọc file theo dõi giao nội địa."""
    log("READ", f"Đang đọc file: {filepath}")
    df = pd.read_csv(filepath, encoding="utf-8")
    log("READ", f"  ✓ Đọc xong: {len(df)} rows × {len(df.columns)} columns")
    log("READ", f"  Columns: {list(df.columns)}")
    return df


# ============================================================
# 2. CLEAN DATA
# ============================================================
def clean_repack(df: pd.DataFrame) -> pd.DataFrame:
    """Clean data cho bảng nhat_ky_dong_goi_lai."""
    log("CLEAN", "Đang clean data bảng nhat_ky_dong_goi_lai...")

    # --- Fill NaN ---
    int_cols = ["original_box_count", "new_box_count", "repack_fee_vnd", "material_cost_vnd"]
    float_cols = ["original_weight_kg", "new_weight_kg"]
    text_cols = [
        "repack_id", "tracking_code", "order_code", "customer_code",
        "reason", "repack_staff", "approved_by", "status",
        "before_photo_url", "after_photo_url"
    ]
    datetime_cols = ["requested_at", "completed_at"]

    for col in int_cols:
        df[col] = df[col].fillna(0).astype(int)
    for col in float_cols:
        df[col] = df[col].fillna(0.0)
    for col in text_cols:
        df[col] = df[col].fillna("").astype(str)
    for col in datetime_cols:
        df[col] = pd.to_datetime(df[col], errors="coerce")

    null_count = df.isnull().sum().sum()
    log("CLEAN", f"  ✓ Clean xong. Remaining NaN: {null_count}")
    return df


def clean_delivery(df: pd.DataFrame) -> pd.DataFrame:
    """Clean data cho bảng theo_doi_giao_noi_dia."""
    log("CLEAN", "Đang clean data bảng theo_doi_giao_noi_dia...")

    # --- Fill NaN ---
    int_cols = ["shipping_fee_vnd", "cod_amount", "attempt_count"]
    text_cols = [
        "delivery_id", "tracking_code", "order_code", "customer_code",
        "recipient_name", "recipient_phone", "province", "district",
        "full_address", "carrier", "carrier_tracking_code",
        "domestic_warehouse", "delivery_status", "delivery_note"
    ]
    date_cols = ["scheduled_date", "actual_delivery_date"]

    for col in int_cols:
        df[col] = df[col].fillna(0).astype(int)
    for col in text_cols:
        df[col] = df[col].fillna("").astype(str)
    for col in date_cols:
        df[col] = pd.to_datetime(df[col], errors="coerce").dt.date

    # Ép phone thành string (tránh lưu dạng số)
    df["recipient_phone"] = df["recipient_phone"].astype(str).str.replace(".0", "", regex=False)

    null_count = df.isnull().sum().sum()
    log("CLEAN", f"  ✓ Clean xong. Remaining NaN: {null_count}")
    return df


# ============================================================
# 3. DEFINE SQLALCHEMY DTYPES (explicit PostgreSQL types)
# ============================================================
REPACK_DTYPES = {
    "repack_id": VARCHAR(20),
    "tracking_code": VARCHAR(20),
    "order_code": VARCHAR(20),
    "customer_code": VARCHAR(20),
    "reason": VARCHAR(200),
    "original_box_count": INTEGER(),
    "new_box_count": INTEGER(),
    "original_weight_kg": NUMERIC(10, 2),
    "new_weight_kg": NUMERIC(10, 2),
    "repack_fee_vnd": INTEGER(),
    "material_cost_vnd": INTEGER(),
    "requested_at": TIMESTAMP(),
    "completed_at": TIMESTAMP(),
    "repack_staff": VARCHAR(100),
    "approved_by": VARCHAR(100),
    "status": VARCHAR(30),
    "before_photo_url": TEXT(),
    "after_photo_url": TEXT(),
}

DELIVERY_DTYPES = {
    "delivery_id": VARCHAR(20),
    "tracking_code": VARCHAR(20),
    "order_code": VARCHAR(20),
    "customer_code": VARCHAR(20),
    "recipient_name": VARCHAR(200),
    "recipient_phone": VARCHAR(20),
    "province": VARCHAR(100),
    "district": VARCHAR(50),
    "full_address": TEXT(),
    "carrier": VARCHAR(50),
    "carrier_tracking_code": VARCHAR(30),
    "domestic_warehouse": VARCHAR(100),
    "shipping_fee_vnd": INTEGER(),
    "cod_amount": INTEGER(),
    "delivery_status": VARCHAR(30),
    "attempt_count": INTEGER(),
    "scheduled_date": DATE(),
    "actual_delivery_date": DATE(),
    "delivery_note": TEXT(),
}


# ============================================================
# 4. INGEST TO POSTGRESQL
# ============================================================
def ingest(engine, df: pd.DataFrame, table_name: str, dtype: dict):
    """Push DataFrame vào PostgreSQL."""
    log("INGEST", f"Đang đẩy {len(df)} rows vào bảng [{table_name}]...")
    df.to_sql(
        name=table_name,
        con=engine,
        if_exists="replace",
        index=False,
        dtype=dtype,
    )
    log("INGEST", f"  ✓ Đẩy xong bảng [{table_name}]!")


# ============================================================
# MAIN
# ============================================================
def main():
    print("=" * 60)
    print("  ETL Pipeline: CSV → PostgreSQL (database: seal)")
    print("=" * 60)

    # --- Step 1: Read ---
    try:
        df_repack = read_repack(FILE_REPACK)
        df_delivery = read_delivery(FILE_DELIVERY)
    except FileNotFoundError as e:
        log("ERROR", f"Không tìm thấy file: {e}")
        sys.exit(1)
    except Exception as e:
        log("ERROR", f"Lỗi khi đọc file: {e}")
        sys.exit(1)

    # --- Step 2: Clean ---
    try:
        df_repack = clean_repack(df_repack)
        df_delivery = clean_delivery(df_delivery)
    except Exception as e:
        log("ERROR", f"Lỗi khi clean data: {e}")
        sys.exit(1)

    # --- Step 3: Connect ---
    try:
        log("CONNECT", f"Đang kết nối PostgreSQL: {DB_CONNECTION}")
        engine = create_engine(DB_CONNECTION)
        # Test connection
        with engine.connect() as conn:
            conn.execute(sa_text("SELECT 1"))
        log("CONNECT", "  ✓ Kết nối thành công!")
    except Exception as e:
        log("ERROR", f"Không thể kết nối PostgreSQL: {e}")
        sys.exit(1)

    # --- Step 4: Ingest ---
    try:
        ingest(engine, df_repack, TABLE_REPACK, REPACK_DTYPES)
        ingest(engine, df_delivery, TABLE_DELIVERY, DELIVERY_DTYPES)
    except Exception as e:
        log("ERROR", f"Lỗi khi đẩy data vào DB: {e}")
        sys.exit(1)

    # --- Step 5: Verify ---
    try:
        log("VERIFY", "Kiểm tra row count...")
        with engine.connect() as conn:
            r1 = conn.execute(sa_text(f"SELECT COUNT(*) FROM {TABLE_REPACK}")).scalar()
            r2 = conn.execute(sa_text(f"SELECT COUNT(*) FROM {TABLE_DELIVERY}")).scalar()
        log("VERIFY", f"  ✓ {TABLE_REPACK}: {r1} rows")
        log("VERIFY", f"  ✓ {TABLE_DELIVERY}: {r2} rows")
    except Exception as e:
        log("ERROR", f"Lỗi khi verify: {e}")
        sys.exit(1)

    print("=" * 60)
    print("  ✅ ETL PIPELINE HOÀN TẤT THÀNH CÔNG!")
    print("=" * 60)


if __name__ == "__main__":
    main()
