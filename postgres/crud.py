# ------------------------------ PACKAGES ------------------------------
# Independant packages
from passlib.context import CryptContext
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

# Database
from postgres.models import User
from postgres.schemas import UserCreate, UserUpdate

# -------------------------------- PASSWORD --------------------------------
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


async def change_user_password(
    db: AsyncSession, user_id: int, old_password: str, new_password: str
):
    db_user = await get_user(db, user_id)
    if db_user and verify_password(old_password, db_user.hashed_password):
        db_user.hashed_password = get_password_hash(new_password)
        await db.commit()
        await db.refresh(db_user)
        return db_user
    return None


async def reset_password(db: AsyncSession, email: str, new_password: str):
    db_user = await get_user_by_email(db, email)
    if db_user:
        db_user.hashed_password = get_password_hash(new_password)
        await db.commit()
        await db.refresh(db_user)
        return db_user
    return None


# ------------------------------ RETRIEVE USER ------------------------------
async def get_user(db: AsyncSession, user_id: int):
    query = select(User).filter(User.id == user_id)
    result = await db.execute(query)
    user = result.scalars().first()
    return user


async def get_user_by_email(db: AsyncSession, email: str):
    query = select(User).filter(User.email == email)
    result = await db.execute(query)
    user = result.scalars().first()
    return user


async def get_users(db: AsyncSession, skip: int = 0, limit: int = 100):
    query = select(User).offset(skip).limit(limit)
    result = await db.execute(query)
    users = result.scalars().all()  # Fetch all rows and convert to list
    return users


# ------------------------------ MANAGE USER ------------------------------
async def create_user(db: AsyncSession, user: UserCreate):
    db_user = User(
        surname=user.surname,
        firstname=user.firstname,
        email=user.email,
        hashed_password=get_password_hash(user.password),
        disabled=False,
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user


async def update_user(db: AsyncSession, email: str, user: UserUpdate):
    db_user = await get_user_by_email(db, email)
    if not db_user:
        return None
    for key, value in user.dict(exclude_unset=True).items():
        setattr(db_user, key, value)
    await db.commit()
    await db.refresh(db_user)
    return db_user


async def delete_user(db: AsyncSession, email: str):
    db_user = await get_user_by_email(db, email)
    if db_user:
        await db.delete(db_user)
        await db.commit()
    return db_user


async def activate_user(db: AsyncSession, email: str):
    db_user = await get_user_by_email(db, email)
    if db_user and db_user.disabled:
        db_user.disabled = False
        await db.commit()
        await db.refresh(db_user)
        return db_user
    return db_user


async def deactivate_user(db: AsyncSession, email: str):
    db_user = await get_user_by_email(db, email)
    if db_user and db_user.disabled:
        db_user.disabled = True
        await db.commit()
        await db.refresh(db_user)
        return db_user
    return db_user