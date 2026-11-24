"""
SmartServe GIS - Phase 4: Pedestrian Accessibility Analysis
Automated Master Pipeline & Verification Orchestrator
Path: analysis/accessibility/run_accessibility_pipeline.py

Executes end-to-end:
1. 01_extract_walking_network.py (Network graph, lengths, travel impedance, PostGIS loading)
2. 02_walking_accessibility_isochrones.py (5, 10, 15 min isochrones, network vs Euclidean)
3. 03_h3_spatial_analysis.py (Uber H3 res 8 & 9 aggregation, reachability, spatial gaps)
4. 04_population_accessibility.py (Demographic grid disaggregation, population coverage)
5. 05_compare_scenarios.py (Scenario benchmarking, charts, and maps)
6. Asserts all output files and PostGIS database records exist and are valid.
"""

import os
import sys
import importlib.util
from pathlib import Path
from sqlalchemy import create_engine, text

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.core.config import settings

def load_module_from_file(module_name: str, file_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

CURRENT_DIR = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data" / "analysis"
MAPS_DIR = CURRENT_DIR / "maps"

def run_pipeline():
    print("\n" + "#" * 80)
    print("  SMARTSERVE GIS - PHASE 4: FULL PEDESTRIAN ACCESSIBILITY PIPELINE")
    print("#" * 80 + "\n")

    # Step 1: Walking Network
    print(">>> STEP 4A: Extract & Ingest Walking Network")
    mod_step1 = load_module_from_file("step1_network", CURRENT_DIR / "01_extract_walking_network.py")
    mod_step1.extract_and_load_walking_network()

    # Step 2: Isochrones
    print("\n>>> STEP 4B & 4C: Walking Network Isochrones")
    mod_step2 = load_module_from_file("step2_isochrones", CURRENT_DIR / "02_walking_accessibility_isochrones.py")
    mod_step2.generate_isochrones()

    # Step 3: H3 Hexagonal Analysis
    print("\n>>> STEP 4D: H3 Discrete Global Grid Analysis")
    mod_step3 = load_module_from_file("step3_h3", CURRENT_DIR / "03_h3_spatial_analysis.py")
    mod_step3.run_h3_analysis()

    # Step 4: Population Accessibility Assessment
    print("\n>>> STEP 4E: Population Accessibility Assessment")
    mod_step4 = load_module_from_file("step4_population", CURRENT_DIR / "04_population_accessibility.py")
    mod_step4.run_population_analysis()

    # Step 5: Comparative Benchmarking & Maps
    print("\n>>> STEP 4F: Scenario Benchmarking, Charts & Maps")
    mod_step5 = load_module_from_file("step5_comparison", CURRENT_DIR / "05_compare_scenarios.py")
    mod_step5.run_scenario_comparison()

    # Step 6: PostGIS Records and Output Verification
    print("\n>>> STEP 4G: Verifying PostGIS Database Records & Artifacts")
    engine = create_engine(settings.database_url)
    with engine.connect() as conn:
        n_nodes = conn.execute(text("SELECT COUNT(*) FROM walking_network_nodes")).scalar()
        n_edges = conn.execute(text("SELECT COUNT(*) FROM walking_network_edges")).scalar()
        n_iso = conn.execute(text("SELECT COUNT(*) FROM accessibility_isochrones")).scalar()
        n_h3 = conn.execute(text("SELECT COUNT(*) FROM h3_accessibility")).scalar()
        n_pop = conn.execute(text("SELECT COUNT(*) FROM population_grid")).scalar()
        n_sum = conn.execute(text("SELECT COUNT(*) FROM accessibility_summary")).scalar()

        print(f"  [POSTGIS] walking_network_nodes : {n_nodes:,}")
        print(f"  [POSTGIS] walking_network_edges : {n_edges:,}")
        print(f"  [POSTGIS] accessibility_isochrones: {n_iso}")
        print(f"  [POSTGIS] h3_accessibility      : {n_h3:,}")
        print(f"  [POSTGIS] population_grid       : {n_pop:,}")
        print(f"  [POSTGIS] accessibility_summary : {n_sum}")

        assert n_nodes > 30000, f"Expected >30k nodes, found {n_nodes}"
        assert n_edges > 80000, f"Expected >80k edges, found {n_edges}"
        assert n_iso >= 18, f"Expected >=18 isochrones, found {n_iso}"
        assert n_h3 >= 360, f"Expected >=360 H3 cells, found {n_h3}"
        assert n_pop >= 360, f"Expected >=360 population cells, found {n_pop}"
        assert n_sum >= 18, f"Expected >=18 summary scenarios, found {n_sum}"

    expected_files = [
        DATA_DIR / "pmc_walking_nodes.geojson",
        DATA_DIR / "pmc_walking_edges.geojson",
        DATA_DIR / "pmc_walking_isochrones.geojson",
        DATA_DIR / "isochrone_summary_metrics.json",
        DATA_DIR / "pmc_h3_accessibility_res8.geojson",
        DATA_DIR / "pmc_h3_accessibility_res9.geojson",
        DATA_DIR / "h3_summary_metrics.json",
        DATA_DIR / "pmc_population_grid.geojson",
        DATA_DIR / "population_accessibility_summary.json",
        MAPS_DIR / "isochrone_coverage_comparison.png",
        MAPS_DIR / "population_access_breakdown.png",
        MAPS_DIR / "pmc_accessibility_isochrones_map.png",
        MAPS_DIR / "pmc_h3_accessibility_gap_map.png"
    ]

    for ef in expected_files:
        assert ef.exists() and ef.stat().st_size > 0, f"Missing output file: {ef}"
        print(f"  [FILE VERIFIED] {ef.name} ({ef.stat().st_size:,} bytes)")

    print("\n" + "=" * 80)
    print("  PHASE 4: PEDESTRIAN ACCESSIBILITY ANALYSIS COMPLETED AND VERIFIED 100%!")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    run_pipeline()
