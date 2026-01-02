from fastapi import APIRouter, Request, HTTPException
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

@router.get("/login")
async def kakao_login():
    """카카오 로그인 페이지로 리다이렉트"""
    kakao_oauth_url = (
        f"https://kauth.kakao.com/oauth/authorize"
        f"?client_id={KAKAO_REST_API_KEY}"
        f"&redirect_uri={KAKAO_REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=talk_message"
    )
    return RedirectResponse(url=kakao_oauth_url)

@router.get("/callback")
async def kakao_callback(code: str):
    """카카오 OAuth 콜백"""
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
        raise HTTPException(status_code=400, detail="토큰 발급 실패")
    
    tokens = response.json()
    kakao_tokens["access_token"] = tokens.get("access_token")
    kakao_tokens["refresh_token"] = tokens.get("refresh_token")
    
    print(f"[카카오] 토큰 발급 성공!")
    return {"message": "카카오 로그인 성공!", "access_token": kakao_tokens["access_token"][:20] + "..."}

@router.post("/send-message")
async def send_kakao_message(message: str = "배회자가 감지되었습니다!"):
    """카카오톡 나에게 메시지 보내기"""
    if not kakao_tokens["access_token"]:
        raise HTTPException(status_code=401, detail="카카오 로그인이 필요합니다. /kakao/login 으로 먼저 로그인하세요.")
    
    message_url = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
    
    template = {
        "object_type": "text",
        "text": f"[배회자 감지 알림]\n\n{message}",
        "link": {
            "web_url": "http://localhost:3000",
            "mobile_web_url": "http://localhost:3000"
        },
        "button_title": "확인하기"
    }
    
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
        "message": "카카오 연동됨" if kakao_tokens["access_token"] else "카카오 로그인 필요"
    }

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
