# Multimodal Construction Intelligence Platform
Full-stack AI decision-support app: **React + Vite** frontend, **FastAPI** backend, multimodal LLM (Google Gemini).

## Features
- Site safety and PPE audit from photos (score, PPE checklist, hazards, remedies, JSON export)
- Crack detection: defect type, width, severity, causes, repairs
- Planning and valuation: budget, spend, market value (INR), steel/cement, phase schedule
- Weather-aware daily advisory and construction chatbot
- Strict JSON contracts (Pydantic) between AI, backend and UI; demo mode without API key

## Run locally
```bash
pip install -r requirements.txt
cp .env.example .env          # add GEMINI_API_KEY (optional)
cd frontend && npm install && npm run build && cd ..
uvicorn backend.main:app --reload     # open http://localhost:8000
```
Dev mode: run uvicorn on :8000 and `npm run dev` in `frontend/`.

## Deploy (Render, free)
New Web Service from this repo. Build: `pip install -r requirements.txt && cd frontend && npm install && npm run build`
Start: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`. Add env var `GEMINI_API_KEY`.

## Known limitations
Cost and valuation use fixed average rates, not live market data. AI findings are advisory and need review by a qualified engineer.
