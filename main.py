# ------------------------------ PACKAGES ------------------------------
# Independant packages
from fastapi import FastAPI
import uvicorn
import yaml

# General packages
import logging
from dotenv import load_dotenv
from logging.config import dictConfig


# Internal packages
import endpoints.scans
import endpoints.users
import documentation.doc
import functions.utils as utils
from src.app import app

# Database
from postgres.database import init_db


# ------------------------------ ROUTING ------------------------------
def init_routers(app: FastAPI):
    app.include_router(endpoints.scans.router)
    app.include_router(endpoints.users.router)
    app.include_router(documentation.doc.router)


# ------------------------------ MAIN ------------------------------

if __name__ == "__main__":
    uvicorn.run(
        app, host="0.0.0.0", port=8000, reload=True, log_config="logging_config.yaml"
    )


# ------------------------------ LOG ------------------------------
# Load YAML configuration
with open("logging_config.yaml", "r") as f:
    logging_config = yaml.safe_load(f)

# Apply custom logging configuration
dictConfig(logging_config)

# Ensure SQLAlchemy logs do not propagate to the terminal
sqlalchemy_logger = logging.getLogger("sqlalchemy.engine")
sqlalchemy_logger.propagate = False


# ------------------------------ SERVER LOADING PROCESS ------------------------------
@app.on_event("startup")
async def startup_event():
    utils.api_log("Startup event triggered. -----------------------------")
    utils.update_cases()  # Refresh scan options
    load_dotenv()  # Load environment variables from .env
    await init_db()  # Initialize database
    init_routers(app)  # Initialize the router
    # Load the JSON data
    profiles, formats, workflows = utils.load_json()
    global ValidprofilesEnum, ValidformatsEnum, ValidworkflowsEnum
    ValidprofilesEnum = utils.create_enum("ValidprofilesEnum", profiles)
    ValidformatsEnum = utils.create_enum("ValidformatsEnum", formats)
    ValidworkflowsEnum = utils.create_enum("ValidworkflowsEnum", workflows)
