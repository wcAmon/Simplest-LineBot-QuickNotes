from enum import Enum


class MessageType(Enum):
    NULL = None
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    FILE = "file"

if __name__ == "__main__":
    msgTypeStr = "text"
    msgType = MessageType[msgTypeStr]
    print(msgType)