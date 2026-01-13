"""
AI Model Service - OpenVINO 객체 감지 모델
==========================================
OpenVINO를 사용한 YOLO 기반 객체 감지 서비스

[아키텍처]
- OpenVINO: 인텔 하드웨어(CPU/GPU)에 최적화된 추론 엔진
- YOLO: You Only Look Once, 실시간 객체 감지 알고리즘
- 입력: 320x320 RGB 이미지
- 출력: 바운딩 박스 + 클래스 라벨 + 신뢰도

[감지 클래스]
- 0: fire (화재)
- 1: person (사람)
- 2: smoke (연기)

[처리 파이프라인]
1. preprocess(): 이미지 리사이즈 → RGB 변환 → 정규화
2. run_inference(): OpenVINO로 추론 실행
3. postprocess(): NMS로 중복 제거 → 결과 포맷팅
"""
import os
import numpy as np
import cv2
from openvino import Core

from app.utils.path_utils import ARTIFACTS_DIR


# ==================================================
# OpenVINO 런타임 초기화
# ==================================================
# Core: OpenVINO의 메인 클래스, 모델 로딩 및 디바이스 관리
core = Core()

# 사용 가능한 디바이스 확인 (CPU, GPU, NPU 등)
available_devices = core.available_devices
print(f"[AIModel] 사용 가능한 디바이스: {available_devices}")


# ==================================================
# 모델 상태 변수 (모듈 레벨 싱글톤)
# ==================================================
_compiled_model = None   # 컴파일된 OpenVINO 모델
_infer_request = None    # 추론 요청 객체 (재사용으로 성능 향상)
_input_layer = None      # 입력 레이어 정보
_output_layer = None     # 출력 레이어 정보
_classes = ["fire", "person", "smoke"]  # 클래스 이름 매핑


def _init_model():
    """
    OpenVINO 모델 초기화
    
    [동작 과정]
    1. XML(구조) + BIN(가중치) 파일로 모델 로드
    2. GPU 우선, 없으면 CPU로 폴백
    3. 캐시 설정으로 재시작 시 로딩 속도 향상
    4. LATENCY 힌트로 실시간 추론 최적화
    """
    global _compiled_model, _infer_request, _input_layer, _output_layer
    
    # 모델 파일 경로 (OpenVINO IR 포맷)
    model_xml = os.path.join(ARTIFACTS_DIR, "best.xml")  # 모델 구조
    model_bin = os.path.join(ARTIFACTS_DIR, "best.bin")  # 모델 가중치
    
    if not os.path.exists(model_xml) or not os.path.exists(model_bin):
        print(f"[AIModel] Warning: 모델 파일 없음")
        return
    
    try:
        # 1. 모델 읽기 (아직 디바이스에 로드되지 않음)
        model = core.read_model(model=model_xml, weights=model_bin)
        
        # 2. 디바이스 선택 (인텔 GPU > CPU)
        device = "GPU" if "GPU" in available_devices else "CPU"
        
        # 3. 캐시 디렉토리 설정 (컴파일된 모델 저장 → 재시작 시 빠른 로딩)
        cache_dir = os.path.join(ARTIFACTS_DIR, "model_cache")
        os.makedirs(cache_dir, exist_ok=True)
        
        # 4. 성능 최적화 설정
        config = {
            "CACHE_DIR": cache_dir,           # 모델 캐싱 (5~10배 빠른 재로딩)
            "PERFORMANCE_HINT": "LATENCY"     # 지연 시간 최소화 (실시간 추론)
        }
        
        # 5. 모델 컴파일 (디바이스에 최적화된 형태로 변환)
        _compiled_model = core.compile_model(model=model, device_name=device, config=config)
        
        # 6. 추론 요청 객체 생성 (재사용으로 메모리 할당 오버헤드 제거)
        _infer_request = _compiled_model.create_infer_request()
        
        # 7. 입출력 레이어 정보 저장
        _input_layer = _compiled_model.input(0)
        _output_layer = _compiled_model.output(0)
        
        print(f"[AIModel] OpenVINO 로드 완료 - 디바이스: {device}")
        print(f"[AIModel] 캐시: {cache_dir}, 성능 힌트: LATENCY")
        print(f"[AIModel] 입력 shape: {_input_layer.shape}, 클래스: {_classes}")
        
    except Exception as e:
        print(f"[AIModel] 로드 실패: {e}")


# 모듈 import 시 자동 초기화
_init_model()


def get_session():
    """컴파일된 모델 반환 (외부에서 모델 상태 확인용)"""
    return _compiled_model


def get_classes():
    """클래스 이름 목록 반환"""
    return _classes


# ==================================================
# 전처리 (Preprocessing)
# ==================================================
INPUT_SIZE = 320  # 모델 입력 크기 (320x320)

# 전처리 버퍼 (메모리 재할당 방지로 성능 향상)
_preprocess_buffer = np.zeros((1, 3, INPUT_SIZE, INPUT_SIZE), dtype=np.float32)


def preprocess(frame):
    """
    이미지 전처리: OpenCV BGR → YOLO 입력 포맷
    
    [변환 과정]
    1. 리사이즈: 원본 → 320x320
    2. 색공간: BGR → RGB
    3. 차원 변환: HWC → CHW (채널 우선)
    4. 정규화: 0~255 → 0.0~1.0
    
    Args:
        frame: OpenCV BGR 이미지 (numpy array)
    
    Returns:
        (1, 3, 320, 320) 형태의 정규화된 텐서
    """
    global _preprocess_buffer
    
    # 리사이즈 (INTER_LINEAR: 속도와 품질의 균형)
    img = cv2.resize(frame, (INPUT_SIZE, INPUT_SIZE), interpolation=cv2.INTER_LINEAR)
    
    # BGR → RGB (OpenCV는 BGR, YOLO는 RGB 사용)
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    # HWC → CHW 변환 후 정규화 (0~1)
    # transpose: (H, W, C) → (C, H, W)
    # /255.0: 픽셀값 정규화
    np.copyto(_preprocess_buffer[0], np.transpose(img, (2, 0, 1)).astype(np.float32) / 255.0)
    
    return _preprocess_buffer


def get_input_size():
    """모델 입력 크기 반환 (좌표 변환 시 사용)"""
    return INPUT_SIZE


def run_inference(input_data):
    """
    OpenVINO 추론 실행
    
    Args:
        input_data: 전처리된 이미지 텐서 (1, 3, 320, 320)
    
    Returns:
        모델 출력 텐서 (바운딩 박스 + 클래스 확률)
    """
    if _infer_request is None:
        return None
    
    # 동기 추론 실행 (입력 인덱스 0에 데이터 전달)
    _infer_request.infer({0: input_data})
    
    # 출력 텐서 반환 (인덱스 0)
    return [_infer_request.get_output_tensor(0).data]


# ==================================================
# 후처리 (Postprocessing)
# ==================================================
def postprocess(output, conf_threshold=0.4, iou_threshold=0.45):
    """
    YOLO 출력 후처리: 원시 출력 → 사용 가능한 감지 결과
    
    [처리 과정]
    1. 신뢰도 필터링: conf_threshold 이하 제거
    2. 좌표 변환: 중심점(cx,cy,w,h) → 코너점(x1,y1,x2,y2)
    3. NMS: 겹치는 박스 중 최고 신뢰도만 유지
    
    Args:
        output: 모델 출력 텐서
        conf_threshold: 최소 신뢰도 (기본 0.4 = 40%)
        iou_threshold: NMS IoU 임계값 (기본 0.45)
    
    Returns:
        감지 결과 리스트: [{"box": [x1,y1,x2,y2], "label": str, "score": float}, ...]
    """
    try:
        # YOLO 출력 형태 변환: (1, 7, 2100) → (2100, 7)
        # 각 행: [cx, cy, w, h, class0_score, class1_score, class2_score]
        raw_output = output[0].squeeze().T
        
        # 클래스별 점수 추출 (4번 인덱스부터)
        classes_scores = raw_output[:, 4:]
        max_scores = np.max(classes_scores, axis=1)      # 각 박스의 최고 점수
        class_ids_all = np.argmax(classes_scores, axis=1)  # 최고 점수 클래스
        
        # 1. 신뢰도 필터링
        mask = max_scores > conf_threshold
        if not np.any(mask):
            return []  # 감지된 객체 없음
        
        filtered_output = raw_output[mask]
        filtered_scores = max_scores[mask]
        filtered_class_ids = class_ids_all[mask]
        
        # 2. 좌표 추출 (중심점 + 크기)
        cx, cy = filtered_output[:, 0], filtered_output[:, 1]  # 중심 좌표
        w, h = filtered_output[:, 2], filtered_output[:, 3]    # 너비, 높이
        
        # 중심점 → 좌상단 좌표 변환
        x1 = (cx - w / 2).astype(np.int32)
        y1 = (cy - h / 2).astype(np.int32)
        w_int, h_int = w.astype(np.int32), h.astype(np.int32)
        
        # NMS 입력 포맷: [x, y, width, height]
        boxes = np.stack([x1, y1, w_int, h_int], axis=1).tolist()
        scores = filtered_scores.tolist()
        class_ids = filtered_class_ids.tolist()
        
        # 3. NMS (Non-Maximum Suppression): 중복 박스 제거
        # 겹치는 박스들 중 가장 신뢰도 높은 것만 유지
        indices = cv2.dnn.NMSBoxes(boxes, scores, conf_threshold, iou_threshold)
        
        # NMS 결과 처리 (OpenCV 버전별 반환 타입 차이 대응)
        results = []
        if isinstance(indices, tuple):
            indices = indices[0] if len(indices) > 0 else []
        
        if len(indices) > 0:
            if isinstance(indices, np.ndarray):
                indices = indices.flatten()
            
            # 최종 결과 포맷팅
            for idx in indices:
                if idx >= len(boxes):
                    continue
                    
                box = boxes[idx]
                x1, y1, w, h = box
                class_idx = class_ids[idx]
                label = _classes[class_idx] if class_idx < len(_classes) else "unknown"
                
                results.append({
                    "box": [x1, y1, x1 + w, y1 + h],  # [좌상단x, 좌상단y, 우하단x, 우하단y]
                    "label": label,                    # 클래스 이름
                    "score": round(scores[idx], 2)     # 신뢰도 (소수점 2자리)
                })
        
        return results
        
    except Exception as e:
        print(f"[AIModel] postprocess 오류: {e}")
        return []
