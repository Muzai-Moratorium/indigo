"""
Database Service - Guardian DB 연동
====================================
감지 이력 저장 및 스냅샷 관리
"""
import os
import cv2
import mysql.connector
from datetime import datetime

from app.utils.path_utils import CAPTURE_DIR
from app.services import ai_model_service


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
    
    prefix = "loiterer" if is_loitering else "person"
    filename = f"{prefix}_{timestamp_file}.jpg"
    filepath = os.path.join(CAPTURE_DIR, filename)

    # 저장할 이미지 결정
    save_image = frame
    
    # 박스 정보가 있으면 해당 영역만 크롭
    if box is not None:
        x1, y1, x2, y2 = box
        h, w = frame.shape[:2]
        
        # YOLO 추론 좌표를 원본 프레임 좌표로 변환
        input_size = ai_model_service.get_input_size()  # 320 또는 640
        scale_x = w / input_size
        scale_y = h / input_size
        
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
            event_type = "[ALERT] 거수자" if is_loitering else "[INFO] Person"
            print(f"{event_type} 캡처! 이미지 저장: {filename} | 체류: {stay_duration:.1f}초 | 시간: {timestamp_display}")
            save_to_database(filepath, score, track_id=track_id, stay_duration=stay_duration, is_loitering=is_loitering)
        else:
            print(f"[Security] [ERROR] 이미지 인코딩 실패: {filename}")
    except Exception as e:
        print(f"[Security] [ERROR] 이미지 저장 실패: {e}")
