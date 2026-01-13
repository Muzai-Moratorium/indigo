"""
Guardian Home Protection API
=============================
AI 기반 배회자 감지 및 알림 시스템

주요 기능:
- 실시간 CCTV 영상 분석 (/security)
- 사용자 인증 (/auth)
- 카카오톡 알림 (/kakao)
- 캡처 이미지 관리 (/api/captures)
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from pathlib import Path

# .env 파일 로드 (반드시 다른 import 전에!)
load_dotenv()

from app.routers import auth, security, kakao
from app.database import init_db


# ============================================
# FastAPI 앱 초기화
# ============================================
app = FastAPI(
    title="Guardian Home Protection API",
    description="YOLO MUNG&NYANG",
    version="1.0.0"
)


# ============================================
# 데이터베이스 초기화
# ============================================
init_db()


# ============================================
# CORS 설정
# ============================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================
# 정적 파일 서빙 (캡처 이미지)
# ============================================
CAPTURES_DIR = Path(__file__).parent / "captures"
CAPTURES_DIR.mkdir(exist_ok=True)
app.mount("/captures", StaticFiles(directory=str(CAPTURES_DIR)), name="captures")


# ============================================
# 라우터 등록
# ============================================
app.include_router(security.router)
app.include_router(auth.router)
app.include_router(kakao.router)


# ============================================
# API 엔드포인트
# ============================================
@app.get("/")
def read_root():
    """API 상태 확인"""
    return {"status": "Guardian Home Protection API is running", "version": "1.0.0"}


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


# ============================================
# PyInstaller 빌드용 엔트리포인트
# ============================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)


