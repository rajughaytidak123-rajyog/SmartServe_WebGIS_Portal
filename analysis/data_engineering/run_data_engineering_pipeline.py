"""
SmartServe GIS - Phase 1: Spatial Data Engineering
Pipeline Orchestrator & Automated Verification
Path: analysis/data_engineering/run_data_engineering_pipeline.py

Executes:
1. 01_validate_geometries_and_crs.py
2. 02_verify_pmc_containment.py
3. Asserts pipeline success and verifies output analytical files.
"""

import sys
import os
import importlib.util
from pathlib import Path

# Add project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

def load_module_from_file(module_name: str, file_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

CURRENT_DIR = Path(__file__).resolve().parent

step1_module = load_module_from_file("step1_validate", CURRENT_DIR / "01_validate_geometries_and_crs.py")
step2_module = load_module_from_file("step2_containment", CURRENT_DIR / "02_verify_pmc_containment.py")

def run_pipeline():
    print("\n" + "#" * 80)
    print("  STARTING PHASE 1: SPATIAL DATA ENGINEERING PIPELINE")
    print("#" * 80 + "\n")

    # Step 1: Geometry & CRS Validation
    print(">>> STEP 1: Geometry & CRS Validation")
    val_report = step1_module.validate_all_datasets()
    assert val_report["overall_summary"]["validation_passed"], "Validation failed: invalid geometries or CRS mismatch"
    assert val_report["overall_summary"]["master_equals_subcategories"], "Mismatch in master vs subcategory feature count"
    print(">>> STEP 1 PASSED: All geometries valid, EPSG:4326 verified, 0 invalid features.\n")

    # Step 2: Containment Verification & Primary Healthcare Extraction
    print(">>> STEP 2: Spatial Containment & Healthcare Destination Extraction")
    contain_report = step2_module.verify_containment_and_extract_targets()
    assert contain_report["pmc_containment"]["strictly_contained"], "Error: Some PMC POIs fall outside PMC boundary!"
    assert contain_report["accessibility_study_targets"]["total_primary_healthcare_destinations"] == 745, "Expected 745 PMC healthcare facilities"
    print(">>> STEP 2 PASSED: 100% PMC containment verified, 745 primary healthcare destinations extracted.\n")

    # Step 3: Verify Output Files Exist
    data_dir = PROJECT_ROOT / "data" / "analysis"
    expected_files = [
        data_dir / "data_validation_report.json",
        data_dir / "pmc_containment_report.json",
        data_dir / "pmc_all_services.geojson",
        data_dir / "pmc_healthcare_facilities.geojson"
    ]

    for ef in expected_files:
        assert ef.exists() and ef.stat().st_size > 0, f"Expected output file missing or empty: {ef}"
        print(f"  [VERIFIED OUTPUT] {ef.name} ({ef.stat().st_size:,} bytes)")

    print("\n" + "=" * 80)
    print("  PHASE 1 SPATIAL DATA ENGINEERING COMPLETED SUCCESSFULLY!")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    try:
        run_pipeline()
        sys.exit(0)
    except AssertionError as e:
        print(f"\n[FAIL] Assertion error during pipeline execution: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        sys.exit(1)
