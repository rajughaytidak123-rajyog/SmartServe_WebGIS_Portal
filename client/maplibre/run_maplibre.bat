@echo off
title SmartServe GIS - MapLibre GL JS Vector Client
color 0B

echo =======================================================================
echo   SMARTSERVE GIS - MAPLIBRE GL JS VECTOR CLIENT (PORT 5600)
echo   Pedestrian Accessibility & Vector Tiles Portal
echo =======================================================================
echo.

cd /d "%~dp0"

echo [INFO] Starting MapLibre vector client server on http://127.0.0.1:5600 ...
python serve.py

pause
