/**
 * SmartServe GIS - MapLibre GL JS Client Application
 * Enterprise Vector WebGIS Engine for Pune Municipal Corporation (PMC)
 * Supporting Live PostGIS MVT, Serverless PMTiles v3, and Multi-Domain Analytics
 */

const CONFIG = {
  center: [73.8567, 18.5204],
  zoom: 12,
  pitch: 25,
  bearing: 0,
  tileservUrl: "http://localhost:7800",
  geoserverUrl: "http://localhost:8080/geoserver",
  backendUrl: "http://127.0.0.1:8000/api/v1",
  basemaps: {
    dark: "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
    positron: "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
    voyager: "https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json"
  },
  categoryColors: {
    "Healthcare": "#ef4444",
    "Food": "#f97316",
    "Transport": "#0ea5e9",
    "Finance": "#10b981",
    "Education": "#8b5cf6",
    "Emergency": "#dc2626",
    "Shopping": "#ec4899",
    "Accommodation": "#6366f1",
    "Recreation": "#22c55e"
  },
  // Phase 4 Empirical Accessibility Benchmarks for Real-Time HUD
  metrics: {
    "All_Healthcare_normal_4.8kmh": { coverage: "56.7%", area: "142.4 km²", pop: "3.71M (93.1%)", gaps: "42 H3 Deserts" },
    "All_Healthcare_slower_3.6kmh": { coverage: "49.6%", area: "124.5 km²", pop: "3.60M (90.3%)", gaps: "68 H3 Deserts" },
    "Hospital_normal_4.8kmh":       { coverage: "52.9%", area: "132.8 km²", pop: "3.58M (89.7%)", gaps: "58 H3 Deserts" },
    "Hospital_slower_3.6kmh":       { coverage: "43.9%", area: "110.2 km²", pop: "3.41M (85.5%)", gaps: "89 H3 Deserts" },
    "Clinic_normal_4.8kmh":         { coverage: "54.3%", area: "136.2 km²", pop: "3.62M (90.8%)", gaps: "51 H3 Deserts" },
    "Clinic_slower_3.6kmh":         { coverage: "46.6%", area: "116.9 km²", pop: "3.49M (87.5%)", gaps: "77 H3 Deserts" }
  }
};

let map;
let activeCategories = new Set(Object.keys(CONFIG.categoryColors));
let activeSpeed = "normal_4.8kmh";
let activeTarget = "All_Healthcare";
const isLocalhost = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1";
let currentTileEngine = isLocalhost ? "mvt" : "pmtiles";
let is3DPitch = true;
let isochroneBaseOpacity = 0.3;

function resolveDataPath(relPath) {
  if (window.location.pathname.includes("/client/maplibre")) {
    return "../../" + relPath;
  }
  return relPath;
}

// Register PMTiles v3 Protocol globally
if (typeof pmtiles !== "undefined") {
  try {
    const pmtilesProtocol = new pmtiles.Protocol();
    maplibregl.addProtocol("pmtiles", pmtilesProtocol.tile);
    console.log("[INFO] PMTiles protocol registered successfully.");
  } catch (err) {
    console.warn("[WARN] PMTiles protocol registration note:", err);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  initMap();
  setupUIHandlers();
  updateMetricsHUD();
});

function initMap() {
  map = new maplibregl.Map({
    container: "map",
    style: CONFIG.basemaps.dark,
    center: CONFIG.center,
    zoom: CONFIG.zoom,
    pitch: CONFIG.pitch,
    bearing: CONFIG.bearing,
    antialias: true
  });

  // Add Navigation, Fullscreen and Scale Controls
  map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), "top-right");
  map.addControl(new maplibregl.FullscreenControl(), "top-right");
  map.addControl(new maplibregl.ScaleControl({ unit: "metric" }), "bottom-right");

  map.on("load", () => {
    console.log("[INFO] MapLibre base map loaded. Registering vector sources...");
    addSourcesAndLayers();
    setupPopupInteractions();
    checkBackendHealth();
  });
}

function addSourcesAndLayers() {
  // Clean up any existing layers and sources if switching styles or engines
  const existingLayers = [
    "healthcare_highlight_layer", "services_layer", "walking_network_layer",
    "isochrones_layer", "h3_layer", "population_layer", "pmc_boundary_line", "pmc_boundary_fill"
  ];
  existingLayers.forEach(id => {
    if (map.getLayer(id)) map.removeLayer(id);
  });
  const existingSources = [
    "pmc_boundary_src", "isochrones_src", "h3_src", "walking_network_src", "population_src", "services_src"
  ];
  existingSources.forEach(id => {
    if (map.getSource(id)) map.removeSource(id);
  });

  // 1. PMC Municipal Boundary Source
  map.addSource("pmc_boundary_src", {
    type: "geojson",
    data: resolveDataPath("data/boundary/pmc.geojson")
  });

  // 2. Walking Isochrones Source (Optimized lightweight dataset for instant loading)
  map.addSource("isochrones_src", {
    type: "geojson",
    data: resolveDataPath("data/analysis/pmc_walking_isochrones_light.geojson")
  });

  // 3. H3 Hexagonal Grid Source
  map.addSource("h3_src", {
    type: "geojson",
    data: resolveDataPath("data/analysis/pmc_h3_accessibility_res8.geojson")
  });

  // 4. Walking Network Source (from pg_tileserv MVT vector tile if on localhost)
  if (isLocalhost) {
    map.addSource("walking_network_src", {
      type: "vector",
      tiles: [`${CONFIG.tileservUrl}/public.walking_network_edges/{z}/{x}/{y}.pbf`],
      minzoom: 12,
      maxzoom: 22
    });
  }

  // 5. Population Grid Source
  map.addSource("population_src", {
    type: "geojson",
    data: resolveDataPath("data/analysis/pmc_population_grid.geojson")
  });

  // 6. Master Services POI Source (MVT or Serverless PMTiles Archive)
  const pmtilesServicesUrl = new URL(resolveDataPath("data/pmtiles/pmc_services.pmtiles"), window.location.href).href;
  const servicesTiles = currentTileEngine === "pmtiles"
    ? [`pmtiles://${pmtilesServicesUrl}/{z}/{x}/{y}`]
    : [`${CONFIG.tileservUrl}/public.services/{z}/{x}/{y}.pbf`];

  map.addSource("services_src", {
    type: "vector",
    tiles: servicesTiles,
    minzoom: 10,
    maxzoom: 22
  });

  // -------------------------------------------------------------
  // ADD LAYERS IN VISUAL STACKING ORDER
  // -------------------------------------------------------------

  // A. PMC Boundary Fill & Outline
  map.addLayer({
    id: "pmc_boundary_fill",
    type: "fill",
    source: "pmc_boundary_src",
    paint: {
      "fill-color": "#3b82f6",
      "fill-opacity": 0.04
    }
  });

  map.addLayer({
    id: "pmc_boundary_line",
    type: "line",
    source: "pmc_boundary_src",
    paint: {
      "line-color": "#3b82f6",
      "line-width": 2,
      "line-dasharray": [4, 2]
    }
  });

  // B. Population Density Grid Layer
  map.addLayer({
    id: "population_layer",
    type: "fill",
    source: "population_src",
    layout: { visibility: "none" },
    paint: {
      "fill-color": [
        "interpolate", ["linear"], ["get", "density_per_sqkm"],
        5000, "#fed7aa",
        15000, "#ea580c",
        30000, "#7c2d12"
      ],
      "fill-opacity": 0.45,
      "fill-outline-color": "#431407"
    }
  });

  // C. H3 Hexagonal Grid Layer
  map.addLayer({
    id: "h3_layer",
    type: "fill",
    source: "h3_src",
    layout: { visibility: "none" },
    paint: {
      "fill-color": [
        "case",
        ["boolean", ["get", "is_accessible_15min_normal"], false],
        "#10b981", // Green for accessible
        "#ef4444"  // Red for gap
      ],
      "fill-opacity": 0.35,
      "fill-outline-color": "rgba(255, 255, 255, 0.4)"
    }
  });

  // D. Accessibility Walking Isochrones Layer (5, 10, 15 min)
  map.addLayer({
    id: "isochrones_layer",
    type: "fill",
    source: "isochrones_src",
    layout: { visibility: "visible" },
    filter: [
      "all",
      ["==", ["get", "speed_scenario"], activeSpeed],
      ["==", ["get", "target_type"], activeTarget]
    ],
    paint: {
      "fill-color": [
        "match", ["get", "cutoff_minutes"],
        5, "#1d4ed8",   // Deep blue
        10, "#3b82f6",  // Medium blue
        15, "#93c5fd",  // Light blue
        "#60a5fa"
      ],
      "fill-opacity": isochroneBaseOpacity,
      "fill-outline-color": "#2563eb"
    }
  });

  // E. Walkable Street Network (MVT Vector LineString)
  if (map.getSource("walking_network_src")) {
    map.addLayer({
      id: "walking_network_layer",
      type: "line",
      source: "walking_network_src",
      "source-layer": "walking_network_edges",
      layout: { visibility: "visible" },
      minzoom: 12,
      paint: {
        "line-color": "#64748b",
        "line-width": [
          "interpolate", ["linear"], ["zoom"],
          12, 0.6,
          15, 1.2,
          18, 2.5
        ],
        "line-opacity": 0.5
      }
    });
  }

  // F. Master Services POIs (MVT Vector Point Circle Markers)
  const categoryMatch = ["match", ["get", "category"]];
  for (const [cat, color] of Object.entries(CONFIG.categoryColors)) {
    categoryMatch.push(cat, color);
  }
  categoryMatch.push("#94a3b8"); // default

  map.addLayer({
    id: "services_layer",
    type: "circle",
    source: "services_src",
    "source-layer": "services",
    layout: { visibility: "visible" },
    paint: {
      "circle-color": categoryMatch,
      "circle-radius": [
        "interpolate", ["linear"], ["zoom"],
        11, 3,
        14, 5.5,
        17, 8
      ],
      "circle-stroke-width": 1.2,
      "circle-stroke-color": "#ffffff",
      "circle-opacity": 0.9
    }
  });

  // G. Healthcare Facilities Highlight Layer (Glow on Hospitals & Clinics)
  map.addLayer({
    id: "healthcare_highlight_layer",
    type: "circle",
    source: "services_src",
    "source-layer": "services",
    filter: ["in", ["get", "subcategory"], ["literal", ["Hospital", "Clinic"]]],
    layout: { visibility: "visible" },
    paint: {
      "circle-color": [
        "match", ["get", "subcategory"],
        "Hospital", "#dc2626",
        "Clinic", "#06b6d4",
        "#ef4444"
      ],
      "circle-radius": [
        "interpolate", ["linear"], ["zoom"],
        11, 4.5,
        14, 7.5,
        17, 11
      ],
      "circle-stroke-width": 2,
      "circle-stroke-color": "#ffffff"
    }
  });
}

// -------------------------------------------------------------
// INTERACTIVE POPUPS
// -------------------------------------------------------------
function setupPopupInteractions() {
  const popup = new maplibregl.Popup({
    closeButton: true,
    closeOnClick: true,
    maxWidth: "320px"
  });

  // Click on Services POIs
  map.on("click", "services_layer", (e) => {
    if (!e.features.length) return;
    const f = e.features[0];
    const p = f.properties;
    const catColor = CONFIG.categoryColors[p.category] || "#2563eb";

    const content = `
      <div class="popup-title">${p.name || "POI Feature"}</div>
      <span class="popup-category" style="background: ${catColor}20; color: ${catColor}; border: 1px solid ${catColor}40;">
        ${p.category} &bull; ${p.subcategory}
      </span>
      <div class="popup-detail"><strong>Municipality:</strong> ${p.municipality || "PMC"}</div>
      ${p.address ? `<div class="popup-detail"><strong>Address:</strong> ${p.address}</div>` : ""}
      ${p.phone ? `<div class="popup-detail"><strong>Phone:</strong> ${p.phone}</div>` : ""}
    `;

    popup.setLngLat(e.lngLat).setHTML(content).addTo(map);
  });

  // Click on Isochrones
  map.on("click", "isochrones_layer", (e) => {
    if (!e.features.length) return;
    const p = e.features[0].properties;

    const content = `
      <div class="popup-title">Walking Isochrone Catchment</div>
      <span class="popup-category" style="background: #2563eb20; color: #60a5fa; border: 1px solid #2563eb40;">
        ${p.cutoff_minutes} Minutes Walk
      </span>
      <div class="popup-detail"><strong>Target Facilities:</strong> ${p.target_type}</div>
      <div class="popup-detail"><strong>Walking Speed:</strong> ${p.speed_scenario} (${p.speed_kmh} km/h)</div>
      <div class="popup-detail"><strong>Accessible Area:</strong> ${p.area_sqkm} km² (${p.coverage_pct_pmc}% of PMC)</div>
    `;

    popup.setLngLat(e.lngLat).setHTML(content).addTo(map);
  });

  // Click on H3 Hexagons
  map.on("click", "h3_layer", (e) => {
    if (!e.features.length) return;
    const p = e.features[0].properties;
    const isAcc = p.is_accessible_15min_normal;

    const content = `
      <div class="popup-title">H3 Hexagon Cell (Res 8)</div>
      <span class="popup-category" style="background: ${isAcc ? '#10b98120' : '#ef444420'}; color: ${isAcc ? '#10b981' : '#ef4444'};">
        ${isAcc ? '15-Min Accessible' : 'Accessibility Gap (Desert)'}
      </span>
      <div class="popup-detail"><strong>H3 Index:</strong> <code>${p.h3_index}</code></div>
      <div class="popup-detail"><strong>Hospitals Inside:</strong> ${p.hospital_count}</div>
      <div class="popup-detail"><strong>Clinics Inside:</strong> ${p.clinic_count}</div>
      <div class="popup-detail"><strong>Dist to Nearest Hospital:</strong> ${p.min_dist_to_hospital_m ? Math.round(p.min_dist_to_hospital_m) + ' m' : 'N/A'}</div>
    `;

    popup.setLngLat(e.lngLat).setHTML(content).addTo(map);
  });

  // Cursor pointers
  ["services_layer", "isochrones_layer", "h3_layer"].forEach(layerId => {
    map.on("mouseenter", layerId, () => { map.getCanvas().style.cursor = "pointer"; });
    map.on("mouseleave", layerId, () => { map.getCanvas().style.cursor = ""; });
  });
}

// -------------------------------------------------------------
// UI CONTROLS & EVENT WIRING
// -------------------------------------------------------------
function setupUIHandlers() {
  // Sidebar Toggle
  const sidebar = document.getElementById("sidebar");
  const toggleBtn = document.getElementById("sidebar-toggle");
  if (toggleBtn && sidebar) {
    toggleBtn.addEventListener("click", () => {
      sidebar.classList.toggle("collapsed");
    });
  }

  // Quick Action: Reset View to PMC
  const resetBtn = document.getElementById("btn-reset-view");
  if (resetBtn) {
    resetBtn.addEventListener("click", () => {
      map.flyTo({
        center: CONFIG.center,
        zoom: CONFIG.zoom,
        pitch: 25,
        bearing: 0,
        essential: true
      });
    });
  }

  // Quick Action: Toggle 3D Pitch
  const pitchBtn = document.getElementById("btn-toggle-pitch");
  const pitchLabel = document.getElementById("pitch-label");
  if (pitchBtn) {
    pitchBtn.addEventListener("click", () => {
      is3DPitch = !is3DPitch;
      const targetPitch = is3DPitch ? 45 : 0;
      map.easeTo({ pitch: targetPitch, duration: 800 });
      if (pitchLabel) {
        pitchLabel.textContent = is3DPitch ? "3D View (45°)" : "2D Flat View";
      }
    });
  }

  // Tile Delivery Engine Selector (Live MVT vs Serverless PMTiles)
  const engineSelect = document.getElementById("select-tile-source");
  if (engineSelect) {
    engineSelect.value = currentTileEngine;
    engineSelect.addEventListener("change", (e) => {
      currentTileEngine = e.target.value;
      console.log(`[INFO] Vector tile delivery engine switched to: ${currentTileEngine}`);
      addSourcesAndLayers();
    });
  }

  // Basemap Selector
  const basemapSelect = document.getElementById("select-basemap");
  if (basemapSelect) {
    basemapSelect.addEventListener("change", (e) => {
      const styleUrl = CONFIG.basemaps[e.target.value] || CONFIG.basemaps.dark;
      map.setStyle(styleUrl);
      map.once("style.load", () => {
        addSourcesAndLayers();
      });
    });
  }

  // Speed Scenario Toggle
  const speedSelect = document.getElementById("select-speed");
  if (speedSelect) {
    speedSelect.addEventListener("change", (e) => {
      activeSpeed = e.target.value;
      updateIsochroneFilter();
      updateMetricsHUD();
    });
  }

  // Facility Target Filter
  const targetSelect = document.getElementById("select-target");
  if (targetSelect) {
    targetSelect.addEventListener("change", (e) => {
      activeTarget = e.target.value;
      updateIsochroneFilter();
      updateMetricsHUD();
    });
  }

  // Isochrone Opacity Slider
  const opacitySlider = document.getElementById("slider-opacity");
  const opacityVal = document.getElementById("opacity-val");
  if (opacitySlider) {
    opacitySlider.addEventListener("input", (e) => {
      isochroneBaseOpacity = parseFloat(e.target.value);
      if (opacityVal) {
        opacityVal.textContent = Math.round(isochroneBaseOpacity * 100) + "%";
      }
      if (map.getLayer("isochrones_layer")) {
        map.setPaintProperty("isochrones_layer", "fill-opacity", isochroneBaseOpacity);
      }
    });
  }

  // Layer Toggles
  const layerMap = {
    "toggle-boundary": ["pmc_boundary_fill", "pmc_boundary_line"],
    "toggle-network": ["walking_network_layer"],
    "toggle-isochrones": ["isochrones_layer"],
    "toggle-h3": ["h3_layer"],
    "toggle-population": ["population_layer"],
    "toggle-services": ["services_layer", "healthcare_highlight_layer"]
  };

  Object.entries(layerMap).forEach(([checkboxId, mapLayers]) => {
    const el = document.getElementById(checkboxId);
    if (el) {
      el.addEventListener("change", (e) => {
        const vis = e.target.checked ? "visible" : "none";
        mapLayers.forEach(l => {
          if (map.getLayer(l)) {
            map.setLayoutProperty(l, "visibility", vis);
          }
        });
      });
    }
  });

  // Category Filter Chips
  document.querySelectorAll(".chip[data-category]").forEach(chip => {
    chip.addEventListener("click", () => {
      const cat = chip.getAttribute("data-category");
      if (activeCategories.has(cat)) {
        activeCategories.delete(cat);
        chip.classList.remove("active");
      } else {
        activeCategories.add(cat);
        chip.classList.add("active");
      }
      updateCategoryFilter();
    });
  });
}

function updateIsochroneFilter() {
  if (map.getLayer("isochrones_layer")) {
    map.setFilter("isochrones_layer", [
      "all",
      ["==", ["get", "speed_scenario"], activeSpeed],
      ["==", ["get", "target_type"], activeTarget]
    ]);
  }
}

function updateCategoryFilter() {
  if (map.getLayer("services_layer")) {
    map.setFilter("services_layer", [
      "in",
      ["get", "category"],
      ["literal", Array.from(activeCategories)]
    ]);
  }
}

function updateMetricsHUD() {
  const key = `${activeTarget}_${activeSpeed}`;
  const data = CONFIG.metrics[key] || CONFIG.metrics["All_Healthcare_normal_4.8kmh"];

  const covEl = document.getElementById("hud-coverage");
  const areaEl = document.getElementById("hud-area");
  const popEl = document.getElementById("hud-population");
  const gapEl = document.getElementById("hud-gaps");

  if (covEl) covEl.textContent = data.coverage;
  if (areaEl) areaEl.textContent = data.area;
  if (popEl) popEl.textContent = data.pop;
  if (gapEl) gapEl.textContent = data.gaps;
}

function checkBackendHealth() {
  fetch(`${CONFIG.backendUrl}/health`)
    .then(r => r.json())
    .then(d => {
      const badge = document.getElementById("status-text");
      if (badge && d.status === "healthy") {
        badge.textContent = `PostGIS ${d.total_services_indexed} POIs Online`;
      }
    })
    .catch(() => {
      const badge = document.getElementById("status-text");
      if (badge) badge.textContent = "Offline Mode (Static Data)";
    });
}
