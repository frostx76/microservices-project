from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from sqlmodel import select, Session
from typing import List, Optional
from datetime import datetime
from .. modul.models.reviews import Review
from .. modul.db import get_session, wait_for_db
from authorization.main import get_current_user as get_auth_user
import logging
import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Review service",
    description="API for film reviews",
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
USERS_SERVICE_URL = "http://users:8003"


@app.on_event("startup")
def startup():
    wait_for_db()
    logger.info("Review service started")


@app.post("/reviews", status_code=status.HTTP_201_CREATED)
async def create_review(  # Добавлен async перед def
        review: Review,
        session: Session = Depends(get_session),
        auth_user=Depends(get_auth_user)
):
    """Добавление отзыва"""
    try:
        # Проверка существования фильма
        async with httpx.AsyncClient() as client:
            film_response = await client.get(f"{FILMS_SERVICE_URL}/films/{review.film_id}")
            if film_response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Film not found"
                )

            # Проверка существования пользователя
            user_response = await client.get(f"{USERS_SERVICE_URL}/users/{review.user_id}")
            if user_response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User not found"
                )

        # Если проверки прошли, сохраняем отзыв
        session.add(review)
        await session.commit()  # Для async сессии
        await session.refresh(review)
        return review

    except HTTPException:
        raise  # Пробрасываем уже созданные HTTPException
    except Exception as e:
        await session.rollback()  # Для async сессии
        logger.error(f"Error creating review: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create review"
        )


@app.get("/reviews", response_model=List[Review])
def get_reviews(
        film_id: Optional[int] = None,
        user_id: Optional[int] = None,
        session: Session = Depends(get_session)
):
    """Получение всех отзывов"""
    query = select(Review)
    if film_id:
        query = query.where(Review.film_id == film_id)
    if user_id:
        query = query.where(Review.user_id == user_id)
    return session.exec(query).all()


@app.get("/reviews/{review_id}", response_model=Review)
def get_review(
        review_id: int,
        session: Session = Depends(get_session)
):
    """Получение отзыва по ID"""
    review = session.get(Review, review_id)
    if not review:
        raise HTTPException(404, detail="Review not found")
    return review


@app.delete("/reviews/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_review(
        review_id: int,
        session: Session = Depends(get_session),
        auth_user=Depends(get_auth_user)
):
    """Удаление отзыва"""
    review = session.get(Review, review_id)
    if not review:
        raise HTTPException(404, detail="Review not found")
    session.delete(review)
    session.commit()


@app.patch("/reviews/{review_id}/approve", response_model=Review)
def approve_review(
        review_id: int,
        session: Session = Depends(get_session),
        auth_user=Depends(get_auth_user)
):
    """Одобрение отзыва модератором"""
    review = session.get(Review, review_id)
    if not review:
        raise HTTPException(404, detail="Review not found")

    review.is_approved = True
    session.add(review)
    session.commit()
    session.refresh(review)
    return review