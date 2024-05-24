
from typing import Annotated
import uvicorn
import yaml
from fastapi import FastAPI, Request, HTTPException, Depends, status
from rules import Base, UserInfo, MessageRecords, ProcessMessage
from database import engine, db_session
from sqlalchemy.orm import Session
from executors import ManagerBot, ClerkBot, CustomerBot, SeniorOfficerBot, StorageBot

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
with open('./config.yaml') as file:
    config = yaml.safe_load(file)
## initialize the manager bot
seniorBot = SeniorOfficerBot(config)
## Create a FastAPI instance
app = FastAPI()
## place liff webpage here

## Define the webhook endpoint
@app.post("/webhook", status_code = status.HTTP_200_OK)
async def handleInboundMessage(request: Request, db: db_driver):
    ## initialize the manager bot
    managerBot = ManagerBot(
        senior = seniorBot,
        DB = db
    )
    ## call manager bot to validate the x-line-signature
    ok = managerBot.validate_signature(request)
    if not ok:
        raise HTTPException(status_code=400, detail="Invalid signature")
    ## call clerk bot to process the inbound request string
    clerkBot = ClerkBot(manager = managerBot)
    ok, msg = clerkBot.getMessage()
    if not ok:
        managerBot.report_error(msg)
        

if __name__ == "__main__":
  uvicorn.run(
      "main:app",
      host="0.0.0.0",
      port=8080,
      log_level="info",
      reload=True
  )