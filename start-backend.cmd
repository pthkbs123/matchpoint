@echo off
cd /d "%~dp0pc_setup\backend"
python -m uvicorn main:app --reload --port 8000
