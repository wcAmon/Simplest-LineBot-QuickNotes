from datetime import datetime
from enum import Enum
from database import Base
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Boolean

## the model that write in database user_info
class UserInfo(Base):
    __tablename__ = "user_info"
    id = Column(Integer, primary_key=True, index=True)
    lineUserId = Column(String, unique=True, index=True)
    email = Column(String, unique=True, nullable=True)
    hashed_password = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)

## the model that write in database message_records
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
    def __init__(self, success: bool, msg: ProcessMessage):
        self.success = success
        self.msg = msg

## enum MessageType for validation of message type in inbound 
## payload
class MessageType(Enum):
    NULL = None
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    FILE = "file"

## Message class holds the message content for process, because 
## the image/audio/file message need to be fetch from the line 
## data endpoint. See FetchDataDocument: https://developers.line.
## biz/en/reference/messaging-api/#get-content
class Message:
    def __init__(self,
                 msg_id: str = None, 
                 msg_type: MessageType = MessageType.NULL, 
                 msg_text: str = None, 
                 msg_filename: str = None,
                 msg_reply_token: str = "",
                 msg_timestamp: datetime = datetime.now(),
                 owner_id: str = None,
                 error_description: str = None,
                 ) -> None:
        if msg_id is None:
            print("message initialize error, please verify.")
            raise ValueError
        self.msg_id = msg_id
        self.msg_type = msg_type
        if msg_text is None:
            msg_text = "this is a file message"
        self.msg_text = msg_text
        if msg_filename is None:
            msg_filename = "this is a text message"
        self.msg_filename = msg_filename
        self.msg_reply_token = msg_reply_token
        self.msg_timestamp = msg_timestamp
        self.owner_id = owner_id
        if error_description is None:
            error_description = ""
        self.error_description = error_description
    def __str__(self) -> str:
        if self.msg_type.value is None:
            return "this is a null message"
        return f"{self.msg_type.value} : {self.msg_id} : {self.msg_text} : {self.msg_filename}"
