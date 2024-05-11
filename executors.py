from datetime import datetime
import json
from typing import Any, Dict, Tuple
from sqlalchemy.orm import Session
from fastapi import Request
import base64
import hashlib
import hmac
from handlers import ReplyMessageHandler, MessageRecordHandler
from rules import ProcessMessage, MessageType, Message

## the senior officer bot only holds a custom dictionary call 
## "configuration key", nothing more, nothing else
class SeniorOfficerBot:
    def __init__(self, configuration_key) -> None:
        self.channel_secret = configuration_key.get("CHANNEL_SECRET")
        self.channel_access_token = configuration_key.get("CHANNEL_ACCESS_TOKEN")
        self.reply_endpoint = configuration_key.get("REPLY_ENDPOINT")

##: the manager bot is responsible for signature validation and 
##: database operations. See VerifySignatureDocument: https://
##: developers.line.biz/en/docs/messaging-api/receiving-messages/ 
##: #verify-signature
class ManagerBot:
    def __init__(
            self,
            senior: SeniorOfficerBot,
            DB: type[Session]
            ) -> None:
        self.channel_secret = senior.channel_secret
        self.channel_access_token = senior.channel_access_token
        self.reply_endpoint = senior.reply_endpoint
        self.DB = DB
        self.body_str = ""
        self.outgoingPayload = Message(msg_id="0")
    def online(self) -> None:
        if self.channel_access_token == "" or self.channel_secret == "":
            print("Manager bot sleeping...something went wrong!")
        else:
            print("Manager bot at your service!")
    ## record the payload for further processing
    def __record_payload(self, payload: Message) -> None:
        self.outgoingPayload = payload
    ## validate the x-line-signature    
    async def validate_signature(
            self, 
            request: Request
            ) -> bool:
        ## Validate the x-line-signature
        body_bytes = await request.body()
        body = body_bytes.decode('utf-8')
        signature = request.headers.get('x-line-signature')
        hash = hmac.new(self.channel_secret.encode('utf-8'),
            body.encode('utf-8'), hashlib.sha256).digest()
        correct_signature = base64.b64encode(hash).decode()
        if signature != correct_signature:
            return False
        self.body_str = body
        return True
    ## deal error from other bots and decide what to do
    def report_error(self, msg: Message) -> bool:
        self.__record_payload(msg)

    ## deal success from other bots
    def report_success(self, msg: ProcessMessage) -> None:
        print(f"Success: {msg.value}")

    

## the clerk bot deals with every incoming message
class ClerkBot:
    def __init__(
            self,
            manager: ManagerBot
            ) -> None:
        self.payload = json.load(manager.body_str)
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
            return (False, Message(msg_id="", error_description="No valid message events received"))
        msgType = message.get("type")
        if msgType is None:
            return (False, Message(
                msg_id="",
                reply_token=self.replyToken, 
                error_description="No valid message type found"))
        ## process the message based on the type: text, image, file, audio
        return (True, Message(
            msg_id = message.get("id"),
            msg_type = MessageType[msgType.upper()],
            msg_text = message.get("text"),
            msg_filename = message.get("fileName"),
            msg_reply_token = self.replyToken,
            msg_timestamp= self.time_stamp,
            owner_id = self.line_user_id,
            error_description = ""
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
            ) -> None:
        self.manager = manager
        self.payload = manager.outgoingPayload
    def __generate_reply_message(self) -> str:
        if self.payload.error_description != "":
            return f'we have a problem: {self.payload.error_description}'
        return f'we have received and processed your {self.payload.msg_type} message.'
    async def respond_message(self) -> Dict[str, str]:
        reply_message = self.__generate_reply_message()
        ## extract the reply token from the payload
        reply_token = self.payload.msg_reply_token
        if reply_token == "":
            print("No reply token found, and the error description: ", reply_message)
            return {}
        ## call the reply message handler
        res = await ReplyMessageHandler(
            reply_endpoint=self.manager.reply_endpoint,
            channel_access_token=self.manager.channel_access_token,
            reply_token=reply_token,
            message=reply_message
        )
        json_res = json.loads(res)
        print(json_res)
        return json_res
    
class StorageBot:
    def __init__(
            self,
            manager: ManagerBot,
            object_to_store: Message
            ) -> None:
        self.manager = manager
        self.object_to_store = object_to_store
    def __file_storage_operation(self) -> Tuple[bool, str]:
        
        pass
    def process_message(self) -> None:
        if self.object_to_store.msg_type == MessageType.TEXT:
            success, msg = MessageRecordHandler(
                    db = self.manager.DB,
                    message = self.object_to_store
                )
            if not success:
                self.manager.report_error(msg)
            else:
                self.manager.report_success(msg)
        else:
            success, report = self.__file_storage_operation()
            if not success:
                self.manager.report_error(report)
            else:
                self.manager.report_success(report)

## deal with file fetch from line data endpoint
class DeliveryBot:
    def __init__(
            self,
            manager: ManagerBot,
            object_to_fetch: Message
            ) -> None:
        self.manager = manager
        self.object_to_fetch = object_to_fetch
    def __file_fetch_operation(self) -> Tuple[bool, str]:
        FileFetchHandler()
        pass

