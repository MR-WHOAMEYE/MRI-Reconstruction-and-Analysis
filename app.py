from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from mri_pipeline import analyze_mri_slice, dataset_info


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_H5 = BASE_DIR / "2022061006_FLAIR01.h5"
OUTPUT_DIR = BASE_DIR / "outputs"
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title="MRI Reconstruction and Analysis API", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalysisRequest(BaseModel):
    file_path: str = Field(default=DEFAULT_H5.name)
    slice_id: int = Field(default=5, ge=0)
    acceleration: int = Field(default=1, ge=1, le=16)
    center_fraction: float = Field(default=0.08, ge=0.0, le=1.0)
    noise_removal: str = Field(default="gaussian")
    smoothing: str = Field(default="blur")
    contrast_enhancement: str = Field(default="clahe")


def _resolve_source(file_path: str) -> Path:
    candidate = Path(file_path)
    if not candidate.is_absolute():
        candidate = BASE_DIR / candidate
    if not candidate.exists():
        raise HTTPException(status_code=404, detail=f"Input file not found: {candidate}")
    return candidate


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def _relative_source_path(source: Path) -> str:
    try:
        return str(source.relative_to(BASE_DIR))
    except ValueError:
        return source.name


@app.get("/api/info")
def info(file_path: str = DEFAULT_H5.name) -> dict:
    source = _resolve_source(file_path)
    data = dataset_info(source)
    data["source_path"] = _relative_source_path(source)
    return data


@app.get("/api/h5-files")
def list_h5_files() -> dict[str, list[str] | str]:
    files = sorted(path.name for path in BASE_DIR.glob("*.h5"))
    default_name = DEFAULT_H5.name if DEFAULT_H5.exists() else (files[0] if files else "")
    return {"files": files, "default": default_name}


@app.post("/api/analyze")
def analyze(request: AnalysisRequest) -> dict:
    source = _resolve_source(request.file_path)
    try:
        data = analyze_mri_slice(
            file_path=source,
            output_dir=OUTPUT_DIR,
            slice_id=request.slice_id,
            acceleration=request.acceleration,
            center_fraction=request.center_fraction,
            noise_removal=request.noise_removal,
            smoothing=request.smoothing,
            contrast_enhancement=request.contrast_enhancement,
        )
        data["source_path"] = _relative_source_path(source)
        return data
    except IndexError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/files/{filename}")
def get_file(filename: str) -> FileResponse:
    file_path = OUTPUT_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Output file not found: {filename}")
    return FileResponse(path=file_path, filename=file_path.name)


app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
