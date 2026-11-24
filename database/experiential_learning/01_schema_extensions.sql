-- ============================================================================
-- SmartServe GIS - Experiential Learning: PostGIS Database Schema Extensions
-- Directory: database/experiential_learning/01_schema_extensions.sql
-- Database: smartserve_db
-- ============================================================================
-- Purpose:
-- Extends the spatial database with tables for:
-- 1. Walking network topology (nodes & edges)
-- 2. Pedestrian accessibility isochrones (5, 10, 15 min at 4.8 km/h & 3.6 km/h)
-- 3. H3 hexagonal spatial aggregation (Resolution 8 & 9)
-- 4. Population accessibility grid & coverage metrics
-- 5. Accessibility scenario comparison summary table
--
-- STRICT PRESERVATION:
-- Reuses existing 'services', 'categories', and 'study_area_boundaries' tables.
-- Does NOT drop, alter, or duplicate existing tables.
-- ============================================================================

-- Ensure PostGIS is enabled
CREATE EXTENSION IF NOT EXISTS postgis;

-- ----------------------------------------------------------------------------
-- 1. WALKING NETWORK NODES
-- Stores intersection points and dead-ends extracted from OSM pedestrian network
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS walking_network_nodes (
    node_id BIGINT PRIMARY KEY,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    municipality VARCHAR(10) NOT NULL DEFAULT 'PMC' CHECK (municipality IN ('PMC', 'PCMC')),
    geom GEOMETRY(Point, 4326) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_walking_nodes_geom_valid CHECK (ST_IsValid(geom))
);

-- Spatial index on walking network nodes
CREATE INDEX IF NOT EXISTS idx_walking_nodes_geom 
    ON walking_network_nodes USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_walking_nodes_muni 
    ON walking_network_nodes (municipality);

COMMENT ON TABLE walking_network_nodes IS 'Graph vertices for PMC walkable street network';

-- ----------------------------------------------------------------------------
-- 2. WALKING NETWORK EDGES
-- Stores walkable street segments with lengths, travel times, and line geometries
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS walking_network_edges (
    edge_id BIGSERIAL PRIMARY KEY,
    u BIGINT NOT NULL,
    v BIGINT NOT NULL,
    key INTEGER NOT NULL DEFAULT 0,
    osmid VARCHAR(100),
    highway VARCHAR(64),
    name VARCHAR(255),
    oneway BOOLEAN DEFAULT FALSE,
    length_meters DOUBLE PRECISION NOT NULL,
    travel_time_normal_sec DOUBLE PRECISION NOT NULL,  -- At 4.8 km/h (1.333 m/s)
    travel_time_slower_sec DOUBLE PRECISION NOT NULL,  -- At 3.6 km/h (1.000 m/s)
    municipality VARCHAR(10) NOT NULL DEFAULT 'PMC',
    geom GEOMETRY(LineString, 4326) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_walking_edges_geom_valid CHECK (ST_IsValid(geom))
);

-- Indexes on walking network edges
CREATE INDEX IF NOT EXISTS idx_walking_edges_geom 
    ON walking_network_edges USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_walking_edges_uv 
    ON walking_network_edges (u, v);
CREATE INDEX IF NOT EXISTS idx_walking_edges_highway 
    ON walking_network_edges (highway);

COMMENT ON TABLE walking_network_edges IS 'Graph edges representing walkable street segments with travel impedance';

-- ----------------------------------------------------------------------------
-- 3. ACCESSIBILITY ISOCHRONES
-- Stores multi-interval polygon service areas generated from network traversal
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS accessibility_isochrones (
    id SERIAL PRIMARY KEY,
    target_type VARCHAR(64) NOT NULL,       -- 'Hospital', 'Clinic', 'All_Healthcare'
    speed_scenario VARCHAR(64) NOT NULL,    -- 'normal_4.8kmh', 'slower_3.6kmh'
    speed_kmh DOUBLE PRECISION NOT NULL,
    cutoff_minutes INTEGER NOT NULL,        -- 5, 10, 15
    cutoff_distance_m DOUBLE PRECISION NOT NULL,
    facility_count INTEGER NOT NULL,
    area_sqkm DOUBLE PRECISION NOT NULL,
    coverage_pct_pmc DOUBLE PRECISION NOT NULL,
    municipality VARCHAR(10) NOT NULL DEFAULT 'PMC',
    geom GEOMETRY(MultiPolygon, 4326) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_isochrones_geom_valid CHECK (ST_IsValid(geom))
);

-- Spatial and attribute indexes on isochrones
CREATE INDEX IF NOT EXISTS idx_isochrones_geom 
    ON accessibility_isochrones USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_isochrones_filter 
    ON accessibility_isochrones (target_type, speed_scenario, cutoff_minutes);

COMMENT ON TABLE accessibility_isochrones IS 'Network-derived isochrone service area polygons';

-- ----------------------------------------------------------------------------
-- 4. H3 HEXAGONAL ACCESSIBILITY AGGREGATION
-- Stores discrete global grid cells (Res 8 / 9) with facility counts and reachability
-- ----------------------------------------------------------------------------
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
    area_sqkm DOUBLE PRECISION NOT NULL DEFAULT 0.737, -- ~0.737 km² for H3 res 8
    geom GEOMETRY(Polygon, 4326) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_h3_geom_valid CHECK (ST_IsValid(geom))
);

-- Spatial and attribute indexes on H3 cells
CREATE INDEX IF NOT EXISTS idx_h3_accessibility_geom 
    ON h3_accessibility USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_h3_resolution 
    ON h3_accessibility (resolution);
CREATE INDEX IF NOT EXISTS idx_h3_accessible_normal 
    ON h3_accessibility (is_accessible_15min_normal);
CREATE INDEX IF NOT EXISTS idx_h3_accessible_slower 
    ON h3_accessibility (is_accessible_15min_slower);

COMMENT ON TABLE h3_accessibility IS 'Uber H3 discrete global grid cells aggregated with healthcare access metrics';

-- ----------------------------------------------------------------------------
-- 5. POPULATION GRID
-- Stores demographic grid cells for population accessibility estimation
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS population_grid (
    id SERIAL PRIMARY KEY,
    grid_id VARCHAR(50),
    source VARCHAR(100) DEFAULT 'WorldPop / GHSL',
    year INTEGER DEFAULT 2020,
    municipality VARCHAR(10) NOT NULL DEFAULT 'PMC',
    population DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    area_sqkm DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    density_per_sqkm DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    is_accessible_15min BOOLEAN NOT NULL DEFAULT FALSE,
    geom GEOMETRY(Polygon, 4326) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_population_geom_valid CHECK (ST_IsValid(geom))
);

-- Spatial index on population grid
CREATE INDEX IF NOT EXISTS idx_population_grid_geom 
    ON population_grid USING GIST (geom);

COMMENT ON TABLE population_grid IS 'Demographic spatial grid for population accessibility quantification';

-- ----------------------------------------------------------------------------
-- 6. ACCESSIBILITY SUMMARY
-- Analytical comparison metrics across walking scenarios and facility types
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS accessibility_summary (
    id SERIAL PRIMARY KEY,
    scenario_id VARCHAR(100) NOT NULL UNIQUE,
    facility_type VARCHAR(64) NOT NULL,
    walking_speed_kmh DOUBLE PRECISION NOT NULL,
    cutoff_minutes INTEGER NOT NULL,
    cutoff_distance_m DOUBLE PRECISION NOT NULL,
    facilities_evaluated INTEGER NOT NULL,
    accessible_area_sqkm DOUBLE PRECISION NOT NULL,
    pct_pmc_area_accessible DOUBLE PRECISION NOT NULL,
    accessible_h3_cells_res8 INTEGER NOT NULL DEFAULT 0,
    total_h3_cells_res8 INTEGER NOT NULL DEFAULT 0,
    pct_h3_cells_accessible DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    estimated_accessible_population DOUBLE PRECISION,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_access_summary_facility 
    ON accessibility_summary (facility_type);
CREATE INDEX IF NOT EXISTS idx_access_summary_speed 
    ON accessibility_summary (walking_speed_kmh);

COMMENT ON TABLE accessibility_summary IS 'Benchmarked comparative statistics for all accessibility scenarios';
