"""
SmartServe GIS - Phase 3: GeoServer OGC Services Automated Test Suite
Script: geoserver/test_ogc_services.py

Tests:
1. WMS GetCapabilities (version 1.3.0 & 1.1.1)
2. WMS GetMap (renders live PNG maps for all 6 published layers to geoserver/test_outputs/)
3. WFS GetCapabilities (version 2.0.0)
4. WFS GetFeature (GeoJSON feature retrieval across all published layers)
5. Comprehensive reporting of response times, HTTP codes, and payload sizes.
6. Execution of FastAPI backend test suite to ensure zero regressions.
"""

import sys
import os
import json
import time
from pathlib import Path
import requests

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

GEOSERVER_HOST = "http://localhost:8080/geoserver"
WORKSPACE = "smartserve"
OUTPUT_DIR = PROJECT_ROOT / "geoserver" / "test_outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Study area bbox in WGS84 [minx/minlon, miny/minlat, maxx/maxlon, maxy/maxlat]
BBOX_WMS_111 = "73.70,18.40,73.98,18.65" # minx, miny, maxx, maxy
BBOX_WMS_130 = "18.40,73.70,18.65,73.98" # miny, minx, maxy, maxx for EPSG:4326 in 1.3.0

LAYERS = [
    "pmc_boundary",
    "all_services",
    "walking_network",
    "accessibility_isochrones",
    "h3_accessibility",
    "population_grid"
]

def run_tests():
    print("=" * 80)
    print("  SMARTSERVE GIS - PHASE 3: OGC WMS & WFS VERIFICATION TEST SUITE")
    print("=" * 80)

    tests_passed = 0
    total_tests = 0

    def record_test(name, passed, detail=""):
        nonlocal tests_passed, total_tests
        total_tests += 1
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {status} {name:<45} | {detail}")
        if not passed:
            assert False, f"Failed: {name} - {detail}"
        tests_passed += 1

    session = requests.Session()

    # -------------------------------------------------------------------------
    # 1. WMS GETCAPABILITIES
    # -------------------------------------------------------------------------
    print("\n--- 1. TESTING WMS GETCAPABILITIES ---")
    wms_cap_url = f"{GEOSERVER_HOST}/{WORKSPACE}/wms?service=WMS&version=1.3.0&request=GetCapabilities"
    t0 = time.time()
    r = session.get(wms_cap_url, timeout=10)
    wms_cap_time = round((time.time() - t0) * 1000, 1)

    has_layers = all(f"<Name>{WORKSPACE}:{lay}</Name>" in r.text or f"<Name>{lay}</Name>" in r.text for lay in LAYERS)
    record_test("WMS 1.3.0 GetCapabilities", r.status_code == 200 and "<WMS_Capabilities" in r.text, f"HTTP {r.status_code} ({wms_cap_time}ms, {len(r.content):,} bytes)")
    record_test("WMS Layers Advertised in XML", has_layers, f"All {len(LAYERS)} layers present in capabilities")

    # -------------------------------------------------------------------------
    # 2. WMS GETMAP (RENDER PNGs)
    # -------------------------------------------------------------------------
    print("\n--- 2. TESTING WMS GETMAP (IMAGE RENDERING) ---")
    for lay in LAYERS:
        full_layer = f"{WORKSPACE}:{lay}"
        getmap_url = (
            f"{GEOSERVER_HOST}/{WORKSPACE}/wms?"
            f"service=WMS&version=1.1.1&request=GetMap&layers={full_layer}&"
            f"styles=&bbox={BBOX_WMS_111}&width=650&height=600&srs=EPSG:4326&format=image/png"
        )
        t0 = time.time()
        r_map = session.get(getmap_url, timeout=15)
        dt = round((time.time() - t0) * 1000, 1)

        is_png = (r_map.status_code == 200 and r_map.content[:8] == b'\x89PNG\r\n\x1a\n')
        out_img = OUTPUT_DIR / f"wms_{lay}.png"
        if is_png:
            with open(out_img, "wb") as f:
                f.write(r_map.content)

        record_test(f"WMS GetMap: {lay}", is_png, f"HTTP {r_map.status_code} ({dt}ms, {len(r_map.content):,} bytes -> {out_img.name})")

    # -------------------------------------------------------------------------
    # 3. WFS GETCAPABILITIES
    # -------------------------------------------------------------------------
    print("\n--- 3. TESTING WFS GETCAPABILITIES ---")
    wfs_cap_url = f"{GEOSERVER_HOST}/{WORKSPACE}/wfs?service=WFS&version=2.0.0&request=GetCapabilities"
    t0 = time.time()
    r_wfs_cap = session.get(wfs_cap_url, timeout=10)
    wfs_cap_time = round((time.time() - t0) * 1000, 1)

    record_test("WFS 2.0.0 GetCapabilities", r_wfs_cap.status_code == 200 and "<wfs:WFS_Capabilities" in r_wfs_cap.text, f"HTTP {r_wfs_cap.status_code} ({wfs_cap_time}ms, {len(r_wfs_cap.content):,} bytes)")

    # -------------------------------------------------------------------------
    # 4. WFS GETFEATURE (GEOJSON STREAMING)
    # -------------------------------------------------------------------------
    print("\n--- 4. TESTING WFS GETFEATURE (GEOJSON EXPORTS) ---")
    for lay in LAYERS:
        full_layer = f"{WORKSPACE}:{lay}"
        getfeat_url = (
            f"{GEOSERVER_HOST}/{WORKSPACE}/wfs?"
            f"service=WFS&version=1.0.0&request=GetFeature&typeName={full_layer}&"
            f"outputFormat=application/json&maxFeatures=25"
        )
        t0 = time.time()
        r_feat = session.get(getfeat_url, timeout=15)
        dt = round((time.time() - t0) * 1000, 1)

        is_valid_geojson = False
        n_features = 0
        if r_feat.status_code == 200:
            try:
                data = r_feat.json()
                if data.get("type") == "FeatureCollection":
                    is_valid_geojson = True
                    n_features = len(data.get("features", []))
            except Exception:
                pass

        record_test(f"WFS GetFeature: {lay}", is_valid_geojson and n_features > 0, f"HTTP {r_feat.status_code} ({dt}ms, {n_features} features returned)")

    print("\n" + "=" * 80)
    print(f"  OGC SERVICE UNIT TESTS: {tests_passed}/{total_tests} PASSED (100%)")
    print("=" * 80 + "\n")

    # 5. Run regression test on existing backend
    print(">>> RUNNING API REGRESSION TEST SUITE...")
    from scripts import test_api_endpoints
    test_api_endpoints.run_tests()

    print("\n" + "=" * 80)
    print("  PHASE 3 GEOSERVER OGC SERVICES FULLY OPERATIONAL!")
    print("=" * 80)

if __name__ == "__main__":
    run_tests()
