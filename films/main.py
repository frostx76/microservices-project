from fastapi import FastAPI, Depends, HTTPException, status
from starlette.responses import JSONResponse

from models.films import Film
from database.db import get_session, wait_for_db
from sqlmodel import select, Session

app = FastAPI()

@app.on_event("startup")
def startup():
    wait_for_db()

@app.post("/films", response_model=Film, status_code=status.HTTP_201_CREATED)
def add_film(film: Film, session: Session = Depends(get_session)):
    session.add(film)
    session.commit()
    session.refresh(film)
    return film

@app.get("/films", response_model=list[Film])
def list_films(session: Session = Depends(get_session)):
    films = session.exec(select(Film)).all()
    return films

@app.get("/films/{film_id}", response_model=Film)
def get_film(film_id: int, session: Session = Depends(get_session)):
    film = session.get(Film, film_id)
    if not film:
        raise HTTPException(status_code=404, detail="Film not found")
    return film

@app.put("/films/{film_id}", response_model=Film)
def update_film(film_id: int, film_data: Film, session: Session = Depends(get_session)):
    film = session.get(Film, film_id)
    if not film:
        raise HTTPException(status_code=404, detail="Film not found")
    film.title = film_data.title
    film.director = film_data.director
    film.year = film_data.year
    film.rating = film_data.rating
    session.add(film)
    session.commit()
    session.refresh(film)
    return film

@app.delete("/films/{film_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_film(film_id: int, session: Session = Depends(get_session)):
    film = session.get(Film, film_id)
    if not film:
        raise HTTPException(status_code=404, detail="Film not found")
    session.delete(film)
    session.commit()
    return JSONResponse(content={"detail": "Deleted successfully"}, status_code=200)
