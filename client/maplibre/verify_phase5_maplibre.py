"""
SmartServe GIS - Phase 5 MapLibre GL JS Verification Suite
Validates all Phase 5 frontend assets, DOM elements, spatial dataset routes,
HTTP Range request support for PMTiles, and regression test against backend APIs.
"""

import os
import sys
import time
import json
import socket
import urllib.request
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CLIENT_DIR = PROJECT_ROOT / "client" / "maplibre"

def run_check(title, condition, details=""):
    status = "PASS" if condition else "FAIL"
    symbol = "✔" if condition else "✖"
    print(f"[{status}] {symbol} {title}")
    if details:
        print(f"       └─ {details}")
    return condition

def main():
    print("=" * 75)
    print("  SMARTSERVE GIS - PHASE 5 MAPLIBRE FRONTEND VERIFICATION SUITE")
    print("=" * 75)

    passed_tests = 0
    total_tests = 0

    # -------------------------------------------------------------------------
    # TEST GROUP 1: File Existence & Integrity
    # -------------------------------------------------------------------------
    print("\n--- 1. MapLibre Frontend File Assets ---")
    files_to_check = [
        ("index.html", CLIENT_DIR / "index.html"),
        ("style.css", CLIENT_DIR / "css" / "style.css"),
        ("app.js", CLIENT_DIR / "js" / "app.js"),
        ("serve.py", CLIENT_DIR / "serve.py"),
        ("run_maplibre.bat", CLIENT_DIR / "run_maplibre.bat")
    ]
    for name, path in files_to_check:
        total_tests += 1
        exists = path.exists() and path.stat().st_size > 100
        size_kb = path.stat().st_size / 1024 if path.exists() else 0
        if run_check(f"Asset: {name}", exists, f"Path: {path.name} ({size_kb:.1f} KB)"):
            passed_tests += 1

    # -------------------------------------------------------------------------
    # TEST GROUP 2: DOM Elements in index.html
    # -------------------------------------------------------------------------
    print("\n--- 2. Required DOM Interactive Controls ---")
    html_content = (CLIENT_DIR / "index.html").read_text(encoding="utf-8")
    dom_requirements = [
        ("Map Container (#map)", 'id="map"'),
        ("Sidebar Container (#sidebar)", 'id="sidebar"'),
        ("Tile Engine Switcher (#select-tile-source)", 'id="select-tile-source"'),
        ("Basemap Switcher (#select-basemap)", 'id="select-basemap"'),
        ("Speed Scenario Dropdown (#select-speed)", 'id="select-speed"'),
        ("Facility Target Dropdown (#select-target)", 'id="select-target"'),
        ("Isochrone Opacity Slider (#slider-opacity)", 'id="slider-opacity"'),
        ("Real-Time Metrics HUD (#metrics-hud)", 'id="metrics-hud"'),
        ("Quick Reset Extent Button (#btn-reset-view)", 'id="btn-reset-view"'),
        ("Quick 3D Pitch Button (#btn-toggle-pitch)", 'id="btn-toggle-pitch"'),
        ("Back to Leaflet Link Button (#btn-back-leaflet)", 'id="btn-back-leaflet"'),
        ("PMTiles Client Library Inclusion", 'pmtiles@3.0.7'),
        ("MapLibre GL JS CSS & JS Inclusions", 'maplibre-gl.css')
    ]
    for label, substr in dom_requirements:
        total_tests += 1
        found = substr in html_content
        if run_check(f"DOM Control: {label}", found):
            passed_tests += 1

    # -------------------------------------------------------------------------
    # TEST GROUP 3: Spatial Datasets Referenced by Client
    # -------------------------------------------------------------------------
    print("\n--- 3. Client Spatial Datasets (GeoJSON & PMTiles) ---")
    datasets_to_check = [
        ("PMC Municipal Boundary", PROJECT_ROOT / "data" / "boundary" / "pmc.geojson"),
        ("Walking Isochrones GeoJSON", PROJECT_ROOT / "data" / "analysis" / "pmc_walking_isochrones.geojson"),
        ("H3 Res 8 Hexagons GeoJSON", PROJECT_ROOT / "data" / "analysis" / "pmc_h3_accessibility_res8.geojson"),
        ("Population Grid GeoJSON", PROJECT_ROOT / "data" / "analysis" / "pmc_population_grid.geojson"),
        ("Services POI PMTiles Archive", PROJECT_ROOT / "data" / "pmtiles" / "pmc_services.pmtiles"),
        ("Isochrones PMTiles Archive", PROJECT_ROOT / "data" / "pmtiles" / "pmc_isochrones.pmtiles"),
        ("H3 Accessibility PMTiles Archive", PROJECT_ROOT / "data" / "pmtiles" / "pmc_h3.pmtiles")
    ]
    for label, path in datasets_to_check:
        total_tests += 1
        exists = path.exists() and path.stat().st_size > 500
        size_kb = path.stat().st_size / 1024 if path.exists() else 0
        if run_check(f"Dataset: {label}", exists, f"Size: {size_kb:.1f} KB"):
            passed_tests += 1

    # -------------------------------------------------------------------------
    # TEST GROUP 4: Static HTTP Server & Range Request Probing
    # -------------------------------------------------------------------------
    print("\n--- 4. HTTP Server & RFC 7233 Range Request Live Test ---")
    server_process = subprocess.Popen([sys.executable, str(CLIENT_DIR / "serve.py")])
    time.sleep(1.8)

    try:
        # Test 4.1: Root Index
        total_tests += 1
        req1 = urllib.request.urlopen("http://127.0.0.1:5600/")
        c1 = req1.getcode() == 200 and "SmartServe GIS" in req1.read().decode("utf-8")
        if run_check("HTTP 200: Root / (index.html)", c1):
            passed_tests += 1

        # Test 4.2: CSS Stylesheet
        total_tests += 1
        req2 = urllib.request.urlopen("http://127.0.0.1:5600/css/style.css")
        c2 = req2.getcode() == 200 and req2.headers.get("Content-Type") == "text/css"
        if run_check("HTTP 200: /css/style.css (MIME text/css)", c2):
            passed_tests += 1

        # Test 4.3: JavaScript Client
        total_tests += 1
        req3 = urllib.request.urlopen("http://127.0.0.1:5600/js/app.js")
        c3 = req3.getcode() == 200 and "CONFIG" in req3.read().decode("utf-8")
        if run_check("HTTP 200: /js/app.js (Main Logic)", c3):
            passed_tests += 1

        # Test 4.4: Static GeoJSON Routed to Project Root
        total_tests += 1
        req4 = urllib.request.urlopen("http://127.0.0.1:5600/data/boundary/pmc.geojson")
        body4 = req4.read().decode("utf-8")
        c4 = req4.getcode() == 200 and "FeatureCollection" in body4
        if run_check("HTTP 200: /data/boundary/pmc.geojson (Root Route)", c4, f"Bytes: {len(body4)}"):
            passed_tests += 1

        # Test 4.5: PMTiles HTTP Range Request (RFC 7233)
        total_tests += 1
        range_req = urllib.request.Request("http://127.0.0.1:5600/data/pmtiles/pmc_services.pmtiles", headers={"Range": "bytes=0-511"})
        range_res = urllib.request.urlopen(range_req)
        c5 = (range_res.getcode() == 206 and 
              range_res.headers.get("Content-Range") is not None and 
              len(range_res.read()) == 512)
        if run_check("HTTP 206: PMTiles Range Request (bytes 0-511)", c5, f"Content-Range: {range_res.headers.get('Content-Range')}"):
            passed_tests += 1

    finally:
        server_process.terminate()
        server_process.wait()

    # -------------------------------------------------------------------------
    # TEST GROUP 5: Cross-Link Verification in Leaflet
    # -------------------------------------------------------------------------
    print("\n--- 5. Leaflet Frontend Cross-Link Integration ---")
    total_tests += 1
    leaflet_html = (PROJECT_ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    has_maplibre_link = "5600" in leaflet_html and "btn-switch-maplibre" in leaflet_html
    if run_check("Cross-Link: Leaflet -> MapLibre (Port 5600)", has_maplibre_link):
        passed_tests += 1

    # -------------------------------------------------------------------------
    # SUMMARY REPORT
    # -------------------------------------------------------------------------
    print("\n" + "=" * 75)
    pass_pct = (passed_tests / total_tests) * 100
    print(f"  PHASE 5 VERIFICATION RESULT: {passed_tests}/{total_tests} PASSED ({pass_pct:.1f}%)")
    print("=" * 75)

    if passed_tests == total_tests:
        print("[SUCCESS] All Phase 5 MapLibre components verified and operational!")
        return 0
    else:
        print(f"[FAIL] {total_tests - passed_tests} test(s) failed.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
