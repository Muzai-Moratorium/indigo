from fastapi import APIRouter, Depends, HTTPException, Response, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.schemas import UserCreate
import bcrypt
from jose import jwt, JWTError
from datetime import datetime, timedelta

router = APIRouter(prefix="/auth", tags=["auth"])

# JWT 설정
SECRET_KEY = "your-super-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24시간

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(request: Request, db: Session = Depends(get_db)):
    """쿠키에서 JWT 토큰을 가져와 사용자 검증"""
    token = request.cookies.get("access_token")
    
    if not token:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다.")
    except JWTError:
        raise HTTPException(status_code=401, detail="토큰이 만료되었거나 유효하지 않습니다.")
    
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise HTTPException(status_code=401, detail="사용자를 찾을 수 없습니다.")
    
    return user

@router.post("/signup")
def signup(user: UserCreate, db: Session = Depends(get_db)):
    """회원가입"""
    # 1. 이메일 중복 확인
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="이미 등록된 이메일입니다.")

    # 2. 비밀번호 해싱 후 저장
    hashed_password = hash_password(user.password)
    new_user = User(email=user.email, password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"message": "회원가입 성공!", "email": new_user.email}

@router.post("/login")
def login(user: UserCreate, response: Response, db: Session = Depends(get_db)):
    """로그인 - JWT를 HttpOnly 쿠키로 설정"""
    # 1. 사용자 조회
    db_user = db.query(User).filter(User.email == user.email).first()

    # 2. 비밀번호 검증
    if not db_user or not verify_password(user.password, db_user.password):
        raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 잘못되었습니다.")

    # 3. JWT 토큰 생성
    access_token = create_access_token(data={"sub": db_user.email})

    # 4. HttpOnly 쿠키로 설정
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        samesite="lax",
        secure=False  # 개발환경에서는 False, 프로덕션에서는 True
    )

    return {"message": "로그인 성공!", "email": db_user.email}

@router.post("/logout")
def logout(response: Response):
    """로그아웃 - 쿠키 삭제"""
    response.delete_cookie(key="access_token")
    return {"message": "로그아웃 성공!"}

@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    """현재 로그인한 사용자 정보 반환"""
    return {"email": current_user.email, "id": current_user.id}

@router.get("/check")
def check_auth(request: Request, db: Session = Depends(get_db)):
    """로그인 상태 확인 (로그인 안됐으면 에러 대신 상태 반환)"""
    token = request.cookies.get("access_token")
    
    if not token:
        return {"authenticated": False, "user": None}
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            return {"authenticated": False, "user": None}
        
        user = db.query(User).filter(User.email == email).first()
        if user is None:
            return {"authenticated": False, "user": None}
        
        return {"authenticated": True, "user": {"email": user.email, "id": user.id}}
    except JWTError:
        return {"authenticated": False, "user": None}
