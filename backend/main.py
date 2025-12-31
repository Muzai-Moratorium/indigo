from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.routers import auth, cats
from app.database import init_db
from pathlib import Path

app = FastAPI()

# Database Initialization
init_db()

# CORS Config
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files - captures 폴더 서빙
CAPTURES_DIR = Path(__file__).parent / "captures"
CAPTURES_DIR.mkdir(exist_ok=True)
app.mount("/captures", StaticFiles(directory=str(CAPTURES_DIR)), name="captures")

# Include Routers
app.include_router(cats.router)
app.include_router(auth.router)

@app.get("/")
def read_root():
    return {"status": "YOLOv8 Backend is running (Refactored)"}

@app.get("/api/captures")
def get_captures():
    """캡처된 이미지 목록 반환"""
    captures = []
    if CAPTURES_DIR.exists():
        for file in sorted(CAPTURES_DIR.glob("*.jpg"), reverse=True):
            captures.append({
                "src": f"http://localhost:8000/captures/{file.name}",
                "alt": file.stem,
                "filename": file.name
            })
    return {"captures": captures}
