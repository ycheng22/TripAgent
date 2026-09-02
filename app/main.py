from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from app.settings import settings

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

@app.get("/healthz")
async def healthz():
    return {"status": "ok", "version": "0.1.0"}

@app.get("/runs/{run_id}/audit")
async def get_audit(run_id: str):
    audit_file = Path("audit_trails") / f"{run_id}.json"
    if not audit_file.exists():
        raise HTTPException(status_code=404, detail="Audit trail not found")
    
    import json
    data = json.loads(audit_file.read_text())
    return data
