# Start the React (Vite) frontend on http://localhost:5173
# Usage:  ./scripts/run-frontend.ps1
Set-Location "$PSScriptRoot/../frontend"
if (-not (Test-Path "node_modules")) { npm install }
npm run dev
