from ast import In
from asyncio import events
from datetime import datetime
from enum import Enum
import json
from typing import Any, Dict, List, Tuple
from sqlalchemy.orm import Session
from fastapi import Request
import base64
import hashlib
import hmac

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
                 owner_id: str = None
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
    def __str__(self) -> str:
        if self.msg_type.value is None:
            return "this is a null message"
        return f"{self.msg_type.value} : {self.msg_id} : {self.msg_text} : {self.msg_filename}"

##: the manager bot holds signature validation and database 
##: operations. See VerifySignatureDocument: https://developers.
##: line.biz/en/docs/messaging-api/receiving-messages/ 
##: #verify-signature
class ManagerBot:
    def __init__(
            self,
            Config: Dict[str, str],
            DB: type[Session],
            ) -> None:
        self.channel_secret = Config["CHANNEL_SECRET"]
        self.channel_access_token = Config["CHANNEL_ACCESS_TOKEN"]
        self.reply_endpoint = Config["REPLY_ENDPOINT"]
        self.DB = DB
    def online(self) -> None:
        if self.channel_access_token == "" or self.channel_secret == "":
            print("Manager bot sleeping...")
        else:
            print("Manager bot at your service!")
    async def validate_signature(
            self, 
            request: Request
            ) -> Tuple[bool, str]:
        ## Validate the x-line-signature
        body_bytes = await request.body()
        body = body_bytes.decode('utf-8')
        signature = request.headers.get('x-line-signature')
        hash = hmac.new(self.channel_secret.encode('utf-8'),
            body.encode('utf-8'), hashlib.sha256).digest()
        correct_signature = base64.b64encode(hash).decode()
        if signature != correct_signature:
            return (False, "")
        return (True, body)

## the clerk bot deals with every incoming message
class ClerkBot:
    def __init__(
            self,
            IncomingPayload: str
            ) -> None:
        self.payload = json.load(IncomingPayload)
        self.replyToken = ""
        self.webhookEventId = ""
        self.line_user_id = ""
        self.time_stamp = ""
    ## events in payload is List[Dict[str, str]], but only one 
    ## event is inside the list currently and its is subjective to 
    ## change by the line api. Refer to WebhookEventDocument: 
    ## https://developers.line.biz/en/docs/messaging-api/
    ## receiving-messages/
    ## webhook-event-in-one-on-one-talk-or-group-chat 
    ## for more info.
    def __process_events(self) -> Tuple[bool , Dict[Any, str]]:
        events = self.payload.get("events")
        if events is None:
            return (False, {})
        event = events[0]
        isReDeliver = event.get("deliveryContext").get("isRedelivery")
        if isReDeliver:
            return (False, {})
        if event.get("source").get("userId") is None:
            print("No user id found")
            return (False, {})
        self.replyToken = event.get("replyToken")
        self.webhookEventId = event.get("webhookEventId")
        self.line_user_id = event.get("source").get("userId")
        ## the timestamp is in milliseconds according to
        ## WebhookEventDocument, 
        ## so we need to convert it to seconds, adjust the process 
        ## subjectively
        self.__process_timestamp(event.get("timestamp")/1000)
        return (True, event.get("message"))
    def __process_message(self) -> Tuple[bool, Message]:
        ok, message = self.__process_events()
        if not ok:
            return (False, )
        msgType = message.get("type")
        if msgType is None:
            return (False, [{}])
        ## process the message based on the type: text, image, file, audio
        return (True, Message(
            msg_id = message.get("id"),
            msg_type = MessageType[msgType.upper()],
            msg_text = message.get("text"),
            msg_filename = message.get("fileName"),
            msg_reply_token = self.replyToken,
            msg_timestamp= self.time_stamp,
            owner_id = self.line_user_id
        ))
    def __process_timestamp(self, timestamp: int) -> datetime:
        self.time_stamp = datetime.fromtimestamp(timestamp)
    ## get message after initialize clerk bot
    def getMessage(self) -> Tuple[bool, Message]:
        return self.__process_message()

## the customer bot will handle response message
class CustomerBot:
    def __init__(
            self,
            manager: ManagerBot,
            OutgoingPayload: str
            ) -> None:
        self.manager = manager
        pass