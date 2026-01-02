"""
Security Router - 배회자 감지 및 추적 시스템
Guardian Home Protection System
"""
from fastapi import APIRouter, WebSocket
import onnxruntime as ort
import numpy as np
import cv2
import time
import os
from datetime import datetime
import mysql.connector
from app.utils.face_recognition_module import FaceRecognitionWhitelist

router = APIRouter(prefix="/security", tags=["security"])

# ============================================
# 스냅샷 저장 설정 (절대 경로 사용)
# ============================================
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CAPTURE_DIR = os.path.join(BACKEND_DIR, "captures")
os.makedirs(CAPTURE_DIR, exist_ok=True)
print(f"[Security] 캡처 저장 경로: {CAPTURE_DIR}")

# ============================================
# 얼굴 인식 화이트리스트 초기화
# ============================================
KNOWN_FACES_DIR = os.path.join(BACKEND_DIR, "known_faces")
os.makedirs(KNOWN_FACES_DIR, exist_ok=True)
face_whitelist = FaceRecognitionWhitelist(KNOWN_FACES_DIR)
print(f"[Security] 화이트리스트 폴더: {KNOWN_FACES_DIR}")

# ============================================
# 배회자 감지 설정
# ============================================
LOITERING_TIME = 7.0  # 배회 기준 시간 (초)
TRACKER_TIMEOUT = 5.0  # 트래커 만료 시간 (초)
FACE_CHECK_INTERVAL = 30  # 얼굴 재검사 프레임 간격
active_trackers = {}  # {track_id: {"start_time": float, "last_seen": float, "notified": bool, "box": list, "is_whitelisted": bool, "whitelist_name": str, "face_checked": bool}}
next_track_id = 0

def get_box_center(box):
    """박스 중심점 계산"""
    x1, y1, x2, y2 = box
    return ((x1 + x2) / 2, (y1 + y2) / 2)

def calculate_iou(box1, box2):
    """두 박스의 IoU 계산"""
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])
    
    intersection = max(0, x2 - x1) * max(0, y2 - y1)
    area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
    area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
    union = area1 + area2 - intersection
    
    return intersection / union if union > 0 else 0

def match_detection_to_tracker(box):
    """감지된 박스를 기존 트래커와 매칭"""
    global next_track_id
    
    best_match_id = None
    best_iou = 0.3  # 최소 IoU 임계값
    
    for track_id, tracker in active_trackers.items():
        iou = calculate_iou(box, tracker["box"])
        if iou > best_iou:
            best_iou = iou
            best_match_id = track_id
    
    if best_match_id is not None:
        return best_match_id
    else:
        # 새 트래커 생성
        new_id = next_track_id
        next_track_id += 1
        return new_id

def check_loitering(track_id, box, frame, score):
    """배회자 체크 및 알림 (화이트리스트 검사 포함)"""
    now = time.time()
    
    if track_id not in active_trackers:
        # 새로운 사람 감지 - 얼굴 인식 수행
        is_whitelisted, whitelist_name = face_whitelist.check_face_in_box(frame, box)
        
        active_trackers[track_id] = {
            "start_time": now,
            "last_seen": now,
            "notified": False,
            "box": box,
            "is_whitelisted": is_whitelisted,
            "whitelist_name": whitelist_name or "",
            "face_checked": True
        }
        
        if is_whitelisted:
            print(f"[Whitelist] 등록된 사용자 감지: {whitelist_name} (ID: {track_id})")
        else:
            print(f"[Track] 새로운 사람 감지 (ID: {track_id})")
    else:
        tracker = active_trackers[track_id]
        tracker["last_seen"] = now
        tracker["box"] = box
        
        # 화이트리스트 사용자는 배회자 판정 건너뛰기
        if tracker.get("is_whitelisted"):
            return
        
        # 배회 판정: 설정 시간 이상 머물렀고, 아직 알림 안 보냄
        elapsed = now - tracker["start_time"]
        if not tracker["notified"] and elapsed >= LOITERING_TIME:
            print(f"[ALERT] 배회자 감지 ID: {track_id} - {elapsed:.1f}초 체류!")
            save_snapshot(frame, score, box, track_id=track_id, stay_duration=elapsed, is_loitering=True)
            # TODO: send_kakao_message() 호출
            tracker["notified"] = True

def cleanup_old_trackers():
    """오래된 트래커 정리"""
    now = time.time()
    expired = [tid for tid, t in active_trackers.items() if now - t["last_seen"] > TRACKER_TIMEOUT]
    for tid in expired:
        elapsed = active_trackers[tid]["last_seen"] - active_trackers[tid]["start_time"]
        print(f"[Leave] ID: {tid} - 총 체류시간: {elapsed:.1f}초")
        del active_trackers[tid]

# ============================================
# YOLOv8 모델 로드 (CPU 최적화)
# ============================================
sess_options = ort.SessionOptions()
sess_options.intra_op_num_threads = 4
sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODEL_PATH = os.path.join(BASE_DIR, "artifacts", "yolov8n.onnx")

if not os.path.exists(MODEL_PATH):
    print(f"Warning: Model file not found at {MODEL_PATH}")

session = ort.InferenceSession(MODEL_PATH, sess_options, providers=providers)

print(f"[Security] YOLOv8 모델 로드 완료 - Providers: {session.get_providers()}")

# ============================================
# COCO 클래스 (사람 감지용)
# ============================================
CLASSES = [
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck", "boat", "traffic light",
    "fire hydrant", "stop sign", "parking meter", "bench", "bird", "cat", "dog", "horse", "sheep", "cow",
    "elephant", "bear", "zebra", "giraffe", "backpack", "umbrella", "handbag", "tie", "suitcase", "frisbee",
    "skis", "snowboard", "sports ball", "kite", "baseball bat", "baseball glove", "skateboard", "surfboard",
    "tennis racket", "bottle", "wine glass",
    "cup", "fork", "knife", "spoon", "bowl", "banana", "apple", "sandwich", "orange", "broccoli",
    "carrot", "hot dog", "pizza", "donut", "cake", "chair", "couch", "potted plant", "bed", "dining table",
    "toilet", "tv", "laptop", "mouse", "remote", "keyboard", "cell phone", "microwave", "oven", "toaster",
    "sink", "refrigerator", "book", "clock", "vase", "scissors", "teddy bear", "hair drier", "toothbrush"
]

def save_to_database(image_path, score, track_id=0, stay_duration=0, is_loitering=False):
    """Guardian DB에 감지 이력 저장"""
    detection_id = None
    try:
        connection = mysql.connector.connect(
            host="localhost",
            port=3306,
            user="root",
            password="1234",
            database="guardian"
        )

        if connection.is_connected():
            cursor = connection.cursor()
            detection_type = 'loitering' if is_loitering else 'simple_pass'
            sql_query = """
            INSERT INTO detection_logs 
            (track_id, image_path, detection_type, stay_duration, confidence_score, created_at) 
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            current_time = datetime.now()
            cursor.execute(sql_query, (
                track_id, 
                image_path, 
                detection_type, 
                float(stay_duration), 
                float(score), 
                current_time
            ))
            connection.commit()
            detection_id = cursor.lastrowid
            
            type_emoji = "[ALERT]" if is_loitering else "[INFO]"
            print(f"[Guardian] DB 저장 완료 ({type_emoji}): ID={detection_id}, 체류={stay_duration:.1f}초, 신뢰도={score:.2f}")

    except mysql.connector.Error as e:
        print(f"[Guardian Error] {e}")
    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()
    
    return detection_id

def save_snapshot(frame, score, box=None, track_id=0, stay_duration=0, is_loitering=False):
    """감지된 영역만 크롭하여 저장"""
    now = datetime.now()
    # 파일명은 영문으로 (한글 경로 문제 방지)
    timestamp_file = now.strftime("%Y%m%d_%H%M%S")
    timestamp_display = now.strftime("%Y년 %m월 %d일 %H시 %M분 %S초")
    
    prefix = "loitering" if is_loitering else "person"
    filename = f"{prefix}_{timestamp_file}.jpg"
    filepath = os.path.join(CAPTURE_DIR, filename)

    # 저장할 이미지 결정
    save_image = frame
    
    # 박스 정보가 있으면 해당 영역만 크롭
    if box is not None:
        x1, y1, x2, y2 = box
        h, w = frame.shape[:2]
        
        # 640x640 추론 좌표를 원본 프레임 좌표로 변환
        scale_x = w / 640
        scale_y = h / 640
        
        x1 = int(x1 * scale_x)
        y1 = int(y1 * scale_y)
        x2 = int(x2 * scale_x)
        y2 = int(y2 * scale_y)
        
        # 약간의 패딩 추가 (10%)
        pad_x = int((x2 - x1) * 0.1)
        pad_y = int((y2 - y1) * 0.1)
        
        x1 = max(0, x1 - pad_x)
        y1 = max(0, y1 - pad_y)
        x2 = min(w, x2 + pad_x)
        y2 = min(h, y2 + pad_y)
        
        cropped = frame[y1:y2, x1:x2]
        if cropped.size > 0:
            save_image = cropped
    
    # cv2.imencode를 사용하여 한글 경로에도 저장 가능
    try:
        success, encoded = cv2.imencode('.jpg', save_image)
        if success:
            with open(filepath, 'wb') as f:
                f.write(encoded.tobytes())
            event_type = "[ALERT] Loitering" if is_loitering else "[INFO] Person"
            print(f"{event_type} 캡처! 이미지 저장: {filename} | 체류: {stay_duration:.1f}초 | 시간: {timestamp_display}")
            save_to_database(filepath, score, track_id=track_id, stay_duration=stay_duration, is_loitering=is_loitering)
        else:
            print(f"[Security] [ERROR] 이미지 인코딩 실패: {filename}")
    except Exception as e:
        print(f"[Security] [ERROR] 이미지 저장 실패: {e}")


# ============================================
# 전처리 (최적화)
# ============================================
def preprocess(frame):
    img = cv2.resize(frame, (640, 640), interpolation=cv2.INTER_LINEAR)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img = img.astype(np.float32) / 255.0
    img = np.transpose(img, (2, 0, 1))
    img = np.expand_dims(img, axis=0)
    return img

# ============================================
# 후처리 (사람 감지 전용)
# ============================================
def postprocess(output, conf_threshold=0.25, iou_threshold=0.5):
    output = output[0].transpose()

    boxes = []
    scores = []
    class_ids = []

    for row in output:
        classes_scores = row[4:]
        max_score = np.max(classes_scores)

        if max_score > conf_threshold:
            class_id = np.argmax(classes_scores)

            # 사람만 필터링
            if CLASSES[class_id] != "person":
                continue

            cx, cy, w, h = row[0], row[1], row[2], row[3]
            x1 = int(cx - w / 2)
            y1 = int(cy - h / 2)
            w_int = int(w)
            h_int = int(h)
            
            boxes.append([x1, y1, w_int, h_int])
            scores.append(float(max_score))
            class_ids.append(class_id)

    indices = cv2.dnn.NMSBoxes(boxes, scores, conf_threshold, iou_threshold)

    results = []

    if isinstance(indices, tuple):
        indices = indices[0] if len(indices) > 0 else []

    if len(indices) > 0:
        if isinstance(indices, np.ndarray):
            indices = indices.flatten()

        for i in indices:
            box = boxes[i]
            x1, y1, w, h = box
            results.append({
                "box": [x1, y1, x1 + w, y1 + h],
                "label": CLASSES[class_ids[i]],
                "score": round(scores[i], 2)
            })

    return results

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
                input_data = preprocess(frame)

                # 추론
                outputs = session.run(None, {session.get_inputs()[0].name: input_data})

                # 후처리
                predictions = postprocess(outputs[0])

                inference_time = (time.time() - inference_start) * 1000

                # FPS 계산
                frame_count += 1
                if frame_count % 30 == 0:
                    elapsed = time.time() - start_time
                    fps = frame_count / elapsed
                    print(f"[Security] FPS: {fps:.1f} | Inference: {inference_time:.1f}ms")

                # 배회자 추적 (모든 감지된 사람에 대해)
                for pred in predictions:
                    if pred['label'] == 'person' and pred['score'] >= 0.5:
                        box = pred['box']
                        track_id = match_detection_to_tracker(box)
                        check_loitering(track_id, box, frame, pred['score'])
                
                # 오래된 트래커 정리
                cleanup_old_trackers()

                # 결과 전송 (트래커 수 포함)
                await ws.send_json({
                    "predictions": predictions,
                    "active_trackers": len(active_trackers)
                })

            except Exception as e:
                print(f"[Security] 처리 중 오류: {e}")
                continue

    except Exception as e:
        print(f"[Security] 클라이언트 연결 종료: {e}")
    finally:
        # 페이지를 나가면 이 섹션이 실행됨
        print("[Security] 연결 종료 - 자원 정리 시작")
        tracker_count = len(active_trackers)
        active_trackers.clear()
        print(f"[Security]   ✓ 활성 트래커 {tracker_count}개 정리 완료")
        print("[Security] 자원 정리 완료")


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


from fastapi import UploadFile, File, Form

@router.post("/whitelist/upload")
async def upload_face(file: UploadFile = File(...), name: str = Form(...)):
    """화이트리스트에 얼굴 이미지 업로드"""
    import shutil
    from pathlib import Path
    
    # 파일 확장자 확인
    allowed_extensions = {'.jpg', '.jpeg', '.png', '.bmp'}
    file_ext = Path(file.filename).suffix.lower()
    
    if file_ext not in allowed_extensions:
        from fastapi import HTTPException
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
        from fastapi import HTTPException
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
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"'{name}' 사용자를 찾을 수 없습니다.")
    
    # 화이트리스트 새로고침
    face_whitelist.reload_known_faces()
    
    return {
        "message": f"'{name}' 삭제 완료 ({deleted_count}개 이미지)",
        "count": face_whitelist.get_whitelist_count(),
        "names": face_whitelist.get_whitelist_names()
    }
