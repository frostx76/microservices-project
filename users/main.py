import httpx
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from sqlmodel import select, Session
from typing import List, Optional
from datetime import date
from .. modul.models.users import User
from .. modul.db import get_session, wait_for_db
from authorization.main import get_current_user as get_auth_user
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="User management service",
    description="API for managing user profiles",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

FILMS_SERVICE_URL = "http://films:8000"
REVIEWS_SERVICE_URL = "http://reviews:8002"


@app.on_event("startup")
async def startup_event():
    logger.info("Starting application...")
    wait_for_db()
    logger.info("Application startup complete")


@app.post("/users",
          response_model=User,
          status_code=status.HTTP_201_CREATED,
          summary="Create a new user",
          response_description="The created user")
async def create_user(user: User, session: Session = Depends(get_session)):
    """
    Создание пользователя с информацией
    """
    try:
        existing_user = session.exec(
            select(User).where(User.email == user.email)
        ).first()

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )

        session.add(user)
        session.commit()
        session.refresh(user)

        logger.info(f"Created new user with ID: {user.id}")
        return user

    except Exception as e:
        logger.error(f"Error creating user: {str(e)}")
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user"
        )


@app.get("/users/{user_id}",
         response_model=User,
         summary="Get user by ID",
         responses={
             404: {"description": "User not found"}
         })
async def get_user(user_id: int, session: Session = Depends(get_session)):
    """Получить 1 пользователя по ID"""
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


@app.get("/users",
         response_model=List[User],
         summary="List all users")
async def list_users(
        skip: int = 0,
        limit: int = 100,
        is_active: Optional[bool] = None,
        session: Session = Depends(get_session)
):
    """
    Получение список пользователей по фильтру
    """
    query = select(User)

    if is_active is not None:
        query = query.where(User.is_active == is_active)

    users = session.exec(
        query.offset(skip).limit(limit)
    ).all()

    return users


@app.patch("/users/{user_id}",
           response_model=User,
           summary="Update user partially",
           responses={
               404: {"description": "User not found"}
           })
async def update_user_partially(
        user_id: int,
        updated_data: User,
        session: Session = Depends(get_session),
        auth_user=Depends(get_auth_user)
):
    """
    Обновление информацию о пользователе

    Поддерживает все опциональные поля о себе
    """
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    user_data = updated_data.dict(exclude_unset=True)
    for key, value in user_data.items():
        setattr(user, key, value)

    session.add(user)
    session.commit()
    session.refresh(user)

    return user


@app.delete("/users/{user_id}",
            status_code=status.HTTP_204_NO_CONTENT,
            summary="Delete a user",
            responses={
                404: {"description": "User not found"}
            })
async def delete_user(
        user_id: int,
        session: Session = Depends(get_session),
        auth_user=Depends(get_auth_user)
):
    """Удаление пользователя по ID"""
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    session.delete(user)
    session.commit()

    return None


@app.get("/users/{user_id}/reviews", summary="Get user reviews")
async def get_user_reviews(
        user_id: int,
        session: Session = Depends(get_session)
):
    """Получение всех отзывов пользователя"""
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{REVIEWS_SERVICE_URL}/reviews?user_id={user_id}")
        if response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get user reviews"
            )
        return response.json()
