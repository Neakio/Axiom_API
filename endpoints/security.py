# ------------------------------ PACKAGES ------------------------------
# Standard imports
from dotenv import load_dotenv

from fastapi import Request

# Local imports
import functions.utils as utils
from src.app import app


# ------------------------------ GENERAL ------------------------------
# Load environment variables
load_dotenv()


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
