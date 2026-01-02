"""
PyInstaller 빌드 스크립트 - FastAPI 백엔드를 .exe로 변환
사용법: python build_backend.py
"""

import subprocess
import sys
import os

def build():
    backend_dir = os.path.join(os.path.dirname(__file__), 'backend')
    main_script = os.path.join(backend_dir, 'main.py')
    
    # PyInstaller 명령어 구성
    cmd = [
        sys.executable,
        '-m', 'PyInstaller',
        '--onefile',           # 단일 exe 파일
        '--name', 'backend',   # 출력 파일명
        '--distpath', os.path.join(os.path.dirname(__file__), 'dist-backend'),
        '--workpath', os.path.join(os.path.dirname(__file__), 'build-backend'),
        '--specpath', os.path.join(os.path.dirname(__file__), 'build-backend'),
        
        # 데이터 파일 포함
        '--add-data', f'{os.path.join(backend_dir, "app")};app',
        '--add-data', f'{os.path.join(backend_dir, "models")};models',
        '--add-data', f'{os.path.join(backend_dir, "known_faces")};known_faces',
        
        # 숨겨진 imports
        '--hidden-import', 'uvicorn.logging',
        '--hidden-import', 'uvicorn.protocols.http',
        '--hidden-import', 'uvicorn.protocols.http.auto',
        '--hidden-import', 'uvicorn.protocols.websockets',
        '--hidden-import', 'uvicorn.protocols.websockets.auto',
        '--hidden-import', 'uvicorn.lifespan',
        '--hidden-import', 'uvicorn.lifespan.on',
        '--hidden-import', 'uvicorn.lifespan.off',
        
        # 메인 스크립트
        main_script,
    ]
    
    print("=" * 50)
    print("FastAPI 백엔드 빌드 시작")
    print("=" * 50)
    
    result = subprocess.run(cmd, cwd=backend_dir)
    
    if result.returncode == 0:
        print("\n" + "=" * 50)
        print("✅ 빌드 완료!")
        print(f"   출력 위치: dist-backend/backend.exe")
        print("=" * 50)
    else:
        print("\n❌ 빌드 실패!")
        sys.exit(1)

if __name__ == '__main__':
    build()
