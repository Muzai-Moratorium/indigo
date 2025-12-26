from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, cats
from app.database import init_db

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

# Include Routers
app.include_router(cats.router)
app.include_router(auth.router)

@app.get("/")
def read_root():
    return {"status": "YOLOv8 Backend is running (Refactored)"}
