from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlmodel import select, Session
from typing import List
from models.films import Film
from database.db import get_session, wait_for_db
import httpx
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Films service",
    description="API for managing films list",
    version="1.0.0"
)

@app.on_event("startup")
async def startup_event():
    logger.info("Launching the movie service...")
    wait_for_db()
    logger.info("The service is ready to work")

@app.post("/films",
          response_model=Film,
          status_code=status.HTTP_201_CREATED,
          summary="Add a new movie",
          response_description="The data of the created movie")
async def create_film(
    film: Film,
    token: str,
    session: Session = Depends(get_session)
):
    async with httpx.AsyncClient() as client:
        r = await client.post("http://auth-service:8000/verify", json={"token": token})
    if r.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid token")

    try:
        session.add(film)
        session.commit()
        session.refresh(film)
        logger.info(f"A new movie has been added: ID {film.id}, {film.title}")
        return film
    except Exception as e:
        session.rollback()
        logger.error(f"Error when adding a movie: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Couldn't add a movie"
        )

@app.get("/films",
         response_model=List[Film],
         summary="Get a list of all movies")
async def read_films(session: Session = Depends(get_session)):
    films = session.exec(select(Film)).all()
    logger.info(f"A list of films was requested, {len(films)} entries were found")
    return films

@app.get("/films/{film_id}",
         response_model=Film,
         summary="Get a movie by ID",
         responses={
             404: {"description": "The movie was not found"}
         })
async def read_film(film_id: int, session: Session = Depends(get_session)):
    film = session.get(Film, film_id)
    if not film:
        logger.warning(f"A non-existent movie ID was requested {film_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The movie was not found"
        )
    logger.info(f"Movie ID requested{film_id}: {film.title}")
    return film

@app.put("/films/{film_id}",
         response_model=Film,
         summary="Update movie data",
         responses={
             404: {"description": "The movie was not found"}
         })
async def update_film(
        film_id: int,
        film_data: Film,
        token: str,
        session: Session = Depends(get_session)
):
    async with httpx.AsyncClient() as client:
        r = await client.post("http://auth-service:8000/verify", json={"token": token})
    if r.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid token")

    film = session.get(Film, film_id)
    if not film:
        logger.warning(f"Attempt to update a non-existent movie ID {film_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The movie was not found"
        )

    update_data = film_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(film, field, value)

    session.add(film)
    session.commit()
    session.refresh(film)

    logger.info(f"Updated movie ID {film_id}: {film.title}")
    return film

@app.delete("/films/{film_id}",
            status_code=status.HTTP_204_NO_CONTENT,
            summary="Delete a movie",
            responses={
                404: {"description": "The movie was not found"},
                200: {"description": "The movie was deleted successfully"}
            })
async def delete_film(
        film_id: int,
        token: str,
        session: Session = Depends(get_session)
):
    async with httpx.AsyncClient() as client:
        r = await client.post("http://auth-service:8000/verify", json={"token": token})
    if r.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid token")

    film = session.get(Film, film_id)
    if not film:
        logger.warning(f"Attempt to delete a non-existent movie ID {film_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The movie was not found"
        )

    session.delete(film)
    session.commit()

    logger.info(f"Deleted movie ID {film_id}: {film.title}")
    return JSONResponse(
        content={"detail": "The movie was deleted successfully"},
        status_code=status.HTTP_200_OK
    )