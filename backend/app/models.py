from sqlalchemy import Column, Integer, String, Float, DateTime, Enum, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True)
    password = Column(String(255))
    created_at = Column(DateTime, default=datetime.now)

class DetectionLog(Base):
    """감지 이력 테이블"""
    __tablename__ = "detection_logs"

    id = Column(Integer, primary_key=True, index=True)
    track_id = Column(Integer, nullable=False, comment="추적 ID")
    image_path = Column(String(255), nullable=False, comment="이미지 경로")
    detection_type = Column(Enum('simple_pass', 'loitering'), default='simple_pass', comment="감지 종류")
    stay_duration = Column(Float, default=0, comment="체류 시간(초)")
    confidence_score = Column(Float, nullable=False, comment="AI 신뢰도")
    created_at = Column(DateTime, default=datetime.now, comment="감지 시간")
    
    # 알림 이력과의 관계
    notifications = relationship("NotificationLog", back_populates="detection")

class NotificationLog(Base):
    """알림 발송 이력 테이블"""
    __tablename__ = "notification_logs"

    id = Column(Integer, primary_key=True, index=True)
    detection_id = Column(Integer, ForeignKey("detection_logs.id", ondelete="CASCADE"), nullable=False)
    notification_type = Column(Enum('kakao', 'email', 'sms'), default='kakao', comment="알림 종류")
    status = Column(Enum('success', 'fail', 'pending'), default='pending', comment="발송 상태")
    error_message = Column(Text, nullable=True, comment="에러 메시지")
    sent_at = Column(DateTime, default=datetime.now, comment="발송 시간")
    
    # 감지 이력과의 관계
    detection = relationship("DetectionLog", back_populates="notifications")

