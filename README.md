# 🏠 YoloMung / YoloNyang  Home Protection System

> **최종 업데이트**: 2026년 1월 13일  
> **프로젝트명**: YoloMung / YoloNyang 

실시간 CCTV 영상 분석을 통한 스마트 홈 보안 시스템

---

## 📋 주요 기능

### 🎯 실시간 감지

| 기능               | 설명                                           |
| ------------------ | ---------------------------------------------- |
| **사람 감지**      | YOLO11n 모델로 사람 감지                       |
| **화재/연기 감지** | 화재 및 연기 감지 (5초 지속 시 알림)           |
| **거수자 감지**    | 5초 이상 체류 시 거수자로 판정                 |
| **이상행동 감지**  | 넘어짐, 손들기, 빠른동작 감지 (MediaPipe Pose) |

### 👥 사람 추적 시스템

- **ID 자동 부여**: 감지된 사람마다 고유 ID 할당
- **3장 자동 캡처**: ID당 0초, 1초, 2초 간격으로 3장 캡처
- **거수자 추가 캡처**: 5초 이상 체류 시 추가 캡처
- **화이트리스트**: 등록된 가족은 거수자 판정 제외

### 🎨 UI 표시

| 상태             | 박스 색상   | 라벨 표시                 | 관절 |
| ---------------- | ----------- | ------------------------- | ---- |
| 🟢 일반인        | 녹색 실선   | `사람 #0 85%`             | ❌   |
| 🟠 거수자 (5초+) | 주황색 점선 | `거수자 #0 85%` + ⚠️ 경고 | ✅   |
| 🔴 화재/연기     | 빨간색 점선 | `fire 95%`                | -    |

---

## 🛠 기술 스택

### Frontend

```
Next.js 14 + React 18
SCSS Modules
Motion (Framer Motion)
```

### Backend

```
FastAPI + Python
ONNX Runtime
OpenVINO
MediaPipePose
MySQL
```

### AI 모델

| 모델                  | 입력 크기 | 클래스              |
| --------------------- | --------- | ------------------- |
| `best.bin` (커스텀)  | 320x320   | person, fire, smoke |
| `yolo11n.onnx` (기본) | 640x640   | COCO 80 클래스      |

---

## 📁 프로젝트 구조

```
indigo_p/
├── src/                    # Next.js 프론트엔드
│   ├── app/
│   │   ├── (pages)/       # 페이지들
│   │   │   ├── cctv/      # CCTV 모니터링
│   │   │   ├── login/     # 로그인
│   │   │   └── ...
│   │   └── page.jsx       # 메인 페이지
│   └── components/        # UI 컴포넌트
│
├── backend/               # FastAPI 백엔드
│   ├── app/
│   │   ├── routers/       # API 라우터
│   │   │   ├── security.py    # 영상 분석 WebSocket
│   │   │   ├── kakao.py       # 카카오 알림
│   │   │   └── auth.py        # 인증
│   │   ├── services/      # 비즈니스 로직
│   │   │   ├── ai_model_service.py    # YOLO 추론
│   │   │   ├── tracker_service.py     # 객체 추적
│   │   │   ├── mediapipe_service.py   # 관절 추출
│   │   │   └── database_service.py    # DB/캡처 저장
│   │   └── utils/         # 유틸리티
│   ├── artifacts/         # ONNX 모델 파일
│   ├── captures/          # 캡처 이미지 저장
│   └── known_faces/       # 화이트리스트 얼굴
│
└── README.md
```

---

## 🚀 실행 방법

### 1. 백엔드 실행

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

### 2. 프론트엔드 실행

```bash
npm install
npm run dev
```

### 접속 URL

- 프론트엔드: http://localhost:3000
- 백엔드 API: http://localhost:8000

---

## 📡 API 엔드포인트

### 인증

| 엔드포인트     | 메서드 | 설명           |
| -------------- | ------ | -------------- |
| `/auth/signup` | POST   | 회원가입       |
| `/auth/login`  | POST   | 로그인         |
| `/auth/logout` | POST   | 로그아웃       |
| `/auth/check`  | GET    | 인증 상태 확인 |

### 보안

| 엔드포인트                     | 메서드    | 설명                |
| ------------------------------ | --------- | ------------------- |
| `/security/ws`                 | WebSocket | 실시간 영상 분석    |
| `/security/mediapipe/settings` | GET       | MediaPipe 설정 조회 |
| `/security/mediapipe/toggle`   | POST      | MediaPipe ON/OFF    |
| `/security/whitelist`          | GET       | 화이트리스트 목록   |
| `/security/whitelist/upload`   | POST      | 얼굴 이미지 등록    |

### 기타

| 엔드포인트      | 메서드 | 설명               |
| --------------- | ------ | ------------------ |
| `/api/captures` | GET    | 캡처 이미지 목록   |
| `/kakao/notify` | POST   | 카카오톡 알림 전송 |

---

## ⚙️ 주요 설정값

### tracker_service.py

```python
LOITERING_TIME = 5.0       # 거수자 기준 시간 (초)
TRACKER_TIMEOUT = 5.0      # 트래커 만료 시간 (초)
MAX_CAPTURES_PER_ID = 3    # ID당 최대 캡처 수
CAPTURE_INTERVALS = [0.0, 1.0, 2.0]  # 캡처 간격 (초)
```

### ai_model_service.py

```python
INPUT_SIZE = 320           # 모델 입력 크기
CONFIDENCE_THRESHOLD = 0.5 # 최소 신뢰도
IOU_THRESHOLD = 0.45       # NMS IOU 임계값
```

---

## 🎨 UI 컴포넌트

| 컴포넌트         | 설명                    |
| ---------------- | ----------------------- |
| `DayNightToggle` | 다크/라이트 모드 토글   |
| `RotatingText`   | 회전 텍스트 애니메이션  |
| `ScrollFloat`    | 스크롤 시 떠오르는 효과 |
| `ScrollReveal`   | 스크롤 시 나타나는 효과 |
| `TrueFocus`      | 포커스 강조 효과        |

---

## 📱 반응형 브레이크포인트

| 디바이스 | 너비           | UI 동작               |
| -------- | -------------- | --------------------- |
| 모바일   | < 768px        | 햄버거 메뉴           |
| 태블릿   | 768px ~ 1024px | 축소 사이드바 (60px)  |
| 데스크톱 | > 1024px       | 전체 사이드바 (250px) |

---

## 📝 최근 업데이트 (2026-01-13)

### 캡처 시스템 개선

- ✅ ID당 3장 자동 캡처 (0초, 1초, 2초 간격)
- ✅ 캡처 좌표 오류 수정 (640→320 변환 오류 해결)
- ✅ 화이트리스트 사용자 캡처 제외

### UI 개선

- ✅ 배회자 → 거수자 용어 변경
- ✅ 거수자 경고 표시 (⚠️ 거수자 주의!)
- ✅ 점선 박스로 위험 상황 강조
- ✅ 박스 색상 구분 (녹색/주황/빨강)

### 주석 정리

- ✅ 전체 백엔드 코드 주석 한글화 및 통일

---

## 📌 알려진 이슈

- Electron 데스크톱 앱 빌드 보류 (백엔드 패키징 문제)
- ESLint useEffect 의존성 경고 (기능에 영향 없음)

---

## 📄 라이선스

MIT License
