from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.schemas import UserCreate

router = APIRouter()

@router.post("/signup")
def signup(user: UserCreate, db: Session = Depends(get_db)):
    # 1. Check if email already exists
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="이미 등록된 이메일입니다.")

    # 2. Create new user
    # Note: In production, password must be hashed!
    new_user = User(email=user.email, password=user.password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"message": "회원가입 성공", "email": new_user.email}

@router.post("/login")
def login(user: UserCreate, db: Session = Depends(get_db)):
    # 1. Find user in DB
    db_user = db.query(User).filter(User.email == user.email).first()

    # 2. Check password
    if not db_user or db_user.password != user.password:
        raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 잘못되었습니다.")

    return {"message": "로그인 성공", "token": "fake-jwt-token"}
