from fastapi import FastAPI, Depends, HTTPException, status
from sqlmodel import select, Session
from typing import List, Optional
from models.users import User
from database.db import wait_for_db, get_session
import httpx
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="User management service",
    description="API for managing user profiles",
    version="1.0.0"
)


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
async def create_user(
        user: User,
        token: str,
        session: Session = Depends(get_session)
):
    async with httpx.AsyncClient() as client:
        r = await client.post("http://auth-service:8000/verify", json={"token": token})
    if r.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid token")

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
        token: str,
        session: Session = Depends(get_session)
):
    async with httpx.AsyncClient() as client:
        r = await client.post("http://auth-service:8000/verify", json={"token": token})
    if r.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid token")

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
        token: str,
        session: Session = Depends(get_session)
):
    async with httpx.AsyncClient() as client:
        r = await client.post("http://auth-service:8000/verify", json={"token": token})
    if r.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = session.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    session.delete(user)
    session.commit()

    return None
