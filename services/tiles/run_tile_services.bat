@echo off
title SmartServe GIS - Vector Tile & Feature Servers (pg_tileserv & pg_featureserv)
echo ======================================================================
echo   SMARTSERVE GIS - VECTOR TILE & OGC FEATURE SERVICES
echo ======================================================================

echo [1/2] Launching pg_tileserv (MVT Vector Tiles) on http://localhost:7800 ...
start "pg_tileserv (MVT Port 7800)" cmd /k "python services/tiles/pg_tileserv.py"

echo [2/2] Launching pg_featureserv (OGC API Features) on http://localhost:9000 ...
start "pg_featureserv (OGC Features Port 9000)" cmd /k "python services/tiles/pg_featureserv.py"

echo.
echo ======================================================================
echo Both tile services launched!
echo - pg_tileserv:     http://localhost:7800/index.json
echo - pg_featureserv:  http://localhost:9000/index.json
echo ======================================================================
pause
