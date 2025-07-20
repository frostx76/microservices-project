from fastapi import FastAPI, Depends, HTTPException, status
from sqlmodel import select, Session
from typing import List
from models.reviews import Review
from database.db import get_session, wait_for_db
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Review service",
    description="API for film reviews",
    version="1.0.0"
)

@app.on_event("startup")
def startup():
    wait_for_db()
    logger.info("Review service started")

@app.post("/reviews", status_code=status.HTTP_201_CREATED)
def create_review(review: Review, session: Session = Depends(get_session)):
    """Добавить отзыв"""
    try:
        session.add(review)
        session.commit()
        session.refresh(review)
        return review
    except Exception as e:
        session.rollback()
        logger.error(f"Error creating review: {e}")
        raise HTTPException(400, detail="Invalid review data")

@app.get("/reviews", response_model=List[Review])
def get_reviews(film_id: int = None, session: Session = Depends(get_session)):
    """Получить все отзывы"""
    query = select(Review)
    if film_id:
        query = query.where(Review.film_id == film_id)
    return session.exec(query).all()

@app.get("/reviews/{review_id}", response_model=Review)
def get_review(review_id: int, session: Session = Depends(get_session)):
    """Получить отзыв по ID"""
    review = session.get(Review, review_id)
    if not review:
        raise HTTPException(404, detail="Review not found")
    return review

@app.delete("/reviews/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_review(review_id: int, session: Session = Depends(get_session)):
    """Удалить отзыв"""
    review = session.get(Review, review_id)
    if not review:
        raise HTTPException(404, detail="Review not found")
    session.delete(review)
    session.commit()