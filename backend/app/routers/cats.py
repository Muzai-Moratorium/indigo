from fastapi import APIRouter, WebSocket
import onnxruntime as ort
import numpy as np
import cv2
import time
import os
from datetime import datetime
import mysql.connector

router = APIRouter()

# ============================================
# 스냅샷 저장 설정
# ============================================
CAPTURE_DIR = "captures"
os.makedirs(CAPTURE_DIR, exist_ok=True)
last_capture_time = 0
CAPTURE_COOLDOWN = 10

# ============================================
# YOLOv8 모델 로드 (CPU 최적화)
# ============================================
sess_options = ort.SessionOptions()
sess_options.intra_op_num_threads = 4  # CPU 스레드 수 조정
sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

# GPU 사용 시도 (없으면 CPU 자동 사용)
providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']

# Calculate the absolute path to the model file
# backend/app/routers/cats.py -> .../backend/
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MODEL_PATH = os.path.join(BASE_DIR, "artifacts", "yolov8n.onnx")

if not os.path.exists(MODEL_PATH):
    print(f"Warning: Model file not found at {MODEL_PATH}")

session = ort.InferenceSession(MODEL_PATH, sess_options, providers=providers)

print(f"Using providers: {session.get_providers()}")

# ============================================
# COCO 클래스
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

def save_to_database(image_path, score):
    try:
        connection = mysql.connector.connect(
            host="localhost",
            port=3306,
            user="root",
            password="1234",
            database="cat_db"
        )

        if connection.is_connected():
            cursor = connection.cursor()
            sql_query = """
            INSERT INTO cat_captures (image_path, score, created_at) 
            VALUES (%s, %s, %s)
            """
            current_time = datetime.now()
            cursor.execute(sql_query, (image_path, float(score), current_time))
            connection.commit()
            print(f"[MySQL] DB 저장 완료: {image_path}, 신뢰도: {score:.2f}")

    except mysql.connector.Error as e:
        print(f"[MySQL Error] {e}")
    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()

def save_snapshot(frame, score, box=None):
    """감지된 영역만 크롭하여 저장"""
    global last_capture_time
    current_time = time.time()

    if current_time - last_capture_time < CAPTURE_COOLDOWN:
        return

    now = datetime.now()
    timestamp_file = now.strftime("%Y년%m월%d일_%H시%M분%S초")
    timestamp_display = now.strftime("%Y년 %m월 %d일 %H시 %M분 %S초")
    filename = f"person_{timestamp_file}.jpg"
    filepath = os.path.join(CAPTURE_DIR, filename)

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
            cv2.imwrite(filepath, cropped)
        else:
            cv2.imwrite(filepath, frame)
    else:
        cv2.imwrite(filepath, frame)
    
    print(f"📸 [캡처] 사람 감지! 이미지 저장: {filename} | 신뢰도: {score:.2f} | 시간: {timestamp_display}")
    save_to_database(filepath, score)
    last_capture_time = current_time

# ============================================
# 전처리 (최적화)
# ============================================
def preprocess(frame):
    # 리사이즈를 먼저 수행 (더 효율적)
    img = cv2.resize(frame, (640, 640), interpolation=cv2.INTER_LINEAR)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    # float32로 한 번에 변환 및 정규화
    img = img.astype(np.float32) / 255.0
    img = np.transpose(img, (2, 0, 1))
    img = np.expand_dims(img, axis=0)
    return img

# ============================================
# 후처리 (신뢰도 임계값 상향)
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
            w = int(w)
            h = int(w)
            # wait, original code used w = int(w), h=int(h) which reassigns input w,h which were float.
            # let's stick to original logic carefully.
            # original: 
            # cx, cy, w, h = row[0], row[1], row[2], row[3]
            # x1 = int(cx - w / 2) ...
            # w = int(w)
            
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
    await ws.accept()
    print("WebSocket connected (Binary mode)")

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
                    print(f"FPS: {fps:.1f} | Inference: {inference_time:.1f}ms")

                # 스냅샷 저장 (신뢰도 0.5 이상, 감지 영역만 크롭)
                for pred in predictions:
                    if pred['label'] == 'person' and pred['score'] >= 0.5:
                        save_snapshot(frame, pred['score'], pred['box'])
                        break

                # 결과 전송
                await ws.send_json({"predictions": predictions})

            except Exception as e:
                print(f"Error during processing: {e}")
                continue

    except Exception as e:
        print(f"Connection closed: {e}")
