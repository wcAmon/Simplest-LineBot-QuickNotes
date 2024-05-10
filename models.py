from enum import Enum
from database import Base
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Boolean
from sqlalchemy.sql import func as Date

class UserInfo(Base):
    __tablename__ = "user_info"
    id = Column(Integer, primary_key=True, index=True)
    lineUserId = Column(String, unique=True, index=True)
    email = Column(String, unique=True, nullable=True)
    hashed_password = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)

class MessageRecords(Base):
    __tablename__ = "message_records"
    id = Column(Integer, primary_key=True, index=True)
    userInfo_id = Column(Integer, ForeignKey("user_info.id"))
    lineUserId = Column(String, index=True)
    message = Column(String)
    filename = Column(String, nullable=True)
    filepath = Column(String, nullable=True)
    timestamp = Column(DateTime, nullable=True)

class ProcessMessage(Enum):
    ALL_OK = "all is well"
    USER_NOT_FOUND = "no user found in the authorized database"
    USER_CREATE_ERROR = "creating user failed"
    DATABASE_WRITE_ERROR = "writing in database failed"
    DATABASE_READ_ERROR = "reading from database failed"
    DATABASE_UPDATE_ERROR = "updating database failed"
    DATABASE_DELETE_ERROR = "deleting from database failed"
    DATABASE_CONNECTION_ERROR = "database connection failed"

class HandleStatus:
    def __init__(self, msg: ProcessMessage, success: bool):
        self.msg = msg
        self.success = success
    