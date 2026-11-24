-- ============================================================================
-- SmartServe GIS - Docker Initialization SQL Script
-- Combined Base Schema & Experiential Learning Schema Extensions
-- ============================================================================

-- 1. Enable PostGIS Extension
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;

-- 2. Base Categories Table
CREATE TABLE IF NOT EXISTS categories (
    id SERIAL PRIMARY KEY,
    category VARCHAR(64) NOT NULL,
    subcategory VARCHAR(64) NOT NULL UNIQUE,
    slug VARCHAR(64) NOT NULL UNIQUE,
    icon VARCHAR(10) NOT NULL,
    color VARCHAR(20) NOT NULL DEFAULT '#3182ce',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. Base Boundaries Table
CREATE TABLE IF NOT EXISTS study_area_boundaries (
    id SERIAL PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    municipality VARCHAR(20),
    area_sqkm DOUBLE PRECISION,
    source VARCHAR(100) DEFAULT 'DataMeet / OpenStreetMap',
    geom GEOMETRY(MultiPolygon, 4326) NOT NULL
);

-- 4. Base Services POI Table
CREATE TABLE IF NOT EXISTS services (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(64) NOT NULL,
    subcategory VARCHAR(64) NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    address TEXT,
    phone VARCHAR(100),
    website VARCHAR(255),
    opening_hours VARCHAR(255),
    operator VARCHAR(150),
    brand VARCHAR(150),
    wheelchair VARCHAR(50),
    municipality VARCHAR(10) NOT NULL CHECK (municipality IN ('PMC', 'PCMC')),
    osm_id VARCHAR(50),
    source VARCHAR(50) DEFAULT 'OpenStreetMap',
    geom GEOMETRY(Point, 4326) NOT NULL,
    geog GEOGRAPHY(Point, 4326) GENERATED ALWAYS AS (geom::geography) STORED,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_services_geom ON services USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_services_geog ON services USING GIST (geog);
CREATE INDEX IF NOT EXISTS idx_services_cat_muni ON services (category, municipality);
CREATE INDEX IF NOT EXISTS idx_services_subcat ON services (subcategory);
CREATE INDEX IF NOT EXISTS idx_boundaries_geom ON study_area_boundaries USING GIST (geom);

-- 5. Walking Network Nodes
CREATE TABLE IF NOT EXISTS walking_network_nodes (
    osmid BIGINT PRIMARY KEY,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    street_count INTEGER DEFAULT 1,
    municipality VARCHAR(10) NOT NULL DEFAULT 'PMC',
    geom GEOMETRY(Point, 4326) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_walking_nodes_geom ON walking_network_nodes USING GIST (geom);

-- 6. Walking Network Edges
CREATE TABLE IF NOT EXISTS walking_network_edges (
    id SERIAL PRIMARY KEY,
    u BIGINT NOT NULL,
    v BIGINT NOT NULL,
    key INTEGER NOT NULL DEFAULT 0,
    osmid VARCHAR(250),
    name VARCHAR(250),
    highway VARCHAR(50),
    oneway BOOLEAN DEFAULT FALSE,
    length_m DOUBLE PRECISION NOT NULL,
    walk_time_min_normal DOUBLE PRECISION NOT NULL,
    walk_time_min_slower DOUBLE PRECISION NOT NULL,
    municipality VARCHAR(10) NOT NULL DEFAULT 'PMC',
    geom GEOMETRY(LineString, 4326) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_walking_edges_geom ON walking_network_edges USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_walking_edges_uv ON walking_network_edges (u, v);

-- 7. Accessibility Isochrones
CREATE TABLE IF NOT EXISTS accessibility_isochrones (
    id SERIAL PRIMARY KEY,
    target_type VARCHAR(50) NOT NULL,
    speed_scenario VARCHAR(50) NOT NULL,
    speed_kmh DOUBLE PRECISION NOT NULL,
    cutoff_minutes INTEGER NOT NULL,
    area_sqkm DOUBLE PRECISION NOT NULL,
    coverage_pct_pmc DOUBLE PRECISION NOT NULL,
    municipality VARCHAR(10) NOT NULL DEFAULT 'PMC',
    geom GEOMETRY(MultiPolygon, 4326) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_isochrones_geom ON accessibility_isochrones USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_isochrones_filter ON accessibility_isochrones (target_type, speed_scenario, cutoff_minutes);

-- 8. H3 Hexagonal Grid
CREATE TABLE IF NOT EXISTS h3_accessibility (
    h3_index VARCHAR(20) PRIMARY KEY,
    resolution INTEGER NOT NULL CHECK (resolution BETWEEN 7 AND 10),
    municipality VARCHAR(10) NOT NULL DEFAULT 'PMC',
    hospital_count INTEGER NOT NULL DEFAULT 0,
    clinic_count INTEGER NOT NULL DEFAULT 0,
    total_healthcare_count INTEGER NOT NULL DEFAULT 0,
    has_facility BOOLEAN NOT NULL DEFAULT FALSE,
    is_accessible_15min_normal BOOLEAN NOT NULL DEFAULT FALSE,
    is_accessible_15min_slower BOOLEAN NOT NULL DEFAULT FALSE,
    min_dist_to_hospital_m DOUBLE PRECISION,
    min_dist_to_clinic_m DOUBLE PRECISION,
    area_sqkm DOUBLE PRECISION NOT NULL DEFAULT 0.737,
    geom GEOMETRY(Polygon, 4326) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_h3_accessibility_geom ON h3_accessibility USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_h3_resolution ON h3_accessibility (resolution);

-- 9. Population Grid
CREATE TABLE IF NOT EXISTS population_grid (
    cell_id VARCHAR(50) PRIMARY KEY,
    source VARCHAR(100) NOT NULL DEFAULT 'WorldPop / GHSL Synthetic Model',
    resolution_m INTEGER NOT NULL DEFAULT 100,
    estimated_population DOUBLE PRECISION NOT NULL,
    density_per_sqkm DOUBLE PRECISION NOT NULL,
    is_accessible_15min_normal BOOLEAN NOT NULL DEFAULT FALSE,
    is_accessible_15min_slower BOOLEAN NOT NULL DEFAULT FALSE,
    municipality VARCHAR(10) NOT NULL DEFAULT 'PMC',
    geom GEOMETRY(Polygon, 4326) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_population_grid_geom ON population_grid USING GIST (geom);

-- 10. Accessibility Summary
CREATE TABLE IF NOT EXISTS accessibility_summary (
    id SERIAL PRIMARY KEY,
    target_type VARCHAR(50) NOT NULL,
    speed_scenario VARCHAR(50) NOT NULL,
    speed_kmh DOUBLE PRECISION NOT NULL,
    cutoff_minutes INTEGER NOT NULL,
    accessible_area_sqkm DOUBLE PRECISION NOT NULL,
    pmc_coverage_pct DOUBLE PRECISION NOT NULL,
    accessible_population BIGINT,
    accessible_population_pct DOUBLE PRECISION,
    accessible_h3_cells_res8 INTEGER,
    gap_h3_cells_res8 INTEGER,
    calculated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
