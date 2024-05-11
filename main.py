
from typing import Annotated
import uvicorn
import yaml
import json
from fastapi import FastAPI, Request, HTTPException, Depends, status
from models import Base, UserInfo, MessageRecords, ProcessMessage
from database import engine, db_session
from handlers import ReplyMessageHandler, TextMessageHandler
from sqlalchemy.orm import Session
from executors import ManagerBot, ClerkBot

## Create sqlite data.db, but only if it doesn't exist
Base.metadata.create_all(bind=engine)
def setup_db_session():
    db = db_session()
    try:
        yield db
    finally:
        db.close()
db_driver = Annotated[Session, Depends(setup_db_session)]
## Load the config file
with open('../config.yaml') as file:
    config = yaml.safe_load(file)
## initialize the manager bot
managerBot = ManagerBot(Config=config, DB=db_driver)
managerBot.online()
## Create a FastAPI instance
app = FastAPI()

@app.get("/", status_code = status.HTTP_200_OK)
async def Users(db: db_driver):
    db.query(UserInfo).all()

## get user by line id
@app.get("/users/", status_code = status.HTTP_200_OK)
async def get_user_by_line_id(db: db_driver, lineUserId: str):
    user_object = db.query(UserInfo).filter(UserInfo.lineUserId == lineUserId).first()
    return user_object


## Define the webhook endpoint
@app.post("/webhook", status_code = status.HTTP_200_OK)
async def handleInboundMessage(request: Request, db: db_driver):
    ## call manager bot to validate the x-line-signature
    ok, bodyStr = managerBot.validate_signature(request)
    ## call clerk bot to process the inbound body string
    clerkBot = ClerkBot(IncomingPayload = bodyStr)
    ok, message = clerkBot.getMessage()
    if not ok:
        ## call customer bot to inform user, maybe try to send message again 
        pass
    ## call manager bot to store the message into database

    pass

if __name__ == "__main__":
  uvicorn.run(
      "main:app",
      host="0.0.0.0",
      port=8080,
      log_level="info",
      reload=True
  )