from pydantic import BaseModel
from datetime import datetime

class ChildReminder(BaseModel):
    text: str
    date: datetime


class Reminder(BaseModel):
    text: str
    date: datetime
    image: str | None = None
    reply_to: int | None = None
    child: ChildReminder | None = None
