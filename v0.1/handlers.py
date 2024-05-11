import aiohttp
import json
from datetime import datetime
from sqlalchemy.orm import Session
from rules import ProcessMessage, UserInfo, MessageRecords, HandleStatus

async def ReplyMessageHandler(
        reply_endpoint: str,
        channel_access_token: str, 
        reply_token: str, 
        message: str
        ) -> str:
    print(f"Replying with message: {message}")
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {channel_access_token}'
    }
    reqBody = {
        "replyToken": reply_token,
        "messages": [
            {
                "type": "text",
                "text": message
            }
        ]
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(reply_endpoint, headers=headers, data=json.dumps(reqBody)) as response:
            return await response.text()


def TextMessageHandler(
        db: type[Session], 
        line_user_id: str, 
        time_stamp: datetime, 
        message: str
        ) -> HandleStatus:
    ## Check if the user exists in the database, if not, create a new user
    user_object = db.query(UserInfo).filter(UserInfo.lineUserId == line_user_id).first()
    if not user_object:
        try:
            new_user_info = UserInfo(lineUserId=line_user_id)
            db.add(new_user_info)
            db.commit()
            user_object = new_user_info
        except Exception as e:
            print("database create user error", e)
            return HandleStatus(ProcessMessage.USER_CREATE_ERROR, False)
    ## Create a new message record
    try:
        TextMessageRecord = MessageRecords(
        userInfo_id=user_object.id,
        lineUserId=line_user_id, 
        message=message, 
        timestamp=time_stamp
        )
        db.add(TextMessageRecord)
        db.commit()
    except Exception as e:
        print("database error", e)
        return HandleStatus(ProcessMessage.DATABASE_WRITE_ERROR, False)
    return HandleStatus(ProcessMessage.ALL_OK, True)