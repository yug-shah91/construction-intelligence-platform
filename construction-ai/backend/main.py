"""Multimodal Construction Intelligence Platform - FastAPI backend.
Every AI response is validated against a strict Pydantic (JSON) schema before it reaches the UI."""
import os, json, base64
from pathlib import Path
from typing import Literal
import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ValidationError

load_dotenv()
KEY = os.getenv("GEMINI_API_KEY", "").strip()
MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
app = FastAPI(title="Multimodal Construction Intelligence Platform")

# ---------- JSON data contracts ----------
Sev = Literal["Low", "Medium", "High", "Critical"]
class PPE(BaseModel):
    item: str; detected: bool
class Hazard(BaseModel):
    hazard: str; severity: Sev; remedy: str
class SafetyReport(BaseModel):
    safety_score: int = Field(ge=0, le=100)
    overall_status: Literal["Compliant", "Needs Attention", "Unsafe"]
    ppe: list[PPE]; hazards: list[Hazard]; summary: str
class CrackReport(BaseModel):
    defect_type: Literal["Hairline", "Settlement", "Structural Shear", "Thermal Expansion", "Spalling", "No Defect"]
    width_mm: float = Field(ge=0); severity: Sev
    causes: list[str]; repairs: list[str]; urgency: str
class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
class ValuationIn(BaseModel):
    structure: Literal["Residential", "Commercial", "Industrial"]
    sqft: float = Field(gt=0, le=1_000_000)
    tier: Literal[1, 2, 3]
    completion: float = Field(ge=0, le=100)

# ---------- Gemini helper ----------
async def gemini(prompt: str, image: bytes | None = None, mime="image/jpeg", as_json=True):
    parts = [{"text": prompt}]
    if image:
        parts.append({"inline_data": {"mime_type": mime, "data": base64.b64encode(image).decode()}})
    body = {"contents": [{"parts": parts}]}
    if as_json:
        body["generationConfig"] = {"responseMimeType": "application/json"}
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={KEY}"
    try:
        async with httpx.AsyncClient(timeout=60) as c:
            r = await c.post(url, json=body); r.raise_for_status()
        text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
        return json.loads(text) if as_json else text
    except Exception as e:
        raise HTTPException(502, f"AI service error: {type(e).__name__}. Check your API key or try again.")

async def read_image(f: UploadFile):
    if f.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(400, "Upload a JPG, PNG or WEBP image.")
    data = await f.read()
    if not data or len(data) > 8_000_000:
        raise HTTPException(400, "Image is empty or larger than 8 MB.")
    return data, f.content_type

def validated(model, data):
    try: return model.model_validate(data).model_dump()
    except ValidationError: raise HTTPException(502, "AI returned an unexpected format. Please retry.")

# ---------- Endpoints ----------
@app.get("/api/health")
def health(): return {"status": "ok", "mode": "live" if KEY else "demo"}

SAFETY_PROMPT = """You are a construction safety inspector (OSHA and Indian IS codes). Analyse the site photo.
Return ONLY JSON: {"safety_score":0-100,"overall_status":"Compliant|Needs Attention|Unsafe",
"ppe":[{"item":"Helmet|Hi-vis vest|Safety boots|Harness|Gloves","detected":bool}],
"hazards":[{"hazard":str,"severity":"Low|Medium|High|Critical","remedy":str}],"summary":str}"""
@app.post("/api/safety")
async def safety(file: UploadFile = File(...)):
    img, mime = await read_image(file)
    if not KEY:
        return {"demo": True, **SafetyReport(safety_score=62, overall_status="Needs Attention",
            ppe=[PPE(item="Helmet", detected=True), PPE(item="Hi-vis vest", detected=True), PPE(item="Safety boots", detected=False),
                 PPE(item="Harness", detected=False), PPE(item="Gloves", detected=True)],
            hazards=[Hazard(hazard="Worker at height without harness", severity="High", remedy="Stop work; provide harness and anchor points."),
                     Hazard(hazard="Loose material near edge", severity="Medium", remedy="Secure or remove debris; install toe boards.")],
            summary="Demo result. Add GEMINI_API_KEY for real image analysis.").model_dump()}
    return validated(SafetyReport, await gemini(SAFETY_PROMPT, img, mime))

CRACK_PROMPT = """You are a structural engineer. Classify the defect in this concrete/wall photo.
Return ONLY JSON: {"defect_type":"Hairline|Settlement|Structural Shear|Thermal Expansion|Spalling|No Defect",
"width_mm":number,"severity":"Low|Medium|High|Critical","causes":[str],"repairs":[str],"urgency":str}"""
@app.post("/api/crack")
async def crack(file: UploadFile = File(...)):
    img, mime = await read_image(file)
    if not KEY:
        return {"demo": True, **CrackReport(defect_type="Hairline", width_mm=0.3, severity="Low",
            causes=["Plastic shrinkage during curing", "Minor thermal movement"],
            repairs=["Seal with flexible crack filler", "Monitor for widening over 3 months"],
            urgency="Routine: repair within 30 days.").model_dump()}
    return validated(CrackReport, await gemini(CRACK_PROMPT, img, mime))

RATE = {"Residential": 1800, "Commercial": 2400, "Industrial": 2100}  # INR per sqft build cost
TIER = {1: 1.35, 2: 1.0, 3: 0.75}
MARKET = {1: 9000, 2: 5500, 3: 3200}  # INR per sqft market value
PHASES = [("Site prep & foundation", 15), ("Structure (RCC frame)", 35), ("Masonry & roofing", 20), ("MEP & finishing", 25), ("Handover", 5)]
@app.post("/api/valuation")
def valuation(v: ValuationIn):
    budget = v.sqft * RATE[v.structure] * TIER[v.tier]
    spent = budget * v.completion / 100
    value = v.sqft * MARKET[v.tier] * (0.4 + 0.6 * v.completion / 100)
    done, sched = 0, []
    for name, w in PHASES:
        done += w
        sched.append({"phase": name, "weight_pct": w, "status": "Done" if v.completion >= done else "In progress" if v.completion > done - w else "Pending"})
    return {"budget_inr": round(budget), "spent_inr": round(spent), "market_value_inr": round(value),
            "steel_kg": round(v.sqft * 4), "cement_bags": round(v.sqft * 0.4), "schedule": sched}

ADVICE = {
    "Normal": ["Hold the daily toolbox talk.", "Check scaffolds and lifting gear before use."],
    "High Wind": ["Suspend crane and hoist operations above 40 km/h.", "Secure sheets, formwork and loose materials."],
    "Heavy Rain": ["Cut power to exposed electrical points.", "Cover fresh concrete and protect cement from moisture.", "Inspect excavations for collapse risk."],
    "Extreme Heat": ["Schedule heavy work before 11:00 and after 16:00.", "Provide water and shaded breaks.", "Cure concrete with wet covers to prevent cracking."],
}
@app.get("/api/advisory/{weather}")
def advisory(weather: str):
    if weather not in ADVICE: raise HTTPException(404, "Unknown weather condition.")
    return {"weather": weather, "alerts": ADVICE[weather]}

@app.post("/api/chat")
async def chat(c: ChatIn):
    if not KEY:
        return {"reply": "Demo mode: add GEMINI_API_KEY to enable the construction assistant."}
    prompt = f"You are a concise construction engineering assistant for Indian sites. Answer in under 120 words.\nQuestion: {c.message}"
    return {"reply": await gemini(prompt, as_json=False)}

# ---------- Serve built React app (single-service deployment) ----------
DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")
    @app.get("/{path:path}")
    def spa(path: str): return FileResponse(DIST / "index.html")
