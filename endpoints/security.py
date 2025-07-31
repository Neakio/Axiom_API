# ------------------------------ PACKAGES ------------------------------
# Standard imports
from dotenv import load_dotenv
from os import getenv

# Third-party libraries
from botocore.exceptions import NoCredentialsError, PartialCredentialsError
from fastapi import HTTPException, status, Request, Header
import boto3

# Local imports
import functions.utils as utils
from src.app import app


# ------------------------------ GENERAL ------------------------------
# Load environment variables
load_dotenv()

# ------------------------------ TOKEN ------------------------------
# Functions to check admin token
def check_token(authorization: str = Header(...)):
    token = authorization.removeprefix("Bearer ").strip()
    stored_token = get_secret()  # Tu récupères ici ton token depuis Secrets Manager
    if token != stored_token:
        utils.api_log("ADMIN TOKEN ERROR: invalid token provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


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
