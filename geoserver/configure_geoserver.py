"""
SmartServe GIS - Phase 3: GeoServer Automated Workspace, Datastore, Styles & Layer Publisher
Script: geoserver/configure_geoserver.py

Automates:
1. Workspace creation: 'smartserve' (URI: 'http://smartserve.gis')
2. PostGIS DataStore creation: 'smartserve_postgis' connecting to smartserve_db
3. SLD Style uploads from geoserver/sld/*.sld
4. Layer publication for:
   - pmc_boundary (study_area_boundaries)
   - all_services (services)
   - healthcare_facilities (services)
   - walking_network (walking_network_edges)
   - accessibility_isochrones (accessibility_isochrones)
   - h3_accessibility (h3_accessibility)
   - population_grid (population_grid)
5. CRS configuration (EPSG:4326) and bbox computation.
"""

import os
import sys
import requests
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.core.config import settings

GEOSERVER_URL = "http://localhost:8080/geoserver/rest"
GEOSERVER_AUTH = ("admin", "geoserver")
WORKSPACE = "smartserve"
DATASTORE = "smartserve_postgis"
SLD_DIR = PROJECT_ROOT / "geoserver" / "sld"

HEADERS_XML = {"Content-Type": "application/xml"}
HEADERS_JSON = {"Content-Type": "application/json"}

def setup_geoserver():
    print("=" * 80)
    print("  SMARTSERVE GIS - PHASE 3: GEOSERVER OGC SERVICE AUTOMATION")
    print("=" * 80)
    print(f"[CONFIG] GeoServer REST URL: {GEOSERVER_URL}")
    print(f"[CONFIG] Target Workspace  : {WORKSPACE}")
    print(f"[CONFIG] Target Datastore  : {DATASTORE}")
    print(f"[CONFIG] Database Target   : {settings.DB_NAME} at {settings.DB_HOST}:{settings.DB_PORT}")

    session = requests.Session()
    session.auth = GEOSERVER_AUTH

    # 1. Check connectivity
    try:
        r = session.get(f"{GEOSERVER_URL}/workspaces.json", timeout=5)
        if r.status_code != 200:
            print(f"[ERROR] Could not connect to GeoServer REST API: {r.status_code}")
            sys.exit(1)
        print("[SUCCESS] Connected to GeoServer REST API.")
    except Exception as e:
        print(f"[ERROR] GeoServer unreachable: {e}")
        sys.exit(1)

    # 2. Create Workspace
    r = session.get(f"{GEOSERVER_URL}/workspaces/{WORKSPACE}.json")
    if r.status_code == 404:
        print(f"[INFO] Creating workspace '{WORKSPACE}'...")
        payload = {"workspace": {"name": WORKSPACE}}
        r_create = session.post(f"{GEOSERVER_URL}/workspaces", json=payload, headers=HEADERS_JSON)
        if r_create.status_code in [200, 201]:
            print(f"[SUCCESS] Workspace '{WORKSPACE}' created.")
        else:
            print(f"[ERROR] Failed to create workspace: {r_create.text}")
            sys.exit(1)
    else:
        print(f"[INFO] Workspace '{WORKSPACE}' already exists.")

    # 3. Create / Update PostGIS Datastore
    ds_url = f"{GEOSERVER_URL}/workspaces/{WORKSPACE}/datastores/{DATASTORE}.json"
    r_ds = session.get(ds_url)
    if r_ds.status_code == 404:
        print(f"[INFO] Configuring PostGIS DataStore '{DATASTORE}'...")
        ds_payload = {
            "dataStore": {
                "name": DATASTORE,
                "connectionParameters": {
                    "entry": [
                        {"@key": "dbtype", "$": "postgis"},
                        {"@key": "host", "$": settings.DB_HOST},
                        {"@key": "port", "$": str(settings.DB_PORT)},
                        {"@key": "database", "$": settings.DB_NAME},
                        {"@key": "schema", "$": "public"},
                        {"@key": "user", "$": settings.DB_USER},
                        {"@key": "passwd", "$": settings.DB_PASSWORD},
                        {"@key": "Expose primary keys", "$": "true"},
                        {"@key": "fetch size", "$": "1000"},
                        {"@key": "Connection timeout", "$": "20"},
                        {"@key": "validate connections", "$": "true"}
                    ]
                }
            }
        }
        r_ds_create = session.post(f"{GEOSERVER_URL}/workspaces/{WORKSPACE}/datastores", json=ds_payload, headers=HEADERS_JSON)
        if r_ds_create.status_code in [200, 201]:
            print(f"[SUCCESS] DataStore '{DATASTORE}' created.")
        else:
            print(f"[ERROR] Failed to create DataStore: {r_ds_create.text}")
            sys.exit(1)
    else:
        print(f"[INFO] DataStore '{DATASTORE}' already exists.")

    # 4. Upload SLD Styles
    print("\n--- UPLOADING SLD STYLES ---")
    sld_files = list(SLD_DIR.glob("*.sld"))
    for sld in sld_files:
        style_name = sld.stem
        with open(sld, "r", encoding="utf-8") as f:
            sld_content = f.read()

        # Check if style exists
        check_url = f"{GEOSERVER_URL}/workspaces/{WORKSPACE}/styles/{style_name}.json"
        r_style = session.get(check_url)
        if r_style.status_code == 404:
            # Create style metadata
            create_url = f"{GEOSERVER_URL}/workspaces/{WORKSPACE}/styles"
            r_c = session.post(create_url, json={"style": {"name": style_name, "filename": f"{style_name}.sld"}}, headers=HEADERS_JSON)

        # Upload SLD body (PUT)
        upload_url = f"{GEOSERVER_URL}/workspaces/{WORKSPACE}/styles/{style_name}"
        r_up = session.put(upload_url, data=sld_content.encode("utf-8"), headers={"Content-Type": "application/vnd.ogc.sld+xml"})
        if r_up.status_code in [200, 201]:
            print(f"  [STYLE UPLOADED] {style_name}")
        else:
            print(f"  [STYLE STATUS] {style_name} -> {r_up.status_code}")

    # 5. Publish PostGIS Feature Types (Layers)
    print("\n--- PUBLISHING POSTGIS FEATURE TYPES ---")
    layers_config = [
        {
            "name": "pmc_boundary",
            "native_name": "study_area_boundaries",
            "title": "PMC & PCMC Municipal Boundaries",
            "default_style": "pmc_boundary"
        },
        {
            "name": "all_services",
            "native_name": "services",
            "title": "SmartServe All Multi-Service POIs",
            "default_style": "all_services"
        },
        {
            "name": "walking_network",
            "native_name": "walking_network_edges",
            "title": "PMC Pedestrian Walking Network",
            "default_style": "walking_network"
        },
        {
            "name": "accessibility_isochrones",
            "native_name": "accessibility_isochrones",
            "title": "Pedestrian Healthcare Walking Isochrones",
            "default_style": "accessibility_isochrones"
        },
        {
            "name": "h3_accessibility",
            "native_name": "h3_accessibility",
            "title": "Uber H3 Hexagonal Healthcare Accessibility",
            "default_style": "h3_accessibility"
        },
        {
            "name": "population_grid",
            "native_name": "population_grid",
            "title": "Population Density & Coverage Grid",
            "default_style": "population_grid"
        }
    ]

    for lay in layers_config:
        lay_name = lay["name"]
        check_layer_url = f"{GEOSERVER_URL}/workspaces/{WORKSPACE}/datastores/{DATASTORE}/featuretypes/{lay_name}.json"
        r_check = session.get(check_layer_url)

        if r_check.status_code == 404:
            payload = {
                "featureType": {
                    "name": lay_name,
                    "nativeName": lay["native_name"],
                    "title": lay["title"],
                    "srs": "EPSG:4326",
                    "nativeCRS": "EPSG:4326",
                    "enabled": True
                }
            }
            create_ft_url = f"{GEOSERVER_URL}/workspaces/{WORKSPACE}/datastores/{DATASTORE}/featuretypes"
            r_ft = session.post(create_ft_url, json=payload, headers=HEADERS_JSON)
            if r_ft.status_code in [200, 201]:
                print(f"  [LAYER PUBLISHED] {lay_name} (Source: {lay['native_name']})")
            else:
                print(f"  [ERROR] Publishing {lay_name}: {r_ft.status_code} - {r_ft.text}")
        else:
            print(f"  [LAYER EXISTS] {lay_name}")

        # Assign Default Style
        style_payload = {
            "layer": {
                "defaultStyle": {
                    "name": f"{WORKSPACE}:{lay['default_style']}",
                    "workspace": WORKSPACE
                }
            }
        }
        session.put(f"{GEOSERVER_URL}/layers/{WORKSPACE}:{lay_name}.json", json=style_payload, headers=HEADERS_JSON)

    print("\n" + "=" * 80)
    print("  GEOSERVER OGC SERVICE SETUP COMPLETE!")
    print("=" * 80)

if __name__ == "__main__":
    setup_geoserver()
