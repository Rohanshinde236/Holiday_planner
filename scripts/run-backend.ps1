# Start the FastAPI backend (engine) on http://localhost:5050
# Usage:  ./scripts/run-backend.ps1
Set-Location "$PSScriptRoot/../backend"
python -m uvicorn api.main:app --reload --port 5050 --host 127.0.0.1
