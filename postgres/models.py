# ------------------------------ PACKAGES ------------------------------
# Independant packages
from sqlalchemy import Boolean, Column, Integer, String


# Database
from postgres.database import Base


# ------------------------------ MODELS ------------------------------
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    surname = Column(String)
    firstname = Column(String)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    disabled = Column(Boolean, default=False)
