/**
 * SmartServe GIS - API Service Module
 * Handles all REST communication with the FastAPI Spatial Backend.
 */

const API = {
    _cachedServices: null,

    /**
     * Generic fetch wrapper with error handling, JSON parsing, and static offline fallback.
     */
    async _fetch(endpoint, params = {}) {
        try {
            const url = new URL(`${CONFIG.API_BASE_URL}${endpoint}`);
            Object.entries(params).forEach(([key, val]) => {
                if (val !== undefined && val !== null && val !== '') {
                    url.searchParams.append(key, val);
                }
            });

            const response = await fetch(url.toString(), {
                method: 'GET',
                headers: {
                    'Accept': 'application/json',
                }
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || `HTTP Error ${response.status}: ${response.statusText}`);
            }

            return await response.json();
        } catch (error) {
            console.warn(`[API Fallback] Backend unreachable (${endpoint}). Using client-side static dataset.`);
            return await this._staticFallback(endpoint, params);
        }
    },

    /**
     * Offline/GitHub Pages static dataset fallback using local GeoJSON.
     */
    async _staticFallback(endpoint, params = {}) {
        if (!this._cachedServices) {
            try {
                // Try full 4,747 dataset first, then fall back to PMC dataset
                let r = await fetch('data/analysis/all_services.geojson');
                if (!r.ok) r = await fetch('data/analysis/pmc_all_services.geojson');
                this._cachedServices = await r.json();
            } catch (e) {
                console.warn("[API Fallback] Trying secondary services file:", e);
                try {
                    const r2 = await fetch('data/analysis/pmc_all_services.geojson');
                    this._cachedServices = await r2.json();
                } catch (err) {
                    console.error("Failed to load static services GeoJSON:", err);
                    this._cachedServices = { type: "FeatureCollection", features: [] };
                }
            }
        }

        // Helper: Great Circle / Haversine distance in meters
        const haversineMeters = (lat1, lon1, lat2, lon2) => {
            const R = 6371000;
            const toRad = deg => deg * Math.PI / 180;
            const dLat = toRad(lat2 - lat1);
            const dLon = toRad(lon2 - lon1);
            const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
                      Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) *
                      Math.sin(dLon / 2) * Math.sin(dLon / 2);
            return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
        };

        if (endpoint.startsWith('/boundaries')) {
            try {
                const r = await fetch('data/boundary/pmc.geojson');
                return await r.json();
            } catch (e) {
                return { type: "FeatureCollection", features: [] };
            }
        }

        if (endpoint.startsWith('/categories/tree')) {
            // Compute per-category and per-subcategory counts from cached services
            const catCounts = {};
            (this._cachedServices?.features || []).forEach(f => {
                const cat = f.properties.category;
                const sub = f.properties.subcategory;
                if (!catCounts[cat]) catCounts[cat] = { total: 0, subs: {} };
                catCounts[cat].total++;
                catCounts[cat].subs[sub] = (catCounts[cat].subs[sub] || 0) + 1;
            });

            const tree = [];
            let catId = 1;
            for (const [catName, catMeta] of Object.entries(CONFIG.CATEGORIES)) {
                const subcats = [];
                for (const [subName, subMeta] of Object.entries(catMeta.subcategories || {})) {
                    subcats.push({
                        id: catId++,
                        category: catName,
                        subcategory: subName,
                        slug: subName.toLowerCase().replace(/[^a-z0-9]/g, '_'),
                        icon: subMeta.icon,
                        color: subMeta.color,
                        count: catCounts[catName]?.subs[subName] || 0
                    });
                }
                tree.push({
                    category: catName,
                    color: catMeta.color,
                    icon: catMeta.icon,
                    total_count: catCounts[catName]?.total || 0,
                    subcategories: subcats
                });
            }
            return tree;
        }

        if (endpoint.startsWith('/categories')) {
            const list = [];
            let catId = 1;
            for (const [catName, catMeta] of Object.entries(CONFIG.CATEGORIES)) {
                for (const [subName, subMeta] of Object.entries(catMeta.subcategories || {})) {
                    list.push({
                        id: catId++,
                        category: catName,
                        subcategory: subName,
                        slug: subName.toLowerCase().replace(/[^a-z0-9]/g, '_'),
                        icon: subMeta.icon,
                        color: subMeta.color
                    });
                }
            }
            return list;
        }

        if (endpoint.startsWith('/services/autocomplete')) {
            const q = (params.q || '').toLowerCase().trim();
            const limit = parseInt(params.limit || 8);
            if (!q) return [];

            const feats = this._cachedServices?.features || [];
            const results = [];
            for (const f of feats) {
                const name = f.properties.name || '';
                const sub = f.properties.subcategory || '';
                const cat = f.properties.category || '';
                if (name.toLowerCase().includes(q) || sub.toLowerCase().includes(q) || cat.toLowerCase().includes(q)) {
                    results.push({
                        ...f.properties,
                        id: f.properties.id,
                        name: f.properties.name,
                        category: f.properties.category,
                        subcategory: f.properties.subcategory,
                        municipality: f.properties.municipality,
                        address: f.properties.address,
                        latitude: f.geometry.coordinates[1],
                        longitude: f.geometry.coordinates[0]
                    });
                    if (results.length >= limit) break;
                }
            }
            return results;
        }

        if (endpoint.startsWith('/services')) {
            let features = [...(this._cachedServices.features || [])];

            if (params.category) {
                features = features.filter(f => f.properties.category === params.category);
            }
            if (params.subcategory) {
                features = features.filter(f => f.properties.subcategory === params.subcategory);
            }
            if (params.municipality) {
                features = features.filter(f => f.properties.municipality === params.municipality);
            }
            if (params.q) {
                const q = params.q.toLowerCase();
                features = features.filter(f => 
                    (f.properties.name || '').toLowerCase().includes(q) || 
                    (f.properties.subcategory || '').toLowerCase().includes(q) ||
                    (f.properties.category || '').toLowerCase().includes(q)
                );
            }

            // Client-side Geometric Distance Calculation (Proximity & KNN)
            if (params.lat !== undefined && params.lon !== undefined) {
                const targetLat = parseFloat(params.lat);
                const targetLon = parseFloat(params.lon);

                features = features.map(f => {
                    const coords = f.geometry.coordinates; // [lon, lat]
                    const dist = haversineMeters(targetLat, targetLon, coords[1], coords[0]);
                    return {
                        ...f,
                        properties: {
                            ...f.properties,
                            distance_meters: Math.round(dist)
                        }
                    };
                });

                // Proximity search: filter within radius
                if (endpoint.startsWith('/services/nearby') || params.radius_meters) {
                    const radius = parseFloat(params.radius_meters || 2000);
                    features = features.filter(f => f.properties.distance_meters <= radius);
                    features.sort((a, b) => a.properties.distance_meters - b.properties.distance_meters);
                }

                // KNN search: sort strictly by ascending distance
                if (endpoint.startsWith('/services/knn')) {
                    features.sort((a, b) => a.properties.distance_meters - b.properties.distance_meters);
                    const k = parseInt(params.k || 5);
                    features = features.slice(0, k);
                }
            }

            if (params.limit && !endpoint.startsWith('/services/knn')) {
                features = features.slice(0, parseInt(params.limit));
            }

            // Map GeoJSON features → flat POI objects that app.js / map.js expect
            // app.js reads: results.items (array), results.total (number)
            // map.js renderPOIs() reads: poi.latitude, poi.longitude, poi.subcategory, poi.name, poi.distance_meters
            const items = features.map(f => ({
                ...f.properties,
                latitude:  f.geometry.coordinates[1],
                longitude: f.geometry.coordinates[0],
                distance_meters: f.properties.distance_meters
            }));

            return {
                items: items,
                total: items.length,
                // keep GeoJSON alongside for any code that accesses .features directly
                type: "FeatureCollection",
                total_features: items.length,
                features: features
            };
        }

        if (endpoint.startsWith('/analytics/overview')) {
            const feats = this._cachedServices.features || [];
            const catCounts = {};
            feats.forEach(f => {
                const cat = f.properties.category || "Other";
                catCounts[cat] = (catCounts[cat] || 0) + 1;
            });

            return {
                total_services: feats.length || 4747,
                total_categories: Object.keys(catCounts).length || 9,
                total_subcategories: 20,
                municipalities: 2,
                services_by_category: catCounts
            };
        }

        return { type: "FeatureCollection", features: [] };
    },

    // ==========================================
    // 1. BOUNDARIES
    // ==========================================
    async getBoundaries() {
        return await this._fetch('/boundaries/');
    },

    // ==========================================
    // 2. CATEGORIES
    // ==========================================
    async getCategoryTree() {
        return await this._fetch('/categories/tree');
    },

    async getCategories() {
        return await this._fetch('/categories/');
    },

    // ==========================================
    // 3. SERVICES / SPATIAL QUERIES
    // ==========================================
    /**
     * Radius Proximity Search (ST_DWithin)
     */
    async getNearbyServices({ lat, lon, radius_meters = 2000, q = null, category = null, subcategory = null, municipality = null, limit = 200 }) {
        return await this._fetch('/services/nearby', {
            lat,
            lon,
            radius_meters,
            q,
            category,
            subcategory,
            municipality,
            limit
        });
    },

    /**
     * K-Nearest Neighbors (PostGIS <-> Operator)
     */
    async getKnnServices({ lat, lon, k = 5, q = null, category = null, subcategory = null, municipality = null }) {
        return await this._fetch('/services/knn', {
            lat,
            lon,
            k,
            q,
            category,
            subcategory,
            municipality
        });
    },

    /**
     * Multi-Criteria Keyword & Attribute Search
     */
    async searchServices({ q = '', category = null, subcategory = null, municipality = null, limit = 50, offset = 0 }) {
        return await this._fetch('/services/search', {
            q,
            category,
            subcategory,
            municipality,
            limit,
            offset
        });
    },

    /**
     * Real-time Autocomplete Suggestions
     */
    async getAutocomplete(q, limit = 8) {
        if (!q || !q.trim()) return [];
        return await this._fetch('/services/autocomplete', {
            q: q.trim(),
            limit
        });
    },

    /**
     * Native GeoJSON POI Stream
     */
    async getGeoJson({ category = null, subcategory = null, municipality = null, bbox = null, limit = 500 }) {
        const params = { category, subcategory, municipality, limit };
        if (bbox && bbox.length === 4) {
            params.min_lon = bbox[0];
            params.min_lat = bbox[1];
            params.max_lon = bbox[2];
            params.max_lat = bbox[3];
        }
        return await this._fetch('/services/geojson', params);
    },

    /**
     * Single POI Details
     */
    async getServiceById(id) {
        return await this._fetch(`/services/${id}`);
    },

    // ==========================================
    // 4. SPATIAL ANALYTICS
    // ==========================================
    async getAnalyticsOverview() {
        return await this._fetch('/analytics/overview');
    },

    async getDensityMetrics() {
        return await this._fetch('/analytics/density');
    },

    async getNearbySummary({ lat, lon, radius_meters = 2000 }) {
        return await this._fetch('/analytics/nearby-summary', {
            lat,
            lon,
            radius_meters
        });
    },

    // ==========================================
    // 5. SYSTEM HEALTH CHECK
    // ==========================================
    async checkHealth() {
        try {
            const res = await fetch('http://127.0.0.1:8000/health');
            return await res.json();
        } catch (e) {
            return { status: 'offline', error: e.message };
        }
    }
};
