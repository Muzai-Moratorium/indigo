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
            print(f"[MySQL] Saved to DB: {image_path}, Score: {score}")

    except mysql.connector.Error as e:
        print(f"[MySQL Error] {e}")
    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()

def save_snapshot(frame, score):
    global last_capture_time
    current_time = time.time()

    if current_time - last_capture_time < CAPTURE_COOLDOWN:
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"cat_{timestamp}.jpg"
    filepath = os.path.join(CAPTURE_DIR, filename)

    cv2.imwrite(filepath, frame)
    print(f"Snapshot saved: {filepath}")
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

            # 고양이만 필터링
            if CLASSES[class_id] != "cat":
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

                # 스냅샷 저장
                for pred in predictions:
                    if pred['label'] == 'cat' and pred['score'] >= 0.8:
                        save_snapshot(frame, pred['score'])
                        break

                # 결과 전송
                await ws.send_json({"predictions": predictions})

            except Exception as e:
                print(f"Error during processing: {e}")
                continue

    except Exception as e:
        print(f"Connection closed: {e}")
