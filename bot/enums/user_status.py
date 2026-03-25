from enum import Enum


class UserStatus(str, Enum):
    OFFLINE = "offline"
    WORKING = "working"
    PAUSED = "paused"
