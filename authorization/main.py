from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import select, Session
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
import os
from typing import Optional
from .. modul.models.authorization import User
from .. modul.db import get_session, wait_for_db
import logging
import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Authorization service",
    description="API for user authentication and authorization",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

USERS_SERVICE_URL = "http://users:8003"

@app.on_event("startup")
async def startup_event():
    logger.info("Starting auth service...")
    wait_for_db()
    logger.info("Service ready")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверка соответствия пароля и хеша"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Генерация хеша пароля"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Создание JWT токена"""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_user_by_email(session: Session, email: str) -> Optional[User]:
    """Поиск пользователя по email"""
    result = session.exec(select(User).where(User.email == email))
    return result.first()

async def authenticate_user(session: Session, email: str, password: str) -> Optional[User]:
    """Аутентификация пользователя"""
    user = await get_user_by_email(session, email)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user

@app.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
        email: str = Query(..., description="User email"),
        password: str = Query(..., description="User password"),
        full_name: Optional[str] = Query(None, description="User full name"),
        session: Session = Depends(get_session)
):
    """Регистрация нового пользователя"""
    existing_user = await get_user_by_email(session, email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    hashed_password = get_password_hash(password)
    auth_user = User(
        email=email,
        hashed_password=hashed_password,
        is_active=True
    )

    session.add(auth_user)
    session.commit()
    session.refresh(auth_user)

    async with httpx.AsyncClient() as client:
        user_profile = {
            "email": email,
            "full_name": full_name,
            "is_active": True
        }
        response = await client.post(
            f"{USERS_SERVICE_URL}/users",
            json=user_profile
        )
        if response.status_code != 201:
            session.delete(auth_user)
            session.commit()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user profile"
            )

    logger.info(f"New user registered: {auth_user.email}")
    return {"email": auth_user.email, "is_active": auth_user.is_active}

@app.post("/token")
async def login_for_access_token(
        form_data: OAuth2PasswordRequestForm = Depends(),
        session: Session = Depends(get_session)
):
    """Получение JWT токена для аутентификации"""
    user = await authenticate_user(session, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

async def get_current_user(
        token: str = Depends(oauth2_scheme),
        session: Session = Depends(get_session)
) -> User:
    """Получение текущего пользователя по JWT токену"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = await get_user_by_email(session, email)
    if user is None:
        raise credentials_exception
    return user

@app.get("/users/me")
async def read_users_me(current_user: User = Depends(get_current_user)):
    """Получение информации о текущем пользователе"""
    return {"email": current_user.email, "is_active": current_user.is_active}