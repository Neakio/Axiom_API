# ------------------------------ PACKAGES ------------------------------
# Standard imports
from datetime import datetime, timedelta
from dotenv import load_dotenv
from os import getenv
from pydantic import BaseModel
from typing import Union
import re

# Third-party libraries
from botocore.exceptions import NoCredentialsError, PartialCredentialsError
from fastapi import HTTPException, Depends, status, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
import boto3
import jwt

# Local imports
import functions.utils as utils
from src.app import app

# Database
import postgres.crud as crud
from postgres.database import get_db


# ------------------------------ GENERAL ------------------------------
# Load environment variables
load_dotenv()
SECRET_KEY = getenv("SECRET_KEY")
ALGORITHM = getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = 1400


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Union[str, None] = None


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")


# ------------------------------ TOKEN ------------------------------
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now() + expires_delta
    else:
        expire = datetime.now() + timedelta(days=90)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# Functions to check admin token
def check_token(token: str = Depends(oauth2_scheme)):
    stored_token = get_secret()
    if token != stored_token:
        utils.api_log("ADMIN TOKEN ERROR, invalid token provided\n\n")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return


def get_secret():
    secret_name = getenv("SECRET_NAME")
    region_name = getenv("REGION_NAME")
    session = boto3.session.Session()
    client = session.client(service_name="secretsmanager", region_name=region_name)
    try:
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
    except (NoCredentialsError, PartialCredentialsError):
        utils.api_log("AWS token not found")
        raise Exception("TOKEN ERROR, AWS credentials not found\n\n")
    except Exception as e:
        utils.api_log(f"TOKEN ERROR, error in retrieving secret : {e}")
        raise Exception(f"Error retrieving secret: {e}")
    utils.api_log("Token successfully retrieved from AWS")
    secret = get_secret_value_response["SecretString"]
    return secret


# ------------------------------ USER ------------------------------
async def get_user(db: Session, email: str):
    return await crud.get_user_by_email(db, email)


async def get_current_user(
    db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    token_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="This token does not have the right to perform scans",
        headers={"WWW-Authenticate": "Bearer"},
    )
    stored_token = get_secret()
    if token == stored_token:
        raise token_exception
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    email: str = payload.get("sub")
    if email is None:
        utils.api_log("AUTH ERROR, invalid credentials\n\n")
        raise credentials_exception
    token_data = TokenData(email=email)
    user = await get_user(db, email=token_data.email)
    if user is None:
        utils.api_log("AUTH ERROR, wrong admin token usage\n\n")
        raise credentials_exception
    return user


async def authenticate_user(db: Session, email: str, password: str):
    user = await crud.get_user_by_email(db, email)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user


################################### [ API ] ##################################
# ------------------------------ Authentication ------------------------------


@app.post("/token")
async def login_for_access_token(
    db: AsyncSession = Depends(get_db), form_data: OAuth2PasswordRequestForm = Depends()
) -> Token:
    utils.api_log("Attempting Token Request")
    email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(email_regex, form_data.username):
        utils.api_log("AUTH ERROR, invalid email provided\n\n")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Please enter a valid email",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        utils.api_log("AUTH ERROR, invalid credentials\n\n")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    utils.api_log(f"Token Request succesful for user {user.email}\n\n")
    return Token(access_token=access_token, token_type="bearer")


# ------------------------------ MONITORING ------------------------------
@app.middleware("http")
async def log_requests(request: Request, call_next):
    # Log request details
    client_ip = request.client.host
    url = str(request.url)
    method = request.method
    headers = dict(request.headers)

    utils.api_log(
        f"MONITORING - IP: {client_ip}, URL: {url}, Method: {method}, Headers: {headers}"
    )
    response = await call_next(request)

    return response
