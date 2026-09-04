import os
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from app.models import BeamAnalysisRequest, BeamAnalysisResponse
from app.solver import solve_beam
from app.materials import MATERIALS, PRESETS, calculate_section_properties

app = FastAPI(
    title="Beam Deflection Visualizer API",
    description="Interactive structural beam calculation and visualization engine for shear force, bending moment, slope, and deflection.",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR / "frontend" if (BASE_DIR / "frontend").exists() else BASE_DIR / "Frontend"

# Mount static frontend assets
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "Beam Deflection Visualizer",
        "version": "1.0.0"
    }

@app.get("/api/presets")
def get_presets():
    return {"presets": PRESETS}

@app.get("/api/materials")
def get_materials():
    return {"materials": MATERIALS}

@app.post("/api/section-calculator")
def section_calculator(payload: dict):
    section_type = payload.get("section_type", "rectangle")
    params = payload.get("parameters", {})
    try:
        results = calculate_section_properties(section_type, params)
        return {"success": True, "properties": results}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/calculate", response_model=BeamAnalysisResponse)
def calculate_beam(req: BeamAnalysisRequest):
    try:
        return solve_beam(req)
    except ValueError as ve:
        raise HTTPException(status_code=422, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Solver execution error: {str(e)}")

@app.get("/")
def serve_index():
    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return JSONResponse({"message": "Beam Deflection Visualizer API is active. Open /docs for Swagger."})
