from fastapi import FastAPI, Depends, HTTPException, status
from sqlmodel import select
from models.auth import User
from database.db import get_session, wait_for_db
from sqlalchemy.exc import IntegrityError
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import jwt
from datetime import datetime, timedelta
import os

app = FastAPI()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

@app.on_event("startup")
def on_startup():
    wait_for_db()

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta if expires_delta else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_user_by_email(session, email: str):
    statement = select(User).where(User.email == email)
    user = session.exec(statement).first()
    return user

@app.post("/register")
def register(user: User, session=Depends(get_session)):
    user_in_db = get_user_by_email(session, user.email)
    if user_in_db:
        raise HTTPException(status_code=400, detail="Email already registered")
    user.hashed_password = get_password_hash(user.hashed_password)
    session.add(user)
    try:
        session.commit()
        session.refresh(user)
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=400, detail="Error creating user")
    return {"msg": "User registered successfully", "user_id": user.id}

@app.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends(), session=Depends(get_session)):
    user = get_user_by_email(session, form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/me")
def read_users_me(token: str = Depends(oauth2_scheme), session=Depends(get_session)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")

    user = get_user_by_email(session, email)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return {"email": user.email, "is_active": user.is_active}
