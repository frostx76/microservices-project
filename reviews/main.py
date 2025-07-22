from fastapi import FastAPI, Depends, HTTPException, status
from sqlmodel import select, Session
from typing import List, Optional
from models.reviews import Review
from database.db import get_session, wait_for_db
import httpx
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
async def create_review(
        review: Review,
        token: str,
        session: Session = Depends(get_session)
):
    async with httpx.AsyncClient() as client:
        r = await client.post("http://auth-service:8001/verify", json={"token": token})
    if r.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid token")

    film_resp = await client.get(f"http://films-service:8000/films/{review.film_id}")
    if film_resp.status_code != 200:
        raise HTTPException(status_code=404, detail="Film not found")

    user_resp = await client.get(f"http://users-service:8003/users/{review.user_id}")
    if user_resp.status_code != 200:
        raise HTTPException(status_code=404, detail="User not found")

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
def get_reviews(
        film_id: Optional[int] = None,
        session: Session = Depends(get_session)
):
    query = select(Review)
    if film_id:
        query = query.where(Review.film_id == film_id)
    return session.exec(query).all()


@app.get("/reviews/{review_id}", response_model=Review)
def get_review(review_id: int, session: Session = Depends(get_session)):
    review = session.get(Review, review_id)
    if not review:
        raise HTTPException(404, detail="Review not found")
    return review


@app.delete("/reviews/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_review(
        review_id: int,
        token: str,
        session: Session = Depends(get_session)
):
    async with httpx.AsyncClient() as client:
        r = await client.post("http://auth-service:8001/verify", json={"token": token})
    if r.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid token")

    review = session.get(Review, review_id)
    if not review:
        raise HTTPException(404, detail="Review not found")
    session.delete(review)
    session.commit()
