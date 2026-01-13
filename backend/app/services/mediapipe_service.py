"""
MediaPipe Service - 관절(Pose) 추출 서비스
============================================
MediaPipe Pose를 사용하여 사람의 33개 관절 좌표 추출

[MediaPipe란?]
- Google에서 개발한 ML 파이프라인 프레임워크
- 얼굴, 손, 포즈 등 다양한 인체 인식 모델 제공
- 실시간 처리에 최적화됨

[Pose Landmarker 33개 관절]
  0: 코 (nose)
  1-4: 눈 (눈썹, 눈, 눈끝)
  5-8: 귀
  9-10: 입
  11-12: 어깨 (왼쪽, 오른쪽)
  13-14: 팔꿈치
  15-16: 손목
  17-22: 손가락 (검지, 새끼, 엄지)
  23-24: 엉덩이
  25-26: 무릎
  27-28: 발목
  29-32: 발 (뒤꿈치, 발가락)

[좌표계]
- 각 관절: [x, y, visibility]
- x, y: 0.0 ~ 1.0 (정규화된 좌표)
- visibility: 0.0 ~ 1.0 (보이는 정도, 높을수록 신뢰도 높음)
"""
import os
import cv2

from app.utils.path_utils import MODELS_DIR


# ==================================================
# 설정값 (Configuration)
# ==================================================
MEDIAPIPE_ENABLED = True     # MediaPipe 활성화 여부
MEDIAPIPE_FRAME_INTERVAL = 2  # N 프레임마다 1번 호출 (성능 최적화)
_frame_counter = 0           # 현재 프레임 카운터


# ==================================================
# MediaPipe Pose Detector (모듈 레벨 싱글톤)
# ==================================================
_pose_detector = None


def _init_mediapipe():
    """
    MediaPipe Pose Landmarker 초기화
    
    [모델 파일]
    - pose_landmarker_lite.task: 경량 모델 (빠르지만 정확도 약간 낮음)
    - pose_landmarker_full.task: 정밀 모델 (정확하지만 느림)
    - pose_landmarker_heavy.task: 최고 정밀 (가장 느림)
    
    [초기화 과정]
    1. 모델 파일 경로 확인
    2. BaseOptions로 모델 로드
    3. PoseLandmarkerOptions로 설정 지정
    4. PoseLandmarker 객체 생성
    """
    global _pose_detector
    
    try:
        # MediaPipe Tasks API (새로운 방식)
        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision as mp_vision
        
        # 모델 파일 경로 (models 폴더에 저장)
        pose_model_path = os.path.join(MODELS_DIR, "pose_landmarker_lite.task")
        print(f"[MediaPipe] 모델 경로: {pose_model_path}")
        print(f"[MediaPipe] 모델 파일 존재: {os.path.exists(pose_model_path)}")
        
        if os.path.exists(pose_model_path):
            # 기본 옵션 (모델 경로 지정)
            base_options = mp_python.BaseOptions(model_asset_path=pose_model_path)
            
            # Pose Landmarker 옵션
            options = mp_vision.PoseLandmarkerOptions(
                base_options=base_options,
                output_segmentation_masks=False  # 세그멘테이션 마스크 불필요 (성능 향상)
            )
            
            # Pose Landmarker 생성
            _pose_detector = mp_vision.PoseLandmarker.create_from_options(options)
            print("[MediaPipe] Pose Landmarker 초기화 완료!")
        else:
            print(f"[MediaPipe] Pose 모델 없음: {pose_model_path}")
            print("[MediaPipe] YOLO 단독 모드로 실행 (관절 추출 비활성화)")
            
    except Exception as e:
        import traceback
        print(f"[MediaPipe] 초기화 실패: {e}")
        traceback.print_exc()
        print("[MediaPipe] YOLO 단독 모드로 실행 (관절 추출 비활성화)")


# 모듈 import 시 자동 초기화
_init_mediapipe()


# ==================================================
# 상태 조회 함수
# ==================================================
def is_available():
    """MediaPipe 사용 가능 여부 (모델 로드 성공 여부)"""
    return _pose_detector is not None


def is_enabled():
    """MediaPipe 활성화 여부 (사용자 설정)"""
    return MEDIAPIPE_ENABLED


def get_frame_interval():
    """현재 호출 주기 (N 프레임마다 1번)"""
    return MEDIAPIPE_FRAME_INTERVAL


# ==================================================
# 설정 변경 함수 (API에서 호출)
# ==================================================
def toggle(enabled: bool):
    """
    MediaPipe 켜기/끄기
    
    Args:
        enabled: True=활성화, False=비활성화
    
    Returns:
        {"success": bool, "enabled": bool, "message": str}
    """
    global MEDIAPIPE_ENABLED
    MEDIAPIPE_ENABLED = enabled
    status = "활성화" if enabled else "비활성화"
    print(f"[MediaPipe] {status}")
    return {
        "success": True,
        "enabled": MEDIAPIPE_ENABLED,
        "message": f"MediaPipe {status}됨"
    }


def set_interval(interval: int):
    """
    호출 주기 설정 (N 프레임마다 1번)
    
    [성능 vs 정확도 트레이드오프]
    - 1: 최고 정확도, 가장 느림
    - 5: 균형 (기본값)
    - 30: 최고 성능, 반응 느림
    
    Args:
        interval: 1~30 사이 값
    
    Returns:
        {"success": bool, "frameInterval": int, "message": str}
    """
    global MEDIAPIPE_FRAME_INTERVAL
    
    # 범위 제한 (1~30)
    if interval < 1:
        interval = 1
    elif interval > 30:
        interval = 30
    
    MEDIAPIPE_FRAME_INTERVAL = interval
    print(f"[MediaPipe] 호출 주기: {interval} 프레임")
    
    return {
        "success": True,
        "frameInterval": MEDIAPIPE_FRAME_INTERVAL,
        "message": f"MediaPipe {interval}프레임마다 호출"
    }


# ==================================================
# 프레임 처리 제어
# ==================================================
def should_process_frame():
    """
    현재 프레임을 처리해야 하는지 확인
    
    [동작 원리]
    - 매 호출마다 _frame_counter 증가
    - MEDIAPIPE_FRAME_INTERVAL에 도달하면 True 반환 후 리셋
    - 예: interval=5 → 5번에 1번만 True
    
    Returns:
        True: 이 프레임 처리, False: 스킵
    """
    global _frame_counter
    _frame_counter += 1
    
    if _frame_counter >= MEDIAPIPE_FRAME_INTERVAL:
        _frame_counter = 0
        return True
    return False


def reset_frame_counter():
    """프레임 카운터 초기화 (새 추적 시작 시)"""
    global _frame_counter
    _frame_counter = 0


# ==================================================
# 관절 추출 (핵심 기능)
# ==================================================
def extract_pose_keypoints(frame, box):
    """
    사람 영역(ROI)에서 33개 관절 좌표 추출
    
    [처리 과정]
    1. YOLO 박스 좌표 → 원본 프레임 좌표로 변환
    2. ROI 크롭 (사람 영역만 추출)
    3. 작은 ROI 리사이즈 (최소 100x100)
    4. BGR → RGB 변환 (MediaPipe 입력 포맷)
    5. MediaPipe Pose 추론
    6. ROI 좌표 → 모델 입력 좌표로 역변환
    
    [좌표 변환 설명]
    - YOLO 출력: 320x320 기준 좌표
    - 프레임: 실제 카메라 해상도 (예: 640x480)
    - MediaPipe: ROI 내 정규화 좌표 (0~1)
    
    변환 순서:
    YOLO(320) → 프레임(640) → ROI → MediaPipe → ROI → 프레임 → YOLO(320)
    
    Args:
        frame: 전체 프레임 이미지 (OpenCV BGR)
        box: YOLO 바운딩 박스 [x1, y1, x2, y2] (320x320 기준)
    
    Returns:
        [[x, y, visibility], ...] 33개 관절 또는 None
    """
    if _pose_detector is None:
        return None
        
    try:
        import mediapipe as mp
        from app.services import ai_model_service
        
        # 프레임 크기
        h, w = frame.shape[:2]
        
        # ─────────────────────────────────────────
        # 1. 좌표 변환: YOLO(320) → 프레임(실제 해상도)
        # ─────────────────────────────────────────
        input_size = ai_model_service.get_input_size()  # 320
        scale_x = w / input_size  # 예: 640/320 = 2.0
        scale_y = h / input_size  # 예: 480/320 = 1.5
        
        # 박스 좌표 스케일 변환
        x1 = int(max(0, box[0] * scale_x))
        y1 = int(max(0, box[1] * scale_y))
        x2 = int(min(w, box[2] * scale_x))
        y2 = int(min(h, box[3] * scale_y))
        
        # ─────────────────────────────────────────
        # 2. ROI 크롭 (사람 영역만)
        # ─────────────────────────────────────────
        roi = frame[y1:y2, x1:x2]
        if roi.size == 0:
            return None
        
        # ─────────────────────────────────────────
        # 3. 작은 ROI 리사이즈 (MediaPipe 정확도 향상)
        # ─────────────────────────────────────────
        roi_h, roi_w = roi.shape[:2]
        if roi_h < 100 or roi_w < 100:
            roi = cv2.resize(roi, (max(100, roi_w), max(100, roi_h)))
            roi_h, roi_w = roi.shape[:2]
        
        # ─────────────────────────────────────────
        # 4. MediaPipe 입력 준비 (BGR → RGB)
        # ─────────────────────────────────────────
        rgb_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_roi)
        
        # ─────────────────────────────────────────
        # 5. Pose 추론
        # ─────────────────────────────────────────
        results = _pose_detector.detect(mp_image)
        
        # ─────────────────────────────────────────
        # 6. 결과 좌표 변환 (ROI → 모델 입력 좌표)
        # ─────────────────────────────────────────
        if results.pose_landmarks and len(results.pose_landmarks) > 0:
            keypoints = []
            
            for landmark in results.pose_landmarks[0]:
                # landmark.x, landmark.y: 0~1 정규화 좌표 (ROI 기준)
                # ROI 좌표로 변환 후 → 모델 입력 좌표로 역변환
                lx = (landmark.x * roi_w + x1) / scale_x
                ly = (landmark.y * roi_h + y1) / scale_y
                
                keypoints.append([lx, ly, landmark.visibility])
            
            return keypoints
            
        return None
        
    except Exception as e:
        # 에러 로그 중복 방지 (첫 번째만 출력)
        if not hasattr(extract_pose_keypoints, '_error_logged'):
            print(f"[MediaPipe] 관절 추출 오류: {e}")
            extract_pose_keypoints._error_logged = True
        return None
