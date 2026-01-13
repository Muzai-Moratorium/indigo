"""
Tracker Service - 객체 추적 및 배회자 감지
===========================================
YOLO로 감지된 사람을 프레임 간 추적하고 배회자/이상행동을 감지

[핵심 개념]
1. 객체 추적 (Object Tracking)
   - 문제: YOLO는 매 프레임 독립적으로 감지 → "같은 사람"인지 모름
   - 해결: IoU(박스 겹침) + 중심점 거리로 이전 프레임 객체와 매칭

2. 배회자 감지 (Loitering Detection)
   - 같은 위치에 일정 시간(5초) 이상 머무르면 배회자로 판정
   - 화이트리스트(등록된 가족)는 배회자에서 제외

3. 이상행동 감지 (Abnormal Behavior Detection)
   - MediaPipe Pose로 관절 좌표 추출
   - 넘어짐, 손들기, 빠른 동작 등 감지

[알고리즘: IoU (Intersection over Union)]
- 두 박스의 겹침 정도를 0~1로 표현
- IoU = 교집합 영역 / 합집합 영역
- 0: 전혀 안 겹침, 1: 완전히 겹침
"""
import time

from app.services import mediapipe_service
from app.services.database_service import save_snapshot


# ==================================================
# 설정값 (Configuration)
# ==================================================

# 배회자 감지 설정
LOITERING_TIME = 5.0       # 배회 기준 시간 (초) - 이 시간 이상 머무르면 배회자
TRACKER_TIMEOUT = 5.0      # 트래커 만료 시간 (초) - 이 시간 동안 안 보이면 삭제
FACE_CHECK_INTERVAL = 30   # 얼굴 재검사 프레임 간격

# 이상행동 감지 설정
ABNORMAL_VELOCITY_THRESHOLD = 50  # 빠른 동작 임계값 (픽셀/프레임)
FALL_DETECTION_RATIO = 0.3        # 넘어짐 감지 비율 (사용 안 함)
KEYPOINT_HISTORY_LENGTH = 10      # 관절 히스토리 보관 프레임 수


# ==================================================
# 트래커 상태 (모듈 레벨 싱글톤)
# ==================================================
# 딕셔너리 구조: { track_id: { start_time, last_seen, box, ... }, ... }
_active_trackers = {}

# 다음에 할당할 트래커 ID (자동 증가)
_next_track_id = 0


# ==================================================
# 트래커 관리 함수
# ==================================================
def get_active_trackers():
    """현재 활성화된 모든 트래커 반환"""
    return _active_trackers


def get_active_tracker_count():
    """현재 추적 중인 사람 수 반환"""
    return len(_active_trackers)


def clear_trackers():
    """모든 트래커 초기화 (연결 종료 시 호출)"""
    global _active_trackers
    count = len(_active_trackers)
    _active_trackers.clear()
    return count


# ==================================================
# 유틸리티 함수
# ==================================================
def get_box_center(box):
    """
    바운딩 박스의 중심점 계산
    
    Args:
        box: [x1, y1, x2, y2] 좌상단, 우하단 좌표
    
    Returns:
        (center_x, center_y) 튜플
    """
    x1, y1, x2, y2 = box
    return ((x1 + x2) / 2, (y1 + y2) / 2)


def calculate_iou(box1, box2):
    """
    IoU (Intersection over Union) 계산
    
    [수식]
    IoU = 교집합 영역 / 합집합 영역
        = intersection / (area1 + area2 - intersection)
    
    [시각화]
    ┌─────────┐
    │  box1   │
    │    ┌────┼────┐
    │    │INTER│    │
    └────┼────┘    │
         │  box2   │
         └─────────┘
    
    Args:
        box1, box2: [x1, y1, x2, y2] 형태의 바운딩 박스
    
    Returns:
        0.0 ~ 1.0 사이의 IoU 값
    """
    # 교집합 영역 계산
    x1 = max(box1[0], box2[0])  # 교집합 좌상단 x
    y1 = max(box1[1], box2[1])  # 교집합 좌상단 y
    x2 = min(box1[2], box2[2])  # 교집합 우하단 x
    y2 = min(box1[3], box2[3])  # 교집합 우하단 y
    
    # 교집합 넓이 (음수면 겹치지 않음 → 0)
    intersection = max(0, x2 - x1) * max(0, y2 - y1)
    
    # 각 박스의 넓이
    area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
    area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
    
    # 합집합 = 두 넓이 합 - 교집합 (중복 제거)
    union = area1 + area2 - intersection
    
    return intersection / union if union > 0 else 0


# ==================================================
# 객체 매칭 (핵심 알고리즘)
# ==================================================
def match_detection_to_tracker(box):
    """
    새로 감지된 박스를 기존 트래커와 매칭
    
    [하이브리드 매칭 알고리즘]
    1. IoU 점수: 박스 겹침 정도 (크기 변화에 강함)
    2. 중심점 거리 점수: 위치 유사도 (빠른 이동에 강함)
    3. 복합 점수 = IoU × 0.5 + 거리점수 × 0.5
    
    [왜 하이브리드?]
    - IoU만 사용: 사람이 빠르게 움직이면 겹침이 적어서 새 ID 부여
    - 거리만 사용: 크기 변화나 여러 사람이 가까이 있으면 혼동
    - 둘 다 사용: 각각의 단점 보완
    
    Args:
        box: [x1, y1, x2, y2] 새로 감지된 박스
    
    Returns:
        매칭된 track_id (없으면 새 ID 생성)
    """
    global _next_track_id
    
    # 기존 트래커가 없으면 새로 생성
    if not _active_trackers:
        new_id = _next_track_id
        _next_track_id += 1
        return new_id
    
    best_match_id = None
    best_score = 0
    
    # 현재 박스의 중심점
    curr_center = get_box_center(box)
    
    # 모든 기존 트래커와 비교
    for track_id, tracker in _active_trackers.items():
        prev_box = tracker["box"]
        prev_center = get_box_center(prev_box)
        
        # 1. IoU 점수 (0 ~ 1)
        iou = calculate_iou(box, prev_box)
        
        # 2. 중심점 거리 점수
        # 유클리드 거리 계산: sqrt((x1-x2)² + (y1-y2)²)
        dist = ((curr_center[0] - prev_center[0])**2 + 
                (curr_center[1] - prev_center[1])**2) ** 0.5
        
        # 거리 → 점수 변환 (가까울수록 1, 100픽셀 이상이면 0)
        max_dist = 100  # 최대 허용 거리
        dist_score = max(0, 1 - dist / max_dist)
        
        # 3. 복합 점수 계산 (50:50 가중치)
        combined_score = iou * 0.5 + dist_score * 0.5
        
        # 최소 임계값 체크 (너무 다르면 매칭 안 함)
        min_threshold = 0.25
        if combined_score > min_threshold and combined_score > best_score:
            best_score = combined_score
            best_match_id = track_id
    
    if best_match_id is not None:
        return best_match_id
    else:
        # 매칭 실패 → 새 트래커 생성
        new_id = _next_track_id
        _next_track_id += 1
        return new_id


# ==================================================
# 이상행동 감지
# ==================================================
def analyze_abnormal_behavior(keypoints, keypoints_history):
    """
    MediaPipe 관절 좌표로 이상행동 분석
    
    [MediaPipe Pose 33개 관절]
    0: 코, 11-12: 어깨, 13-14: 팔꿈치, 15-16: 손목
    23-24: 엉덩이, 25-26: 무릎, 27-28: 발목
    
    [감지 행동]
    1. FALL: 넘어짐 (머리와 발목 높이 차이가 작음)
    2. HANDS_UP: 손들기/위협 (손목이 어깨보다 위)
    3. FAST_MOTION: 빠른 동작 (관절 이동 속도 임계값 초과)
    
    Args:
        keypoints: 현재 프레임 관절 좌표 [[x, y, confidence], ...]
        keypoints_history: 이전 프레임들의 관절 좌표 리스트
    
    Returns:
        감지된 행동 리스트 ["FALL", "HANDS_UP"] 또는 None
    """
    if not keypoints or len(keypoints) < 25:
        return None
    
    behaviors = []
    
    # ─────────────────────────────────────────────
    # 1. 넘어짐 감지 (FALL)
    # ─────────────────────────────────────────────
    # 정상: 머리가 위, 발이 아래 (y 차이 큼)
    # 넘어짐: 머리와 발 높이가 비슷 (y 차이 작음)
    nose_y = keypoints[0][1]       # 코 y좌표
    ankle_y = (keypoints[27][1] + keypoints[28][1]) / 2  # 발목 평균 y좌표
    
    height_diff = ankle_y - nose_y  # 발목 - 코 (정상이면 양수, 큰 값)
    if height_diff < 50:  # 50픽셀 미만이면 수평 자세 → 넘어짐
        behaviors.append("FALL")
    
    # ─────────────────────────────────────────────
    # 2. 손들기/위협 감지 (HANDS_UP)
    # ─────────────────────────────────────────────
    # 손목 y좌표 < 어깨 y좌표 → 손이 어깨보다 위
    # (좌표계: 위쪽이 0, 아래쪽이 큰 값)
    left_wrist_y = keypoints[15][1]
    right_wrist_y = keypoints[16][1]
    left_shoulder_y = keypoints[11][1]
    right_shoulder_y = keypoints[12][1]
    
    # 손목이 어깨보다 30픽셀 이상 위에 있으면
    if (left_wrist_y < left_shoulder_y - 30 or 
        right_wrist_y < right_shoulder_y - 30):
        # 신뢰도 체크 (오탐 방지)
        if keypoints[15][2] > 0.3 or keypoints[16][2] > 0.3:
            behaviors.append("HANDS_UP")
    
    # ─────────────────────────────────────────────
    # 3. 빠른 동작 감지 (FAST_MOTION)
    # ─────────────────────────────────────────────
    # 이전 프레임과 현재 프레임의 관절 이동 거리 계산
    if len(keypoints_history) >= 2:
        prev_kpts = keypoints_history[-1]  # 바로 이전 프레임
        
        if prev_kpts and len(prev_kpts) >= 25:
            total_velocity = 0
            count = 0
            
            # 손목(15,16)과 발목(27,28)의 이동 속도 측정
            for i in [15, 16, 27, 28]:
                # 신뢰도가 충분한 경우만 계산
                if keypoints[i][2] > 0.3 and prev_kpts[i][2] > 0.3:
                    dx = keypoints[i][0] - prev_kpts[i][0]
                    dy = keypoints[i][1] - prev_kpts[i][1]
                    velocity = (dx**2 + dy**2) ** 0.5  # 유클리드 거리
                    total_velocity += velocity
                    count += 1
            
            # 평균 속도가 임계값 초과하면 빠른 동작
            if count > 0 and (total_velocity / count) > ABNORMAL_VELOCITY_THRESHOLD:
                behaviors.append("FAST_MOTION")
    
    return behaviors if behaviors else None


# ==================================================
# 배회자 판정 (메인 로직)
# ==================================================
def check_loitering(track_id, box, frame, score, face_whitelist):
    """
    배회자 판정 및 이상행동 감지
    
    [판정 흐름]
    1. 새로운 사람 → 얼굴 인식으로 화이트리스트 체크
    2. 화이트리스트 → 배회자 판정 안 함
    3. 5초 이상 체류 → 배회자로 판정 + MediaPipe 적용
    4. 이상행동 감지 → 추가 알림
    
    Args:
        track_id: 추적 ID
        box: 바운딩 박스 [x1, y1, x2, y2]
        frame: 현재 프레임 이미지
        score: YOLO 신뢰도
        face_whitelist: 얼굴 인식 화이트리스트 객체
    
    Returns:
        {"type": "loitering"/"abnormal"/"tracking", "keypoints": [...]} 또는 None
    """
    now = time.time()
    
    # ─────────────────────────────────────────────
    # 새로운 사람 감지 (트래커에 없는 ID)
    # ─────────────────────────────────────────────
    if track_id not in _active_trackers:
        # 얼굴 인식으로 화이트리스트 체크
        is_whitelisted, whitelist_name = face_whitelist.check_face_in_box(frame, box)
        
        # 새 트래커 생성
        _active_trackers[track_id] = {
            "start_time": now,           # 첫 감지 시간
            "last_seen": now,            # 마지막 감지 시간
            "notified": False,           # 배회 알림 발송 여부
            "box": box,                  # 현재 바운딩 박스
            "is_whitelisted": is_whitelisted,     # 화이트리스트 여부
            "whitelist_name": whitelist_name or "",  # 등록된 이름
            "face_checked": True,        # 얼굴 검사 완료 여부
            "keypoints_history": [],     # 관절 좌표 히스토리
            "abnormal_notified": False,  # 이상행동 알림 발송 여부
            "last_keypoints": None       # 마지막 관절 좌표 (캐싱)
        }
        
        if is_whitelisted:
            print(f"[Whitelist] 등록된 사용자 감지: {whitelist_name} (ID: {track_id})")
        else:
            print(f"[Track] 새로운 사람 감지 (ID: {track_id})")
    
    # ─────────────────────────────────────────────
    # 기존 트래커 업데이트
    # ─────────────────────────────────────────────
    else:
        tracker = _active_trackers[track_id]
        tracker["last_seen"] = now
        tracker["box"] = box
        
        # 화이트리스트 사용자는 배회자 판정 스킵
        if tracker.get("is_whitelisted"):
            return None
        
        # 체류 시간 계산
        elapsed = now - tracker["start_time"]
        
        # ─────────────────────────────────────────
        # 배회자(5초+)에게 MediaPipe 적용
        # ─────────────────────────────────────────
        keypoints = None
        if elapsed >= LOITERING_TIME and mediapipe_service.is_enabled():
            # 프레임 간격에 따라 MediaPipe 호출 (성능 최적화)
            if mediapipe_service.should_process_frame():
                keypoints = mediapipe_service.extract_pose_keypoints(frame, box)
            elif tracker.get("last_keypoints"):
                # 이전 프레임 관절 재사용 (스킵된 프레임)
                keypoints = tracker["last_keypoints"]
            
            if keypoints:
                # 관절 히스토리 저장 (이상행동 분석용)
                tracker["keypoints_history"].append(keypoints)
                if len(tracker["keypoints_history"]) > KEYPOINT_HISTORY_LENGTH:
                    tracker["keypoints_history"].pop(0)  # 오래된 것 삭제
                tracker["last_keypoints"] = keypoints
                
                # 이상행동 분석
                abnormal = analyze_abnormal_behavior(keypoints, tracker["keypoints_history"])
                if abnormal and not tracker.get("abnormal_notified"):
                    print(f"[DANGER] 이상행동 감지! ID: {track_id} - {', '.join(abnormal)}")
                    save_snapshot(frame, score, box, track_id=track_id, 
                                stay_duration=elapsed, is_loitering=True)
                    tracker["abnormal_notified"] = True
                    return {"type": "abnormal", "behaviors": abnormal, "keypoints": keypoints}
        
        # ─────────────────────────────────────────
        # 첫 배회 판정 (5초 경과)
        # ─────────────────────────────────────────
        if not tracker["notified"] and elapsed >= LOITERING_TIME:
            print(f"[ALERT] 배회자 감지 ID: {track_id} - {elapsed:.1f}초 체류!")
            save_snapshot(frame, score, box, track_id=track_id, 
                         stay_duration=elapsed, is_loitering=True)
            tracker["notified"] = True
            return {"type": "loitering", "keypoints": keypoints, "elapsed": elapsed}
        
        # 이미 배회자로 판정된 경우 → 관절 정보만 반환
        if tracker["notified"] and keypoints:
            return {"type": "tracking", "keypoints": keypoints}
    
    return None


# ==================================================
# 트래커 정리
# ==================================================
def cleanup_old_trackers():
    """
    오래된 트래커 정리 (매 프레임 호출)
    
    TRACKER_TIMEOUT 시간 동안 감지되지 않은 트래커 삭제
    → 사람이 화면에서 사라졌거나 감지 실패한 경우
    """
    now = time.time()
    
    # 만료된 트래커 ID 수집
    expired = [
        tid for tid, t in _active_trackers.items() 
        if now - t["last_seen"] > TRACKER_TIMEOUT
    ]
    
    # 삭제 및 로그 출력
    for tid in expired:
        elapsed = _active_trackers[tid]["last_seen"] - _active_trackers[tid]["start_time"]
        print(f"[Leave] ID: {tid} - 총 체류시간: {elapsed:.1f}초")
        del _active_trackers[tid]
