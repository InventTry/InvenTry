#!/usr/bin/env python3

from datetime import date, datetime, timedelta, timezone
import os
from typing import Optional, List, Union
from fastapi import FastAPI, HTTPException, Response, Cookie, Depends
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, EmailStr, ConfigDict
from passlib.context import CryptContext
from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey, CHAR, Date, text
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
import uvicorn
from sqlalchemy.sql.functions import func
from starlette import status
import jwt

# For now credentials from environment variables
DB_PASS = os.getenv("POSTGRES_PASSWORD")
DB_USER = os.getenv("POSTGRES_USER")
DB_HOST = os.getenv("POSTGRES_HOST")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}/inventry"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Permission bit masks:
# 1. Moderator Read 2. Moderator Write 3. User Read 4. User Write
MOD_READ = text("B'1000'")
MOD_WRITE = text("B'0100'")
USR_READ = text("B'0010'")
USR_WRITE = text("B'0001'")

class UserDB(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, server_default="user")
    date_joined = Column(Date, nullable = False, server_default=func.current_date())
    date_left = Column(Date)
    archived = Column(Boolean, nullable = False, server_default=func.false())

class ItemDB(Base):
    __tablename__ = "inventory"
    id = Column(Integer, primary_key=True, index=True)
    display_name = Column(String(50),  nullable=False)
    serial_number = Column(String, unique=True)
    date_created = Column(Date)
    date_updated = Column(Date)
    category_id = Column(Integer, ForeignKey("categories.id"))
    assigned_to = Column(Integer, ForeignKey("users.id"))
    permissions = Column(CHAR(4))
    archived = Column(Boolean)
    date_archived = Column(Date)

class CategoryDB(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)

class Item(BaseModel):
    id: int
    display_name: str
    serial_number: Optional[str] = None
    date_created: date
    date_updated: date
    category_id: int
    assigned_to: Optional[int] = None
    permissions: str
    archived: bool
    date_archived: Optional[date] = None
    model_config = ConfigDict(from_attributes=True)

hash_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str
app = FastAPI()

@app.get("/")
def read_root():
    return HTMLResponse(content="<h1>Hello World!</h1>")
@app.post("/api/register", status_code=status.HTTP_201_CREATED)
def register(user: UserCreate):
    db=SessionLocal() #Connect to db
    try:
        #Check if email taken
        if db.query(UserDB).filter_by(email=user.email).first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered")
        #Hash password
        hashed_password = hash_context.hash(user.password)

        new_user = UserDB(
            email = user.email,
            password_hash = hashed_password,
            last_name = user.last_name,
            first_name = user.first_name
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return {"message": "User created successfully"}
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database operation error {e}")
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    finally:
        db.close()

def create_access_token(user_id: str):
    SECRET_KEY = os.getenv("SECRET_KEY")
    ALGORITHM = os.getenv("ALGORITHM")
    # Token for 1h
    expire = datetime.now(timezone.utc) + timedelta(hours=1)
    to_encode = {"sub": user_id, "exp": expire}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(access_token: str = Cookie(None)):
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )
    try:
        SECRET_KEY = os.getenv("SECRET_KEY")
        ALGORITHM = os.getenv("ALGORITHM")
        # Decode token
        payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")

        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        db = SessionLocal()
        user = db.query(UserDB).filter_by(id=user_id).first()
        return user  # Return user id for further authentification

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.post("/api/login", status_code=status.HTTP_200_OK)
def login(response: Response, user: UserLogin):
    db=SessionLocal()
    try:
        user_in_db = db.query(UserDB).filter_by(email=user.email).first()
        if user_in_db or hash_context.verify(user.password, user_in_db.password_hash):
            access_token = create_access_token(str(user_in_db.id))
            response.set_cookie(
                key="access_token",
                value=access_token,
                httponly=True,
                secure=False,  # FOR PRODUCTION CHANGE TO TRUE FOR HTTPS
                samesite="lax",
                max_age=86400
            )
            return {"message": "Logged in successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail= f"Database operation error {e}"
        )
    finally:
        db.close()

@app.get("/api/get_items", response_model=Union[Item, List[Item]])
def read_items(
        id: Optional[str] = None,
        category: Optional[str] = None,
        current_user: UserDB = Depends(get_current_user),
):
    db = SessionLocal()
    try:
        query = db.query(ItemDB)
        if current_user.role == "admin":
            pass
        elif current_user.role == "moderator":
            query = query.filter(ItemDB.permissions.op('&')(MOD_READ) != text("B'0000'"))
        elif current_user.role == "user":
            query = query.filter(ItemDB.permissions.op('&')(USR_READ) != text("B'0000'"))
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User corrupted, contact administrator"
            )
        if category == "all":
            pass
        elif id and not category:
            query = query.filter_by(id=id).first()
        elif category and not id:
            category_db = db.query(CategoryDB).filter_by(name = category).first()
            query = query.filter_by(category_id=category_db.id).all()
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bad Request"
            )
        return query

    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail= f"Database operation error {e}"
        )
    finally:
        db.close()


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)