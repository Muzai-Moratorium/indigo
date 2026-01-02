"""
얼굴 인식 화이트리스트 모듈 (OpenCV DNN 기반)

- 서버 시작 시 known_faces/ 폴더의 얼굴 인코딩 로드
- YOLO 바운딩 박스 내 얼굴 탐지 및 매칭 수행
- OpenCV DNN FaceNet 기반 가벼운 얼굴 인식
"""

import cv2
import numpy as np
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from typing import Tuple, Optional, List, Union


class FaceRecognitionWhitelist:
    """OpenCV DNN 기반 얼굴 인식 화이트리스트 시스템"""
    
    # 얼굴 인식 설정
    FACE_DETECTION_CONFIDENCE = 0.5  # 얼굴 탐지 최소 신뢰도
    FACE_MATCH_THRESHOLD = 0.6       # 얼굴 매칭 임계값 (낮을수록 엄격)
    
    def __init__(self, known_faces_dir: str, models_dir: Union[str, Path, None] = None):
        """
        Args:
            known_faces_dir: 등록된 얼굴 이미지 폴더 경로
            models_dir: OpenCV DNN 모델 파일 경로 (없으면 자동 생성)
        """
        self.known_faces_dir = Path(known_faces_dir)
        self.known_faces_dir.mkdir(exist_ok=True)
        
        # 등록된 얼굴 인코딩 저장
        self.known_encodings: List[np.ndarray] = []
        self.known_names: List[str] = []
        
        # 비동기 처리용 스레드풀
        self.executor = ThreadPoolExecutor(max_workers=2)
        
        # 모델 디렉토리 설정
        if models_dir is None:
            self.models_dir = Path(__file__).parent.parent.parent / "models" / "face"
        else:
            self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        # OpenCV DNN 얼굴 탐지기 초기화
        self._init_face_detector()
        
        # 등록된 얼굴 로드
        self._load_known_faces()
    
    def _init_face_detector(self):
        """OpenCV DNN 기반 얼굴 탐지기 초기화"""
        # OpenCV의 기본 Haar Cascade 사용 (가장 가벼움)
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        self.face_cascade = cv2.CascadeClassifier(cascade_path)
        
        if self.face_cascade.empty():
            print("[FaceRecognition] [ERROR] 얼굴 탐지 모델 로드 실패")
        else:
            print("[FaceRecognition] 얼굴 탐지기 초기화 완료 (Haar Cascade)")
    
    def _load_known_faces(self):
        """서버 시작 시 known_faces/ 폴더의 얼굴 인코딩 로드"""
        self.known_encodings.clear()
        self.known_names.clear()
        
        if not self.known_faces_dir.exists():
            print(f"[FaceRecognition] 화이트리스트 폴더 없음: {self.known_faces_dir}")
            return
        
        # 지원 이미지 확장자
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp'}
        
        for img_path in self.known_faces_dir.iterdir():
            if img_path.suffix.lower() not in image_extensions:
                continue
            
            try:
                # 이미지 로드 (한글 경로 지원)
                # cv2.imread()는 한글 경로를 지원하지 않으므로 numpy로 읽음
                with open(img_path, 'rb') as f:
                    img_data = np.frombuffer(f.read(), np.uint8)
                img = cv2.imdecode(img_data, cv2.IMREAD_COLOR)
                
                if img is None:
                    print(f"[FaceRecognition] [WARN] 이미지 로드 실패: {img_path.name}")
                    continue
                
                # 얼굴 탐지
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                faces = self.face_cascade.detectMultiScale(
                    gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
                )
                
                if len(faces) == 0:
                    print(f"[FaceRecognition] [WARN] 얼굴 없음: {img_path.name}")
                    continue
                
                # 가장 큰 얼굴 선택
                x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
                face_roi = img[y:y+h, x:x+w]
                
                # 얼굴 인코딩 생성 (간단한 히스토그램 기반)
                encoding = self._get_face_encoding(face_roi)
                
                # 파일명에서 사용자 이름 추출 (확장자 제거, _숫자 제거)
                name = img_path.stem
                # 예: "홍길동_1" -> "홍길동"
                if '_' in name and name.rsplit('_', 1)[-1].isdigit():
                    name = name.rsplit('_', 1)[0]
                
                self.known_encodings.append(encoding)
                self.known_names.append(name)
                
                print(f"[FaceRecognition] 등록: {name} ({img_path.name})")
                
            except Exception as e:
                print(f"[FaceRecognition] [ERROR] 처리 실패 {img_path.name}: {e}")
        
        print(f"[FaceRecognition] {len(self.known_names)}명의 화이트리스트 사용자 로드 완료")
    
    def _get_face_encoding(self, face_img: np.ndarray) -> np.ndarray:
        """
        얼굴 이미지에서 특징 벡터(인코딩) 추출
        - OpenCV 히스토그램 + 리사이즈 기반 간단한 인코딩
        """
        # 얼굴 이미지를 고정 크기로 리사이즈
        face_resized = cv2.resize(face_img, (64, 64))
        
        # 그레이스케일 변환
        if len(face_resized.shape) == 3:
            gray = cv2.cvtColor(face_resized, cv2.COLOR_BGR2GRAY)
        else:
            gray = face_resized
        
        # LBP (Local Binary Pattern) 유사 특징 추출
        # 히스토그램 기반 간단한 인코딩
        hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
        hist = cv2.normalize(hist, hist).flatten()
        
        # 추가: 평탄화된 픽셀 값도 포함
        flattened = gray.flatten().astype(np.float32) / 255.0
        
        # 히스토그램 + 리사이즈된 특징 결합
        encoding = np.concatenate([hist, flattened[:256]])
        
        return encoding
    
    def _compare_faces(self, encoding1: np.ndarray, encoding2: np.ndarray) -> float:
        """두 얼굴 인코딩 비교 (유사도 반환, 0~1, 낮을수록 유사)"""
        # 코사인 유사도 기반 거리
        norm1 = np.linalg.norm(encoding1)
        norm2 = np.linalg.norm(encoding2)
        
        if norm1 == 0 or norm2 == 0:
            return 1.0
        
        similarity = np.dot(encoding1, encoding2) / (norm1 * norm2)
        distance = 1 - similarity
        
        return distance
    
    def check_face_in_box(self, frame: np.ndarray, box: List[int]) -> Tuple[bool, Optional[str]]:
        """
        바운딩 박스 내 얼굴이 화이트리스트에 있는지 확인
        
        Args:
            frame: 원본 프레임
            box: YOLO 바운딩 박스 [x1, y1, x2, y2] (640x640 기준)
        
        Returns:
            (is_whitelisted, person_name) - 화이트리스트 여부와 인식된 이름
        """
        if len(self.known_encodings) == 0:
            return False, None
        
        try:
            # 바운딩 박스 좌표 추출 (640x640 -> 원본 스케일 변환)
            x1, y1, x2, y2 = box
            h, w = frame.shape[:2]
            
            scale_x = w / 640
            scale_y = h / 640
            
            x1 = int(max(0, x1 * scale_x))
            y1 = int(max(0, y1 * scale_y))
            x2 = int(min(w, x2 * scale_x))
            y2 = int(min(h, y2 * scale_y))
            
            # 사람 영역 크롭
            person_roi = frame[y1:y2, x1:x2]
            
            if person_roi.size == 0:
                return False, None
            
            # 크롭된 영역에서 얼굴 탐지
            gray = cv2.cvtColor(person_roi, cv2.COLOR_BGR2GRAY)
            faces = self.face_cascade.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=5, minSize=(20, 20)
            )
            
            if len(faces) == 0:
                return False, None
            
            # 가장 큰 얼굴 선택
            fx, fy, fw, fh = max(faces, key=lambda f: f[2] * f[3])
            face_roi = person_roi[fy:fy+fh, fx:fx+fw]
            
            if face_roi.size == 0:
                return False, None
            
            # 얼굴 인코딩 생성
            encoding = self._get_face_encoding(face_roi)
            
            # 등록된 얼굴과 비교
            best_match_idx = -1
            best_distance = self.FACE_MATCH_THRESHOLD
            
            for idx, known_enc in enumerate(self.known_encodings):
                distance = self._compare_faces(encoding, known_enc)
                if distance < best_distance:
                    best_distance = distance
                    best_match_idx = idx
            
            if best_match_idx >= 0:
                matched_name = self.known_names[best_match_idx]
                return True, matched_name
            
            return False, None
            
        except Exception as e:
            print(f"[FaceRecognition] 얼굴 인식 오류: {e}")
            return False, None
    
    def reload_known_faces(self):
        """화이트리스트 얼굴 다시 로드 (새 사용자 추가 시)"""
        print("[FaceRecognition] 화이트리스트 새로고침...")
        self._load_known_faces()
    
    def get_whitelist_count(self) -> int:
        """등록된 화이트리스트 사용자 수"""
        return len(set(self.known_names))
    
    def get_whitelist_names(self) -> List[str]:
        """등록된 화이트리스트 사용자 이름 목록"""
        return list(set(self.known_names))
