"""
Security Router - Guardian Home Protection System
=================================================
YOLO11n(객체 감지) + MediaPipe Pose(관절 추출) 하이브리드 방식

주요 기능:
- 실시간 CCTV 영상 분석 (WebSocket)
- 사람/화재/연기 감지 (YOLO11n)
- 배회자 추적 및 알림
- 이상행동 감지 (MediaPipe Pose)
- 얼굴 인식 화이트리스트
- 동적 모델 변경 API
"""
from fastapi import APIRouter, WebSocket, Query, HTTPException, UploadFile, File, Form
import numpy as np
import cv2
import time

# 서비스 모듈 import
from app.utils.path_utils import KNOWN_FACES_DIR
from app.utils.face_recognition_module import FaceRecognitionWhitelist
from app.services import ai_model_service
from app.services import mediapipe_service
from app.services import tracker_service

router = APIRouter(prefix="/security", tags=["security"])

# ============================================
# 얼굴 인식 화이트리스트 초기화
# ============================================
face_whitelist = FaceRecognitionWhitelist(KNOWN_FACES_DIR)
print(f"[Security] 화이트리스트 폴더: {KNOWN_FACES_DIR}")


# ============================================
# WebSocket 엔드포인트 - 실시간 영상 분석
# ============================================
@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    """실시간 영상 분석 WebSocket 엔드포인트"""
    await ws.accept()
    print("[Security] WebSocket 연결됨 (Binary mode)")

    frame_count = 0
    start_time = time.time()

    try:
        while True:
            # Binary 데이터 수신
            data = await ws.receive_bytes()

            try:
                # Bytes -> numpy 배열 -> OpenCV 이미지
                nparr = np.frombuffer(data, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

                if frame is None:
                    print("Frame decode failed")
                    continue

                # 추론 시간 측정
                inference_start = time.time()

                # 전처리
                input_data = ai_model_service.preprocess(frame)

                # 추론
                outputs = ai_model_service.run_inference(input_data)

                # 후처리
                predictions = ai_model_service.postprocess(outputs)

                inference_time = (time.time() - inference_start) * 1000

                # FPS 계산
                frame_count += 1
                if frame_count % 30 == 0:
                    elapsed = time.time() - start_time
                    fps = frame_count / elapsed
                    print(f"[Security] FPS: {fps:.1f} | Inference: {inference_time:.1f}ms")

                # 클래스별 조건 분기 처리
                alerts = []
                for pred in predictions:
                    label = pred['label']
                    score = pred['score']
                    box = pred['box']
                    
                    if label == 'person' and score >= 0.5:
                        # 사람만 얼굴 인식 + 배회자 추적 + 이상행동 감지
                        track_id = tracker_service.match_detection_to_tracker(box)
                        loiter_result = tracker_service.check_loitering(
                            track_id, box, frame, score, face_whitelist
                        )
                        
                        # 배회자이면 관절 정보 추가
                        if loiter_result:
                            if loiter_result.get("keypoints"):
                                pred["keypoints"] = loiter_result["keypoints"]
                            
                            if loiter_result["type"] == "abnormal":
                                alert = {
                                    "type": "abnormal",
                                    "track_id": track_id,
                                    "behaviors": loiter_result["behaviors"],
                                    "box": box
                                }
                                alerts.append(alert)
                            elif loiter_result["type"] == "loitering":
                                alert = {
                                    "type": "loitering",
                                    "track_id": track_id,
                                    "box": box
                                }
                                alerts.append(alert)
                    elif label in ['fire', 'smoke']:
                        # 화재/연기는 즉시 경보
                        print(f"[DANGER] 위험 감지: {label} (Score: {score:.2f})")
                        alerts.append({
                            "type": label,
                            "box": box,
                            "score": score
                        })
                
                # 오래된 트래커 정리
                tracker_service.cleanup_old_trackers()

                # 결과 전송
                await ws.send_json({
                    "predictions": predictions,
                    "active_trackers": tracker_service.get_active_tracker_count(),
                    "alerts": alerts
                })

            except Exception as e:
                print(f"[Security] 처리 중 오류: {e}")
                continue

    except Exception as e:
        print(f"[Security] 클라이언트 연결 종료: {e}")
    finally:
        print("[Security] 연결 종료 - 자원 정리 시작")
        cleared = tracker_service.clear_trackers()
        print(f"[Security]   ✓ 활성 트래커 {cleared}개 정리 완료")
        print("[Security] 자원 정리 완료")


# ============================================
# MediaPipe 설정 API
# ============================================
@router.get("/mediapipe/settings")
def get_mediapipe_settings():
    """MediaPipe 설정 조회"""
    return {
        "enabled": mediapipe_service.is_enabled(),
        "frameInterval": mediapipe_service.get_frame_interval(),
        "available": mediapipe_service.is_available()
    }


@router.post("/mediapipe/toggle")
def toggle_mediapipe(enabled: bool = Query(..., description="MediaPipe 활성화 여부")):
    """MediaPipe 켜기/끄기"""
    return mediapipe_service.toggle(enabled)


@router.post("/mediapipe/interval")
def set_mediapipe_interval(interval: int = Query(..., description="호출 주기 (1~30)")):
    """MediaPipe 호출 주기 설정 (N 프레임마다 1번)"""
    return mediapipe_service.set_interval(interval)


# ============================================
# 화이트리스트 관리 API
# ============================================
@router.get("/whitelist")
def get_whitelist():
    """화이트리스트 사용자 목록 조회"""
    return {
        "count": face_whitelist.get_whitelist_count(),
        "names": face_whitelist.get_whitelist_names(),
        "folder": KNOWN_FACES_DIR
    }


@router.post("/whitelist/reload")
def reload_whitelist():
    """화이트리스트 새로고침 (새 사용자 추가 후 호출)"""
    face_whitelist.reload_known_faces()
    return {
        "message": "화이트리스트 새로고침 완료",
        "count": face_whitelist.get_whitelist_count(),
        "names": face_whitelist.get_whitelist_names()
    }


@router.post("/whitelist/upload")
async def upload_face(file: UploadFile = File(...), name: str = Form(...)):
    """화이트리스트에 얼굴 이미지 업로드"""
    import shutil
    from pathlib import Path
    
    # 파일 확장자 확인
    allowed_extensions = {'.jpg', '.jpeg', '.png', '.bmp'}
    file_ext = Path(file.filename).suffix.lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail="지원하지 않는 파일 형식입니다. (jpg, png, bmp만 가능)")
    
    # 파일명 생성 (이름 + 확장자)
    safe_name = name.replace(" ", "_").replace("/", "_")
    
    # 동일 이름 파일이 있으면 번호 추가
    base_path = Path(KNOWN_FACES_DIR) / f"{safe_name}{file_ext}"
    counter = 1
    while base_path.exists():
        base_path = Path(KNOWN_FACES_DIR) / f"{safe_name}_{counter}{file_ext}"
        counter += 1
    
    # 파일 저장
    try:
        with open(base_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # 화이트리스트 새로고침
        face_whitelist.reload_known_faces()
        
        return {
            "message": f"'{name}' 등록 완료",
            "filename": base_path.name,
            "count": face_whitelist.get_whitelist_count(),
            "names": face_whitelist.get_whitelist_names()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"파일 저장 실패: {str(e)}")


@router.delete("/whitelist/{name}")
def delete_whitelist_user(name: str):
    """화이트리스트에서 사용자 삭제 (해당 이름의 모든 이미지 삭제)"""
    from pathlib import Path
    
    deleted_count = 0
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp'}
    
    for img_path in Path(KNOWN_FACES_DIR).iterdir():
        if img_path.suffix.lower() not in image_extensions:
            continue
        
        # 파일명에서 이름 추출
        file_name = img_path.stem
        if '_' in file_name and file_name.rsplit('_', 1)[-1].isdigit():
            file_name = file_name.rsplit('_', 1)[0]
        
        # 이름이 일치하면 삭제
        if file_name == name:
            try:
                img_path.unlink()
                deleted_count += 1
                print(f"[FaceRecognition] 삭제: {img_path.name}")
            except Exception as e:
                print(f"[FaceRecognition] [ERROR] 삭제 실패: {img_path.name} - {e}")
    
    if deleted_count == 0:
        raise HTTPException(status_code=404, detail=f"'{name}' 사용자를 찾을 수 없습니다.")
    
    # 화이트리스트 새로고침
    face_whitelist.reload_known_faces()
    
    return {
        "message": f"'{name}' 삭제 완료 ({deleted_count}개 이미지)",
        "count": face_whitelist.get_whitelist_count(),
        "names": face_whitelist.get_whitelist_names()
    }
