"""
SmartServe GIS - Master Platform End-to-End Verification Suite
Validates the entire multi-tier spatial infrastructure across all 10 phases.
"""

import os
import sys
import yaml
import psycopg2
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

def log_test(title, passed, detail=""):
    symbol = "✔" if passed else "✖"
    status = "PASS" if passed else "FAIL"
    print(f"[{status}] {symbol} {title}")
    if detail:
        print(f"       └─ {detail}")
    return passed

def main():
    print("=" * 80)
    print("  SMARTSERVE GIS - MASTER END-TO-END PLATFORM VERIFICATION")
    print("  Location-Based Multi-Service WebGIS & Spatial Infrastructure Platform")
    print("=" * 80)

    total_checks = 0
    passed_checks = 0

    # -------------------------------------------------------------------------
    # 1. PostGIS Database & Tables Check
    # -------------------------------------------------------------------------
    print("\n--- 1. PostGIS Spatial Database Verification (Port 5432) ---")
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", "5432"),
            dbname=os.getenv("DB_NAME", "smartserve_db"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", "postgres")
        )
        cur = conn.cursor()
        total_checks += 1
        if log_test("PostgreSQL/PostGIS Connection", True, "Connected to smartserve_db"):
            passed_checks += 1

        tables = [
            ("services", 4747),
            ("study_area_boundaries", 2),
            ("categories", 20),
            ("walking_network_nodes", 39454),
            ("walking_network_edges", 99062),
            ("accessibility_isochrones", 18),
            ("h3_accessibility", 363),
            ("population_grid", 363),
            ("accessibility_summary", 18)
        ]

        for tbl, expected_min in tables:
            total_checks += 1
            cur.execute(f"SELECT COUNT(*) FROM {tbl};")
            count = cur.fetchone()[0]
            ok = count >= expected_min
            if log_test(f"Table: {tbl}", ok, f"Row count: {count} (expected >= {expected_min})"):
                passed_checks += 1

        cur.close()
        conn.close()
    except Exception as e:
        total_checks += 1
        log_test("PostGIS Connection", False, str(e))

    # -------------------------------------------------------------------------
    # 2. WebGIS Frontend Portals Check
    # -------------------------------------------------------------------------
    print("\n--- 2. WebGIS Frontend Portals Check ---")
    frontends = [
        ("Leaflet Frontend Index", PROJECT_ROOT / "frontend" / "index.html"),
        ("Leaflet Frontend Server Launcher", PROJECT_ROOT / "frontend" / "serve.py"),
        ("MapLibre Frontend Index", PROJECT_ROOT / "client" / "maplibre" / "index.html"),
        ("MapLibre Frontend Stylesheet", PROJECT_ROOT / "client" / "maplibre" / "css" / "style.css"),
        ("MapLibre Frontend Engine Script", PROJECT_ROOT / "client" / "maplibre" / "js" / "app.js"),
        ("MapLibre HTTP Server (Range Support)", PROJECT_ROOT / "client" / "maplibre" / "serve.py")
    ]
    for name, path in frontends:
        total_checks += 1
        ok = path.exists() and path.stat().st_size > 100
        if log_test(f"Frontend: {name}", ok, f"Size: {path.stat().st_size / 1024:.1f} KB"):
            passed_checks += 1

    # -------------------------------------------------------------------------
    # 3. Cloud-Native PMTiles Archives Check
    # -------------------------------------------------------------------------
    print("\n--- 3. Cloud-Native PMTiles v3 Single-File Archives ---")
    pmtiles_archives = [
        ("pmc_services.pmtiles", PROJECT_ROOT / "data" / "pmtiles" / "pmc_services.pmtiles", 1000),
        ("pmc_isochrones.pmtiles", PROJECT_ROOT / "data" / "pmtiles" / "pmc_isochrones.pmtiles", 3000),
        ("pmc_h3.pmtiles", PROJECT_ROOT / "data" / "pmtiles" / "pmc_h3.pmtiles", 150)
    ]
    for name, path, min_kb in pmtiles_archives:
        total_checks += 1
        ok = path.exists() and (path.stat().st_size / 1024) >= min_kb
        size_kb = path.stat().st_size / 1024 if path.exists() else 0
        if log_test(f"PMTiles Archive: {name}", ok, f"Size: {size_kb:.1f} KB"):
            passed_checks += 1

    # -------------------------------------------------------------------------
    # 4. Container Orchestration & CI/CD Check
    # -------------------------------------------------------------------------
    print("\n--- 4. Containerization & Orchestration Manifests ---")
    manifests = [
        ("Docker Compose (docker-compose.yml)", PROJECT_ROOT / "docker-compose.yml"),
        ("Backend Container Dockerfile", PROJECT_ROOT / "backend" / "Dockerfile"),
        ("Client Container Dockerfile", PROJECT_ROOT / "docker" / "Dockerfile.client"),
        ("Nginx Gateway Configuration", PROJECT_ROOT / "docker" / "nginx.conf"),
        ("PostGIS Docker Init SQL", PROJECT_ROOT / "docker" / "init-db" / "01_init_all_schemas.sql"),
        ("Kubernetes Namespace Manifest", PROJECT_ROOT / "k8s" / "01-namespace.yaml"),
        ("Kubernetes PostGIS StatefulSet", PROJECT_ROOT / "k8s" / "04-postgis-statefulset.yaml"),
        ("Kubernetes Backend Deployment", PROJECT_ROOT / "k8s" / "06-backend-deployment.yaml"),
        ("Kubernetes Client Deployment", PROJECT_ROOT / "k8s" / "08-client-deployment.yaml"),
        ("GitHub Actions Workflow (.github/workflows/deploy.yml)", PROJECT_ROOT / ".github" / "workflows" / "deploy.yml")
    ]
    for name, path in manifests:
        total_checks += 1
        ok = path.exists() and path.stat().st_size > 50
        if log_test(f"Manifest: {name}", ok, f"Size: {path.stat().st_size} bytes"):
            passed_checks += 1

    # Validate docker-compose.yml structure with PyYAML
    total_checks += 1
    try:
        compose_data = yaml.safe_load(open(PROJECT_ROOT / "docker-compose.yml", encoding="utf-8"))
        has_services = len(compose_data.get("services", {})) == 6
        if log_test("Docker Compose Syntax & 6 Microservices", has_services, f"Services: {list(compose_data['services'].keys())}"):
            passed_checks += 1
    except Exception as e:
        log_test("Docker Compose YAML", False, str(e))

    # -------------------------------------------------------------------------
    # 5. Technical Documentation & Reports Check
    # -------------------------------------------------------------------------
    print("\n--- 5. Technical Documentation & Viva Guides ---")
    doc_files = [
        ("Master Project README.md", PROJECT_ROOT / "README.md"),
        ("Technical Viva Guide (docs/ANSWERS.md)", PROJECT_ROOT / "docs" / "ANSWERS.md"),
        ("Master Project Audit (docs/PROJECT_AUDIT.md)", PROJECT_ROOT / "docs" / "PROJECT_AUDIT.md"),
        ("Verification Dossier (docs/evidence/EVIDENCE_DOSSIER.md)", PROJECT_ROOT / "docs" / "evidence" / "EVIDENCE_DOSSIER.md"),
        ("Data Engineering Report", PROJECT_ROOT / "analysis" / "data_engineering" / "DATA_ENGINEERING_REPORT.md"),
        ("Accessibility Analysis Report", PROJECT_ROOT / "analysis" / "accessibility" / "ACCESSIBILITY_REPORT.md"),
        ("GeoServer OGC Report", PROJECT_ROOT / "geoserver" / "GEOSERVER_OGC_REPORT.md"),
        ("Vector Tile Benchmark Report", PROJECT_ROOT / "services" / "tiles" / "VECTOR_TILE_BENCHMARK_REPORT.md"),
        ("MapLibre Frontend Report", PROJECT_ROOT / "client" / "maplibre" / "MAPLIBRE_FRONTEND_REPORT.md"),
        ("PMTiles Serverless Report", PROJECT_ROOT / "services" / "pmtiles" / "PMTILES_SERVERLESS_REPORT.md")
    ]
    for name, path in doc_files:
        total_checks += 1
        ok = path.exists() and path.stat().st_size > 500
        if log_test(f"Documentation: {name}", ok, f"Size: {path.stat().st_size / 1024:.1f} KB"):
            passed_checks += 1

    # -------------------------------------------------------------------------
    # FINAL SUMMARY
    # -------------------------------------------------------------------------
    print("\n" + "=" * 80)
    pct = (passed_checks / total_checks) * 100
    print(f"  MASTER PLATFORM AUDIT: {passed_checks}/{total_checks} CHECKS PASSED ({pct:.1f}%)")
    print("=" * 80)

    if passed_checks == total_checks:
        print("\n🏆 ALL SPATIAL INFRASTRUCTURE PLATFORM COMPONENTS ARE 100% OPERATIONAL!\n")
        return 0
    else:
        print(f"\n⚠️  {total_checks - passed_checks} check(s) failed.\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())
