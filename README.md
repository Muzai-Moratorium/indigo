# Cat Finder 프로젝트 중간 보고서

> **작성일**: 2024년 12월 31일  
> **프로젝트**: 실시간 사람 감지 웹 애플리케이션

---

## 1. 프로젝트 개요

| 항목             | 내용                  |
| ---------------- | --------------------- |
| **프론트엔드**   | Next.js + React       |
| **백엔드**       | FastAPI + Python      |
| **AI 모델**      | YOLOv8 (ONNX)         |
| **데이터베이스** | MySQL                 |
| **인증**         | JWT + HttpOnly Cookie |

---

## 2. 완료된 기능

### 2.1 실시간 사람 감지

- ✅ 웹캠을 통한 실시간 영상 스트리밍
- ✅ YOLOv8 모델을 이용한 사람 감지
- ✅ 감지 시 자동 스냅샷 저장 (10초 쿨다운)
- ✅ MySQL 데이터베이스에 기록 저장
- ✅ 파일명 형식: `person_2024년12월31일_14시30분51초.jpg`

### 2.2 사용자 인증 시스템

- ✅ 회원가입 (bcrypt 비밀번호 해싱)
- ✅ 로그인 (JWT 토큰 발급)
- ✅ HttpOnly 쿠키 기반 보안 인증
- ✅ 로그아웃
- ✅ 로그인 상태 확인 API
- ✅ Protected Route (로그인 필수 페이지)

### 2.3 반응형 UI

- ✅ 모바일/태블릿/데스크톱 대응
- ✅ 햄버거 메뉴 (모바일)
- ✅ 축소 사이드바 (태블릿)
- ✅ 반응형 카메라 뷰어

---

## 3. 기술 스택

### 프론트엔드

```
Next.js 14
React 18
SCSS Modules
```

### 백엔드

```
FastAPI
uvicorn
ONNX Runtime (YOLOv8)
MySQL Connector
bcrypt + python-jose (JWT)
```

---

## 4. API 엔드포인트

| 엔드포인트      | 메서드    | 설명             |
| --------------- | --------- | ---------------- |
| `/auth/signup`  | POST      | 회원가입         |
| `/auth/login`   | POST      | 로그인           |
| `/auth/logout`  | POST      | 로그아웃         |
| `/auth/me`      | GET       | 내 정보          |
| `/auth/check`   | GET       | 인증 상태 확인   |
| `/ws`           | WebSocket | 실시간 영상 감지 |
| `/api/captures` | GET       | 캡처 이미지 목록 |

---

## 5. 브레이크포인트

| 디바이스 | 너비           | UI 동작                     |
| -------- | -------------- | --------------------------- |
| 모바일   | < 768px        | 사이드바 숨김 + 햄버거 메뉴 |
| 태블릿   | 768px ~ 1024px | 사이드바 축소 (60px)        |
| 데스크톱 | > 1024px       | 사이드바 전체 (250px)       |

---

## 6. 향후 계획

- [ ] UI 디자인 완성
- [ ] 감지 기록 조회 페이지
- [ ] 관리자 대시보드
- [ ] 알림 기능 (이메일/푸시)

---

## 7. 실행 방법

```bash
# 백엔드
cd backend
python -m uvicorn main:app --reload

# 프론트엔드
npm run dev
```

**접속 URL**

- 프론트엔드: http://localhost:3000
- 백엔드: http://localhost:8000

---

## 8. Electron 데스크톱 앱 (2026-01-02 추가)

### 8.1 개요

Next.js 웹 앱을 Windows 데스크톱 앱(.exe)으로 패키징하는 기능 추가.

| 항목            | 내용                               |
| --------------- | ---------------------------------- |
| **패키징 도구** | electron-packager                  |
| **빌드 결과**   | `dist-electron/Cat App-win32-x64/` |
| **앱 크기**     | ~200MB                             |

### 8.2 추가된 파일

| 파일                  | 용도                                      |
| --------------------- | ----------------------------------------- |
| `electron/main.js`    | Electron 메인 프로세스                    |
| `electron/preload.js` | 보안 preload 스크립트                     |
| `build_backend.py`    | PyInstaller 백엔드 빌드 스크립트 (미사용) |

### 8.3 사용 방법

```bash
# 웹 개발 모드
npm run dev

# Electron 개발 모드
npm run electron:dev

# 프로덕션 빌드 (EXE 생성)
$env:ELECTRON_BUILD='true'; npm run build
npx electron-packager . "Cat App" --platform=win32 --arch=x64 --out=dist-electron --overwrite
```

### 8.4 현재 상태

- ✅ 메인 화면 표시
- ✅ CSS 스타일 적용
- ⚠️ 페이지 네비게이션 (부분 작동 - 추가 수정 필요)
- ⚠️ 백엔드 통합 (별도 서버 실행 필요)

---

## 9. 빌드 과정 문제점 및 해결 (2026-01-02)

### 문제 1: electron-builder 빌드 실패

**증상**: `npm run build:electron` 실행 시 반복적으로 exit code 1 발생

**원인**:

- `extraResources`에서 `dist-backend` 폴더 참조 (존재하지 않음)
- `public/icon.ico` 아이콘 파일 미존재

**해결**:

- electron-builder 대신 **electron-packager** 사용
- `package.json`에서 `extraResources` 및 `icon` 설정 제거

---

### 문제 2: 하얀 화면 (빈 화면)

**증상**: Cat App.exe 실행 시 아무것도 표시 안 됨

**원인**:

- `out/` 폴더가 없음 (Next.js static export 미실행)
- `next.config.mjs`의 `output: 'export'` 설정이 개발 모드에서만 비활성화됨
- 환경변수 `ELECTRON_BUILD=true` 없이 빌드하면 static export 안 됨

**해결**:

```powershell
$env:ELECTRON_BUILD='true'; npm run build
```

---

### 문제 3: CSS 미적용

**증상**: 앱 화면은 나오지만 스타일이 없음 (텍스트만 표시)

**원인**:

- Next.js 빌드가 절대 경로(`/_next/...`)로 CSS 참조
- Electron의 `file://` 프로토콜에서 루트 경로를 찾지 못함

**해결**:

- `next.config.mjs`에 `assetPrefix: './'` 추가

```javascript
...(isElectronBuild && {
  output: 'export',
  trailingSlash: true,
  assetPrefix: './',  // 상대 경로로 변경
}),
```

---

### 문제 4: 페이지 네비게이션 안 됨 (진행 중)

**증상**: 로그인, CCTV 등 다른 페이지 클릭 시 하얀 화면

**원인**:

- SPA 라우팅이 브라우저 History API 사용
- Electron의 `file://` 프로토콜에서는 History API가 작동하지 않음

**시도한 해결**:

- `electron/main.js`에 `will-navigate` 이벤트 핸들러 추가
- URL을 로컬 HTML 파일 경로로 변환

**현재 상태**: 추가 디버깅 필요

---

## 10. 향후 Electron 관련 작업

- [ ] 페이지 네비게이션 문제 완전 해결
- [ ] 백엔드 PyInstaller 패키징 및 통합
- [ ] 앱 아이콘 추가 (`public/icon.ico`)
- [ ] 자동 업데이트 기능
- [ ] 설치 프로그램 생성 (NSIS)
