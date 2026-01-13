"""
Kakao Router - 카카오톡 알림 시스템
==================================
카카오 OAuth 연동 및 메시지 전송

주요 기능:
- 카카오 OAuth 로그인 (GET /kakao/login, /kakao/callback)
- 카카오톡 메시지 전송 (POST /kakao/send-message)
- 연동 상태 확인 (GET /kakao/status)
- 배회자 감지 알림 전송 (notify_loitering)
"""
from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import RedirectResponse
import httpx
import os

router = APIRouter(prefix="/kakao", tags=["kakao"])

# ============================================
# 카카오 API 설정
# ============================================
# TODO: 실제 값으로 변경 필요
KAKAO_REST_API_KEY = os.getenv("KAKAO_REST_API_KEY", "your-rest-api-key")
KAKAO_REDIRECT_URI = "http://localhost:8000/kakao/callback"

# 토큰 저장 (실제 서비스에서는 DB 사용 권장)
kakao_tokens = {
    "access_token": None,
    "refresh_token": None
}

# 현재 테마 상태 (기본값: mung - 욜로멍)
# mung: 일반 모드 (욜로멍)
# nyang: 다크 모드 (욜로냥)
current_theme = "mung"

@router.get("/login")
async def kakao_login():
    """카카오 로그인 페이지로 리다이렉트"""
    print(f"[카카오] REST API KEY: {KAKAO_REST_API_KEY[:10]}..." if len(KAKAO_REST_API_KEY) > 10 else f"[카카오] REST API KEY: {KAKAO_REST_API_KEY}")
    print(f"[카카오] Redirect URI: {KAKAO_REDIRECT_URI}")
    
    kakao_oauth_url = (
        f"https://kauth.kakao.com/oauth/authorize"
        f"?client_id={KAKAO_REST_API_KEY}"
        f"&redirect_uri={KAKAO_REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=talk_message"
    )
    print(f"[카카오] OAuth URL: {kakao_oauth_url[:80]}...")
    return RedirectResponse(url=kakao_oauth_url)

@router.get("/callback")
async def kakao_callback(code: str = None, error: str = None, error_description: str = None):
    """카카오 OAuth 콜백"""
    # 에러 처리
    if error:
        print(f"[카카오] OAuth 에러: {error} - {error_description}")
        return RedirectResponse(url=f"http://localhost:3000/mypage?kakao_error={error}")
    
    if not code:
        return RedirectResponse(url="http://localhost:3000/mypage?kakao_error=no_code")
    
    token_url = "https://kauth.kakao.com/oauth/token"
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            token_url,
            data={
                "grant_type": "authorization_code",
                "client_id": KAKAO_REST_API_KEY,
                "redirect_uri": KAKAO_REDIRECT_URI,
                "code": code
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
    
    if response.status_code != 200:
        print(f"[카카오] 토큰 발급 실패: {response.text}")
        return RedirectResponse(url="http://localhost:3000/mypage?kakao_error=token_failed")
    
    tokens = response.json()
    kakao_tokens["access_token"] = tokens.get("access_token")
    kakao_tokens["refresh_token"] = tokens.get("refresh_token")
    
    print(f"[카카오] 토큰 발급 성공!")
    return RedirectResponse(url="http://localhost:3000/mypage?kakao_success=true")

@router.post("/send-message")
async def send_kakao_message(message: str = "배회자가 감지되었습니다!"):
    """카카오톡 나에게 메시지 보내기"""
    if not kakao_tokens["access_token"]:
        raise HTTPException(status_code=401, detail="카카오 로그인이 필요합니다. /kakao/login 으로 먼저 로그인하세요.")
    
    message_url = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
    
    # 테마에 따른 메시지 헤더 설정
    if current_theme == "nyang":
        header = "[욜로냥 긴급냥!!]"
    else:
        header = "[욜로멍 긴급멍!!]"

    template = {
        "object_type": "text",
        "text": f"{header}\n\n{message}",
        "link": {
            "web_url": "http://localhost:3000",
            "mobile_web_url": "http://localhost:3000"
        },
        "button_title": "확인하기"
    }
    
    # [학습 포인트: 비동기 HTTP 요청]
    # - `httpx`는 `requests`와 비슷하지만 `async/await`를 지원합니다.
    # - FastAPI 같은 비동기 프레임워크에서는 `requests` 대신 `httpx`를 써야 서버가 멈추지 않습니다.
    # - `async with`를 쓰면 클라이언트를 자동으로 닫아주어 자원 누수를 막습니다.
    async with httpx.AsyncClient() as client:
        response = await client.post(
            message_url,
            data={"template_object": str(template).replace("'", '"')},
            headers={
                "Authorization": f"Bearer {kakao_tokens['access_token']}",
                "Content-Type": "application/x-www-form-urlencoded"
            }
        )
    
    if response.status_code != 200:
        print(f"[카카오] 메시지 전송 실패: {response.text}")
        raise HTTPException(status_code=400, detail=f"메시지 전송 실패: {response.text}")
    
    print(f"[카카오] 메시지 전송 성공!")
    return {"message": "카카오톡 메시지 전송 성공!"}

@router.get("/status")
async def kakao_status():
    """카카오 연동 상태 확인"""
    return {
        "connected": kakao_tokens["access_token"] is not None,
        "message": "카카오 연동됨" if kakao_tokens["access_token"] else "카카오 로그인 필요",
        "theme": current_theme
    }

@router.post("/logout")
async def kakao_logout():
    """
    카카오 연동 해제 (로그아웃)
    
    [학습 포인트: 로그아웃 구현 방식]
    1. 간단한 방식: 서버에 저장된 토큰을 삭제하면 "연동 안됨" 상태가 됩니다.
    2. 완전한 방식: 카카오 서버에 로그아웃 API를 호출하여 토큰을 무효화합니다.
       - 카카오 로그아웃 API: https://kapi.kakao.com/v1/user/logout
       - 이 방식은 카카오 개발자 센터에 Logout Redirect URI 등록이 필요합니다.
    
    여기서는 간단한 방식(토큰 삭제)을 사용합니다.
    """
    global kakao_tokens
    
    # 토큰이 있으면 카카오 서버에도 로그아웃 요청 (선택)
    if kakao_tokens["access_token"]:
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    "https://kapi.kakao.com/v1/user/logout",
                    headers={"Authorization": f"Bearer {kakao_tokens['access_token']}"}
                )
            print("[카카오] 카카오 서버 로그아웃 완료")
        except Exception as e:
            print(f"[카카오] 카카오 서버 로그아웃 실패 (무시): {e}")
    
    # 로컬 토큰 삭제
    kakao_tokens["access_token"] = None
    kakao_tokens["refresh_token"] = None
    
    print("[카카오] 로그아웃 완료 - 토큰 삭제됨")
    return {"message": "카카오 로그아웃 완료", "connected": False}

@router.post("/theme")
async def set_theme(theme: str = Query(..., description="테마 설정 (mung 또는 nyang)")):
    """프론트엔드 테마 설정 (mung: 일반/욜로멍, nyang: 다크/욜로냥)"""
    global current_theme
    if theme not in ["mung", "nyang"]:
        raise HTTPException(status_code=400, detail="유효하지 않은 테마입니다. (mung 또는 nyang)")
    
    current_theme = theme
    print(f"[Kakao] 테마 변경됨: {current_theme} ({'욜로냥' if theme == 'nyang' else '욜로멍'})")
    return {"message": "테마 설정 완료", "current_theme": current_theme}

# 배회자 감지 시 호출할 함수
async def notify_loitering(track_id: int, elapsed_time: float):
    """배회자 감지 시 카카오톡 알림 전송"""
    if not kakao_tokens["access_token"]:
        print("[카카오] 토큰 없음 - 알림 생략")
        return False
    
    message = f"ID: {track_id}\n체류시간: {elapsed_time:.1f}초\n\n즉시 확인이 필요합니다."
    
    try:
        await send_kakao_message(message)
        return True
    except Exception as e:
        print(f"[카카오] 알림 전송 실패: {e}")
        return False

# 화재/연기 감지 시 호출할 함수
async def notify_hazard(label: str, score: float, elapsed_time: float):
    """
    화재/연기 감지 시 카카오톡 알림 전송 (학습용 주석 포함)
    
    Args:
        label (str): 감지된 클래스 이름 ('fire' 또는 'smoke')
        score (float): 신뢰도 점수 (0.0 ~ 1.0)
        elapsed_time (float): 지속된 시간 (초)
    """
    # 1. 토큰 체크: 카카오 로그인이 안 되어있으면 알림을 못 보냄
    if not kakao_tokens["access_token"]:
        print("[카카오] 토큰 없음 - 알림 생략")
        return False
    
    # 2. 메시지 구성
    # - 사용자에게 보여줄 친절한 메시지를 만듭니다.
    hazard_type = "화재(Fire)" if label == "fire" else "연기(Smoke)"
    message = f"[위험] {hazard_type} 감지!\n신뢰도: {score*100:.1f}%\n지속시간: {elapsed_time:.1f}초\n\n즉시 확인이 필요합니다!"
    
    # 3. 비동기 전송 시도
    # - `try-except`로 감싸서 알림 전송이 실패해도 서버가 죽지 않게 합니다.
    try:
        await send_kakao_message(message)
        return True
    except Exception as e:
        print(f"[카카오] 위험 알림 전송 실패: {e}")
        return False
