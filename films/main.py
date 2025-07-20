from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlmodel import select, Session
from typing import List
from models.films import Film
from database.db import get_session, wait_for_db
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Фильмотека API",
    description="API для управления базой данных фильмов",
    version="1.0.0"
)


@app.on_event("startup")
async def startup_event():
    logger.info("Запуск сервиса фильмов...")
    wait_for_db()
    logger.info("Сервис готов к работе")


@app.post("/films",
          response_model=Film,
          status_code=status.HTTP_201_CREATED,
          summary="Добавить новый фильм",
          response_description="Данные созданного фильма")
async def create_film(film: Film, session: Session = Depends(get_session)):
    """
    Добавляет фильм в DB

    Параметры:
     - title: название фильма (обязательно)
     - director: режиссер (обязательно)
     - year: год выпуска (year > 1900)
     - rating: рейтинг (0 > rating > 10)
    """
    try:
        session.add(film)
        session.commit()
        session.refresh(film)
        logger.info(f"Добавлен новый фильм: ID {film.id}, {film.title}")
        return film
    except Exception as e:
        session.rollback()
        logger.error(f"Ошибка при добавлении фильма: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Не удалось добавить фильм"
        )


@app.get("/films",
         response_model=List[Film],
         summary="Получить список всех фильмов")
async def read_films(session: Session = Depends(get_session)):
    """
    Возвращает все фильмы в DB
    """
    films = session.exec(select(Film)).all()
    logger.info(f"Запрошен список фильмов, найдено {len(films)} записей")
    return films


@app.get("/films/{film_id}",
         response_model=Film,
         summary="Получить фильм по ID",
         responses={
             404: {"description": "Фильм не найден"}
         })
async def read_film(film_id: int, session: Session = Depends(get_session)):
    """
    Возвращает данные о фильме по ID

    Параметры:
     - film_id: ID фильма (обязательно)
    """
    film = session.get(Film, film_id)
    if not film:
        logger.warning(f"Запрошен несуществующий фильм ID {film_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Фильм не найден"
        )
    logger.info(f"Запрошен фильм ID {film_id}: {film.title}")
    return film


@app.put("/films/{film_id}",
         response_model=Film,
         summary="Обновить данные фильма",
         responses={
             404: {"description": "Фильм не найден"}
         })
async def update_film(
        film_id: int,
        film_data: Film,
        session: Session = Depends(get_session)
):
    """
    Обновляет информацию о фильме

    Параметры:
     - film_id: ID фильма (обязательно)
     - film_data: новая информация
    """
    film = session.get(Film, film_id)
    if not film:
        logger.warning(f"Попытка обновить несуществующий фильм ID {film_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Фильм не найден"
        )

    update_data = film_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(film, field, value)

    session.add(film)
    session.commit()
    session.refresh(film)

    logger.info(f"Обновлен фильм ID {film_id}: {film.title}")
    return film


@app.delete("/films/{film_id}",
            status_code=status.HTTP_204_NO_CONTENT,
            summary="Удалить фильм",
            responses={
                404: {"description": "Фильм не найден"},
                200: {"description": "Фильм успешно удален"}
            })
async def delete_film(film_id: int, session: Session = Depends(get_session)):
    """
    Удаляет фильм

    Параметры:
     - film_id: ID фильма (обязательно)
    """
    film = session.get(Film, film_id)
    if not film:
        logger.warning(f"Попытка удалить несуществующий фильм ID {film_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Фильм не найден"
        )

    session.delete(film)
    session.commit()

    logger.info(f"Удален фильм ID {film_id}: {film.title}")
    return JSONResponse(
        content={"detail": "Фильм успешно удален"},
        status_code=status.HTTP_200_OK
    )