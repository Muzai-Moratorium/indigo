from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import mysql.connector

# Guardian 스키마로 변경
SQLALCHEMY_DATABASE_URL = "mysql+mysqlconnector://root:1234@localhost:3306/guardian"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def init_db():
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
            
            # 감지 이력 테이블 (detection_logs)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS detection_logs (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    track_id INT NOT NULL COMMENT '추적 ID',
                    image_path VARCHAR(255) NOT NULL COMMENT '이미지 경로',
                    detection_type ENUM('simple_pass', 'loitering') NOT NULL DEFAULT 'simple_pass' COMMENT '감지 종류',
                    stay_duration FLOAT NOT NULL DEFAULT 0 COMMENT '체류 시간(초)',
                    confidence_score FLOAT NOT NULL COMMENT 'AI 신뢰도',
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '감지 시간',
                    INDEX idx_detection_type (detection_type),
                    INDEX idx_created_at (created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='감지 이력'
            """)
            
            # 알림 발송 이력 테이블 (notification_logs)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS notification_logs (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    detection_id INT NOT NULL COMMENT '감지 이력 ID',
                    notification_type ENUM('kakao', 'email', 'sms') NOT NULL DEFAULT 'kakao' COMMENT '알림 종류',
                    status ENUM('success', 'fail', 'pending') NOT NULL DEFAULT 'pending' COMMENT '발송 상태',
                    error_message TEXT NULL COMMENT '에러 메시지',
                    sent_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '발송 시간',
                    FOREIGN KEY (detection_id) REFERENCES detection_logs(id) ON DELETE CASCADE,
                    INDEX idx_status (status),
                    INDEX idx_sent_at (sent_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='알림 발송 이력'
            """)
            
            # 사용자 테이블 (users)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    password VARCHAR(255) NOT NULL,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='사용자'
            """)
            
            connection.commit()
            print("[Guardian] 데이터베이스 테이블 초기화 완료")
            cursor.close()
            connection.close()
    except mysql.connector.Error as e:
        print(f"[Guardian Init Error] {e}")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

