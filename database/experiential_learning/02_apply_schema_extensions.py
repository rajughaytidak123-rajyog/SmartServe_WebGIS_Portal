"""
SmartServe GIS - Experiential Learning: PostGIS Schema Extensions Applier
Script: database/experiential_learning/02_apply_schema_extensions.py

Connects to PostgreSQL/PostGIS database and executes 01_schema_extensions.sql.
Preserves existing 'services', 'categories', and 'study_area_boundaries' tables.
"""

import os
import sys
from pathlib import Path
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Ensure project root in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.core.config import settings

SQL_FILE = Path(__file__).resolve().parent / "01_schema_extensions.sql"

def apply_extensions():
    print("=" * 80)
    print("  SMARTSERVE GIS - APPLYING EXPERIENTIAL LEARNING POSTGIS EXTENSIONS")
    print("=" * 80)
    print(f"[CONFIG] Database: {settings.DB_NAME} at {settings.DB_HOST}:{settings.DB_PORT}")

    if not SQL_FILE.exists():
        print(f"[ERROR] SQL file not found: {SQL_FILE}")
        sys.exit(1)

    with open(SQL_FILE, "r", encoding="utf-8") as f:
        sql_content = f.read()

    engine = create_engine(settings.database_url)

    with engine.connect() as conn:
        print("[INFO] Executing schema extension DDL...")
        # Split on standard SQL statements or execute full script
        conn.execute(text(sql_content))
        conn.commit()
        print("[SUCCESS] Schema extension DDL executed successfully.")

        # Verify tables created
        res = conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
              AND table_type = 'BASE TABLE'
            ORDER BY table_name;
        """)).fetchall()

        tables = [r[0] for r in res]
        print(f"\n[INFO] Current public tables in '{settings.DB_NAME}':")
        for t in tables:
            print(f"  - {t}")

        # Check geometry_columns view
        geom_res = conn.execute(text("""
            SELECT f_table_name, f_geometry_column, srid, type 
            FROM geometry_columns 
            WHERE f_table_schema = 'public'
            ORDER BY f_table_name;
        """)).fetchall()

        print(f"\n[INFO] PostGIS Registered Geometry Columns:")
        for g in geom_res:
            print(f"  - Table: {g[0]:<25} | Column: {g[1]:<10} | SRID: {g[2]} | Type: {g[3]}")

    print("=" * 80)
    print("  SCHEMA EXTENSION COMPLETED!")
    print("=" * 80)

if __name__ == "__main__":
    apply_extensions()
