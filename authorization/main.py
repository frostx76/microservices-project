from fastapi import FastAPI, Depends, HTTPException, status, Form, Header
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlmodel import select, Session
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
import os
from typing import Optional
from models.authorization import User
from database.db import get_session, wait_for_db
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Authorization service",
    description="API for user authentication and authorization",
    version="1.0.0",
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


@app.on_event("startup")
async def startup_event():
    logger.info("Starting auth service...")
    wait_for_db()
    logger.info("Service ready")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_user_by_email(session: Session, email: str) -> Optional[User]:
    result = session.exec(select(User).where(User.email == email))
    return result.first()


async def authenticate_user(session: Session, email: str, password: str) -> Optional[User]:
    user = await get_user_by_email(session, email)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user


@app.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
        email: str,
        password: str,
        session: Session = Depends(get_session)
):
    existing_user = await get_user_by_email(session, email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    hashed_password = get_password_hash(password)
    user = User(
        email=email,
        hashed_password=hashed_password,
        is_active=True
    )

    session.add(user)
    session.commit()
    session.refresh(user)

    logger.info(f"New user registered: {user.email}")
    return {"email": user.email, "is_active": user.is_active}


@app.post("/token")
async def login_for_access_token(
        email: str = Form(...),
        password: str = Form(...),
        session: Session = Depends(get_session)
):
    user = await authenticate_user(session, email, password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/verify")
async def verify_token(token: str = Header(..., alias="Authorization")):
    try:
        token = token.replace("Bearer ", "").strip()
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return {"email": payload.get("sub")}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
