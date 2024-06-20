from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Float, Date, LargeBinary, DateTime
from database import Base


class Users(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)  # Email should be unique
    # password = Column(String)  # No need for index on password
    # password = Column(LargeBinary, nullable=False)  # Use LargeBinary for longer hashes
    name = Column(String) # ex. Jon Doe
    picture_embeddings = Column(String, index=True)  # Array of floats
    security_pin = Column(Integer, index=True)  # 4-digit pin check

class Transactions(Base):
    __tablename__ = 'transaction_history'

    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String, ForeignKey("users.email"))
    transaction_date = Column(DateTime)
    total_payment = Column(Float)
