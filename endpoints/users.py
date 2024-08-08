# ------------------------------ PACKAGES ------------------------------
# Independant packages
from fastapi import (
    HTTPException,
    Depends,
    APIRouter,
)
from sqlalchemy.ext.asyncio import AsyncSession

# General packages
from dotenv import load_dotenv

# Internal packages
import functions.utils as utils
import endpoints.security as security

# Database
import postgres.crud as crud
import postgres.models as models
import postgres.schemas as schemas
from postgres.database import get_db

################################## [ INIT ] ##################################

load_dotenv()

profiles, formats, workflows = utils.load_json()
ValidprofilesEnum = utils.create_enum("ValidprofilesEnum", profiles)
ValidformatsEnum = utils.create_enum("ValidformatsEnum", formats)
ValidworkflowsEnum = utils.create_enum("ValidworkflowsEnum", workflows)

router = APIRouter(prefix="/users", tags=["users"])


################################### [ API ] ##################################
# ------------------------------ Users Management ------------------------------


# List all users
@router.get(
    "/",
    dependencies=[Depends(security.check_token)],
)
async def read_users(
    db: AsyncSession = Depends(get_db), skip: int = 0, limit: int = 100
):
    utils.api_log("Retrieving all users")
    users = await crud.get_users(db, skip=skip, limit=limit)
    return utils.clean_users_data(users)


# Create a user
@router.post("/", dependencies=[Depends(security.check_token)])
async def create_user(user: schemas.UserCreate, db: AsyncSession = Depends(get_db)):
    utils.api_log(f"Creating a new user : {user.email}")
    db_user = await crud.get_user_by_email(db, email=user.email)
    if db_user:
        utils.api_log(f"DATABASE ERROR, user already registered : {user.email}\n\n")
        raise HTTPException(status_code=400, detail="User already registered")
    user = await crud.create_user(db=db, user=user)
    utils.api_log(f"User {user.email} created \n\n")
    return utils.clean_user_data(user)


# Delete specified user
@router.delete(
    "/{user_email}",
    dependencies=[Depends(security.check_token)],
)
async def delete_user(user_email: str, db: AsyncSession = Depends(get_db)):
    utils.api_log(f"Deleting user {user_email}")
    db_user = await crud.get_user_by_email(db, email=user_email)
    if db_user is None:
        utils.api_log(
            f"DATABASE ERROR, user {user_email} not found, impossible to delete\n\n"
        )
        raise HTTPException(status_code=404, detail="User not found")
    user = await crud.delete_user(db=db, email=user_email)
    utils.api_log(f"User {user_email} deleted \n\n")
    return utils.clean_user_data(user)


# Modify specified user
@router.put(
    "/{user_email}",
    dependencies=[Depends(security.check_token)],
)
async def update_user(
    user_email: str, user: schemas.UserUpdate, db: AsyncSession = Depends(get_db)
):
    utils.api_log(f"Updating user {user_email}")
    db_user = await crud.get_user_by_email(db, email=user_email)
    if db_user is None:
        utils.api_log(
            f"DATABASE ERROR, user {user_email} not found, impossible to update\n\n"
        )
        raise HTTPException(status_code=404, detail="User not found")
    user = await crud.update_user(db=db, email=user_email, user=user)
    utils.api_log(f"User {user_email} updated \n\n")
    return utils.clean_user_data(user)


# Reset user password as Admin
@router.get(
    "/{user_email}/password/forgotten",
    dependencies=[Depends(security.check_token)],
)
async def reset_user_password(
    password_change: schemas.UserPasswordChange,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    return {"message": "Forgotten Password Administrator to be implemented"}


# Activate user
@router.get(
    "/{user_email}/activate",
    dependencies=[Depends(security.check_token)],
)
async def activate_user(
    user_email: str, user: schemas.UserChangeStatus, db: AsyncSession = Depends(get_db)
):
    utils.api_log(f"Activating user {user_email}")
    db_user = await crud.get_user_by_email(db, email=user_email)
    if db_user is None:
        utils.api_log(
            f"DATABASE ERROR, user {user_email} not found, impossible to activate\n\n"
        )
        raise HTTPException(status_code=404, detail="User not found")
    user = await crud.activate_user(db=db, email=user_email, user=user)
    utils.api_log(f"User {user_email} activated \n\n")
    return utils.clean_user_data(user)


# Deactivate user
@router.get(
    "/{user_email}/deactivate",
    dependencies=[Depends(security.check_token)],
)
async def deactivate_user(
    user_email: str, user: schemas.UserChangeStatus, db: AsyncSession = Depends(get_db)
):
    utils.api_log(f"Deactivating user {user_email}")
    db_user = await crud.get_user_by_email(db, email=user_email)
    if db_user is None:
        utils.api_log(
            f"DATABASE ERROR, user {user_email} not found, impossible to deactivate\n\n"
        )
        raise HTTPException(status_code=404, detail="User not found")
    user = await crud.deactivate_user(db=db, email=user_email, user=user)
    utils.api_log(f"User {user_email} deactivated \n\n")
    return utils.clean_user_data(user)


# Reset user password (password reset)
@router.put("/password/reset", response_model=schemas.User)
async def change_password(
    password_change: schemas.UserPasswordChange,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    updated_user = await crud.change_user_password(
        db=db,
        user_id=current_user.id,
        old_password=password_change.old_password,
        new_password=password_change.new_password,
    )
    utils.api_log(f"Reseting password by credentials for user {current_user.email}")
    if updated_user is None:
        utils.api_log("DATABASE ERROR, incorrect password provided\n\n")
        raise HTTPException(status_code=400, detail="Old password is incorrect")
    utils.api_log(f"Password reseted for user {current_user.email}\n\n")
    return utils.clean_user_data(updated_user)


# Reset user password (email reset)
@router.get(
    "/password/forgotten",
)
async def reset_password(
    password_change: schemas.UserPasswordChange,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
):
    return {"message": "Forgotten Password to be implemented"}
