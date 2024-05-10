from datetime import datetime
from models import MessageRecords, UserInfo
from database import db_driver
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

DATABASE_URL = "sqlite:///./data.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
db_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def test_db(db: Session):
    user = db.query(UserInfo).filter(UserInfo.id == 1).first()
    
    TextMessageRecord = MessageRecords(
    userInfo_id=1,
    lineUserId=user.lineUserId, 
    message="hello", 
    timestamp=datetime.fromtimestamp(1234567890)
    )
    db.add(TextMessageRecord)
    db.commit()
    db.close()

if __name__ == "__main__":
    test_db(db_session())