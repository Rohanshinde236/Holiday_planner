# WFM Holiday Planner (rebuild)

Local-only workforce-management holiday staffing tool. Modern stack, **same WFM formulas**
as the original (frozen and golden-tested). See `DESIGN.md` for the full spec.

```
backend/    Python · FastAPI · the pure formula engine + ILP optimiser (all the math)
frontend/   React · Vite · TypeScript (the 8 tabs + charts — presentation only)
plans/      saved plan files (JSON)
scripts/    run helpers
```

## Run it (two terminals)

**1. Backend** (http://localhost:5050, docs at `/docs`)
```powershell
cd backend
pip install -r requirements.txt      # first time
python -m uvicorn api.main:app --reload --port 5050
```

**2. Frontend** (http://localhost:5173)
```powershell
cd frontend
npm install                          # first time
npm run dev
```

Open **http://localhost:5173**, click **Compute plan**, and work through the 8 tabs.
(Or use the helpers: `scripts/run-backend.ps1` and `scripts/run-frontend.ps1`.)

## Verify the formulas are unchanged
```powershell
cd backend
python -m pytest -v        # 33 tests incl. golden numbers (Christmas 57, Diwali 81/18/16)
```

## Status
- Phase 1 — formula engine + golden tests ✅
- Phase 2 — FastAPI API + Pydantic validation + ILP optimal shifts ✅
- Phase 3 — React frontend (8 tabs, charts) ✅
- Phase 4 — LLM explain/review (Grok/Gemini/NVIDIA) — pending
- Phase 5 — exports (PDF/Excel), holiday calendar, multi-day — pending

No git, no database, no cloud — runs entirely on your machine.
