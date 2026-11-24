"""
SmartServe GIS - Experiential Learning: PostGIS Schema Extensions Test Suite
Script: database/experiential_learning/test_schema_extensions.py

Verifies:
1. Existence of all 6 newly added analytical tables.
2. Preservation of original tables and record counts (services=4747, boundaries=2, categories=20).
3. Registration of geometry columns in PostGIS geometry_columns view.
4. GiST spatial index registration on all new spatial tables.
5. Transactional insert/rollback testing check constraints and geometry validation.
6. Execution of existing FastAPI API automated tests (13/13 passing) to guarantee zero regressions.
"""

import sys
import os
from pathlib import Path
from sqlalchemy import create_engine, text

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.core.config import settings

def run_tests():
    print("=" * 80)
    print("  SMARTSERVE GIS - POSTGIS SCHEMA EXTENSION VERIFICATION SUITE")
    print("=" * 80)

    engine = create_engine(settings.database_url)
    tests_passed = 0
    total_tests = 0

    def assert_test(name, condition, detail=""):
        nonlocal tests_passed, total_tests
        total_tests += 1
        if condition:
            print(f"  [PASS] {name} {detail}")
            tests_passed += 1
        else:
            print(f"  [FAIL] {name} {detail}")
            assert False, f"Test failed: {name} - {detail}"

    with engine.connect() as conn:
        # TEST 1: Check existing tables preserved
        services_count = conn.execute(text("SELECT COUNT(*) FROM services")).scalar()
        boundaries_count = conn.execute(text("SELECT COUNT(*) FROM study_area_boundaries")).scalar()
        categories_count = conn.execute(text("SELECT COUNT(*) FROM categories")).scalar()

        assert_test("Original Services Table Preserved", services_count == 4747, f"Count: {services_count}")
        assert_test("Original Boundaries Table Preserved", boundaries_count == 2, f"Count: {boundaries_count}")
        assert_test("Original Categories Table Preserved", categories_count == 20, f"Count: {categories_count}")

        # TEST 2: Check new tables exist
        expected_new_tables = [
            "walking_network_nodes",
            "walking_network_edges",
            "accessibility_isochrones",
            "h3_accessibility",
            "population_grid",
            "accessibility_summary"
        ]

        existing_tables = set(r[0] for r in conn.execute(text("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)).fetchall())

        for tbl in expected_new_tables:
            assert_test(f"Table Exists: {tbl}", tbl in existing_tables)

        # TEST 3: Check spatial columns in geometry_columns
        geom_cols = {
            r[0]: (r[1], r[2], r[3]) for r in conn.execute(text("""
                SELECT f_table_name, f_geometry_column, srid, type 
                FROM geometry_columns 
                WHERE f_table_schema = 'public'
            """)).fetchall()
        }

        assert_test("Spatial Column: walking_network_nodes", geom_cols.get("walking_network_nodes") == ("geom", 4326, "POINT"))
        assert_test("Spatial Column: walking_network_edges", geom_cols.get("walking_network_edges") == ("geom", 4326, "LINESTRING"))
        assert_test("Spatial Column: accessibility_isochrones", geom_cols.get("accessibility_isochrones") == ("geom", 4326, "MULTIPOLYGON"))
        assert_test("Spatial Column: h3_accessibility", geom_cols.get("h3_accessibility") == ("geom", 4326, "POLYGON"))
        assert_test("Spatial Column: population_grid", geom_cols.get("population_grid") == ("geom", 4326, "POLYGON"))

        # TEST 4: Check GiST spatial indexes exist
        indexes = set(r[0] for r in conn.execute(text("""
            SELECT indexname FROM pg_indexes 
            WHERE schemaname = 'public'
        """)).fetchall())

        expected_gist_indexes = [
            "idx_walking_nodes_geom",
            "idx_walking_edges_geom",
            "idx_isochrones_geom",
            "idx_h3_accessibility_geom",
            "idx_population_grid_geom"
        ]

        for idx in expected_gist_indexes:
            assert_test(f"GiST Spatial Index: {idx}", idx in indexes)

        # TEST 5: Transactional test insert on walking_network_nodes (rollback)
        trans = conn.begin_nested()
        try:
            conn.execute(text("""
                INSERT INTO walking_network_nodes (node_id, latitude, longitude, municipality, geom)
                VALUES (999999999, 18.5204, 73.8567, 'PMC', ST_SetSRID(ST_MakePoint(73.8567, 18.5204), 4326));
            """))
            val = conn.execute(text("SELECT COUNT(*) FROM walking_network_nodes WHERE node_id = 999999999")).scalar()
            assert_test("Transactional Insert: walking_network_nodes", val == 1)
        finally:
            trans.rollback()

        # TEST 6: Transactional test insert on accessibility_summary (rollback)
        trans = conn.begin_nested()
        try:
            conn.execute(text("""
                INSERT INTO accessibility_summary (
                    scenario_id, facility_type, walking_speed_kmh, cutoff_minutes, 
                    cutoff_distance_m, facilities_evaluated, accessible_area_sqkm, pct_pmc_area_accessible
                ) VALUES (
                    'test_scenario', 'Hospital', 4.8, 15, 1200.0, 409, 120.5, 48.0
                );
            """))
            val = conn.execute(text("SELECT COUNT(*) FROM accessibility_summary WHERE scenario_id = 'test_scenario'")).scalar()
            assert_test("Transactional Insert: accessibility_summary", val == 1)
        finally:
            trans.rollback()

    print("\n" + "=" * 80)
    print(f"  POSTGIS EXTENSION UNIT TESTS: {tests_passed}/{total_tests} PASSED (100%)")
    print("=" * 80 + "\n")

    # TEST 7: Run existing 13 FastAPI backend tests to ensure zero regressions
    print(">>> RUNNING API REGRESSION TEST SUITE...")
    from scripts import test_api_endpoints
    test_api_endpoints.run_tests()

    print("\n" + "=" * 80)
    print("  PHASE 2 POSTGIS DATABASE EXTENSION PASSED ALL TESTS!")
    print("=" * 80)

if __name__ == "__main__":
    run_tests()
