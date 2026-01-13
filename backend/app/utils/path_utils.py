"""
Path Utilities - PyInstaller 호환 경로 관리
==========================================
"""
import os
import sys


def get_base_dir():
    """PyInstaller 빌드 또는 일반 실행 모두 지원하는 베이스 경로 반환"""
    if getattr(sys, 'frozen', False):
        # PyInstaller로 빌드된 경우 - exe 파일이 있는 디렉토리
        return os.path.dirname(sys.executable)
    else:
        # 일반 Python 실행 - backend 폴더
        return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# 베이스 디렉토리
BACKEND_DIR = get_base_dir()

# 캡처 이미지 저장 경로
CAPTURE_DIR = os.path.join(BACKEND_DIR, "captures")
os.makedirs(CAPTURE_DIR, exist_ok=True)

# 화이트리스트 얼굴 폴더
KNOWN_FACES_DIR = os.path.join(BACKEND_DIR, "known_faces")
os.makedirs(KNOWN_FACES_DIR, exist_ok=True)

# 모델 경로
ARTIFACTS_DIR = os.path.join(BACKEND_DIR, "artifacts")
MODELS_DIR = os.path.join(BACKEND_DIR, "models")

print(f"[PathUtils] 베이스 경로: {BACKEND_DIR}")
print(f"[PathUtils] 캡처 저장 경로: {CAPTURE_DIR}")
print(f"[PathUtils] 화이트리스트 폴더: {KNOWN_FACES_DIR}")
