from datetime import datetime
from typing import Annotated
import base64
import hashlib
import hmac
from multiprocessing import Process
import uvicorn
import yaml
import json
from fastapi import FastAPI, Request, HTTPException, Depends, status
from models import Base, UserInfo, MessageRecords, ProcessMessage
from database import engine, db_session
from handlers import ReplyMessageHandler, TextMessageHandler
from sqlalchemy.orm import Session

## Load the config file
with open('config.yaml') as file:
    config = yaml.safe_load(file)
## Get the channel secret from the config file
channel_secret = config["CHANNEL_SECRET"]
reply_endpoint = config["REPLY_ENDPOINT"]
channel_access_token = config["CHANNEL_ACCESS_TOKEN"]
## Create sqlite data.db, but only if it doesn't exist
Base.metadata.create_all(bind=engine)
def setup_db_session():
    db = db_session()
    try:
        yield db
    finally:
        db.close()
db_driver = Annotated[Session, Depends(setup_db_session)]
## Create a FastAPI instance
app = FastAPI()

@app.get("/", status_code = status.HTTP_200_OK)
async def home(db: db_driver):
    db.query(UserInfo).all()

@app.get("/users/", status_code = status.HTTP_200_OK)
async def get_user_by_line_id(db: db_driver, lineUserId: str):
    user_object = db.query(UserInfo).filter(UserInfo.lineUserId == lineUserId).first()
    return user_object


## Define the webhook endpoint
@app.post("/webhook", status_code = status.HTTP_200_OK)
async def handleInboundMessage(request: Request, db: db_driver):
    ## Validate the x-line-signature
    body_bytes = await request.body()
    body = body_bytes.decode('utf-8')
    signature = request.headers.get('x-line-signature')
    hash = hmac.new(channel_secret.encode('utf-8'),
        body.encode('utf-8'), hashlib.sha256).digest()
    correct_signature = base64.b64encode(hash).decode()
    if signature != correct_signature:
        raise HTTPException(status_code=400, detail="Invalid signature")
    ## Parse the body and extract the message events
    body_dict = json.loads(body)
    events = body_dict.get("events")
    for event in events:
        if event.get("type") == "message":
            line_user_id = event.get("source").get("userId")
            time_stamp = datetime.fromtimestamp(event.get("timestamp")/1000)
            message = event.get("message")
            reply_token = event.get("replyToken")
            if message.get("type") == "text":
                handle_status = TextMessageHandler(db, line_user_id, time_stamp, message.get("text"))
                if not handle_status.success:
                   res = await ReplyMessageHandler(reply_endpoint, channel_access_token, reply_token, handle_status.msg.value)
                   print("response from line server", res)
                   return
        else:
            print("Event type not message")
            return
                    
    res = await ReplyMessageHandler(reply_endpoint, channel_access_token, reply_token, ProcessMessage.ALL_OK.value)
    print("response from line server", res)


if __name__ == "__main__":
  uvicorn.run(
      "main:app",
      host="0.0.0.0",
      port=8080,
      log_level="info",
      reload=True
  )