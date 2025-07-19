from fastapi import FastAPI, Depends
from models.films import Film
from database.db import get_session, wait_for_db
from sqlmodel import select

app = FastAPI()

@app.on_event("startup")
def startup():
    wait_for_db()

@app.post("/films")
def add_film(film: Film, session=Depends(get_session)):
    session.add(film)
    session.commit()
    return film

@app.get("/films")
def list_films(session=Depends(get_session)):
    films = session.exec(select(Film)).all()
    return films