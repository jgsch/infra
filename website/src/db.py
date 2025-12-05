from datetime import date, datetime, time, timedelta

from sqlalchemy import (
    JSON,
    Column,
    Date,
    DateTime,
    Integer,
    String,
    Time,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

DATE_FORMAT = "%Y-%m-%d"
TIME_FORMAT = "%H-%M"


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False, unique=True)

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}')>"


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)

    type1: Mapped[str] = mapped_column(String, nullable=False)
    type2: Mapped[str | None] = mapped_column(String, nullable=True)
    type3: Mapped[str | None] = mapped_column(String, nullable=True)

    date: Mapped[datetime] = mapped_column(Date, nullable=False)
    time_start: Mapped[time] = mapped_column(Time, nullable=False)
    time_doors: Mapped[time] = mapped_column(Time, nullable=False)

    price: Mapped[str] = mapped_column(String, nullable=False)

    age: Mapped[int] = mapped_column(Integer, nullable=False)

    trigger_warnings: Mapped[list | None] = mapped_column(JSON, nullable=True)

    description: Mapped[str] = mapped_column(String, nullable=False)

    reminder_id: Mapped[str | None] = mapped_column(String, nullable=True)
    reminder_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user_id: Mapped[str] = mapped_column(String, nullable=False)

    def __repr__(self):
        return (
            f"<Event(id={self.id}, title='{self.title}', "
            + f"date='{self.date}', price='{self.price}', "
            + f"user_id='{self.user_id}', "
            + f"reminder_id='{self.reminder_id}')>"
        )

    def to_dict(self, edit: bool = False):
        event = {
            "id": self.id,
            "title": self.title,
            "subtitle": get_subtitle(self),
            "type1": self.type1,
            "type2": self.type2,
            "type3": self.type3,
            "date": self.date.strftime("%Y-%m-%d"),
            "day_name": self.date.strftime("%A"),
            "day_number": self.date.strftime("%d"),
            "month": self.date.strftime("%B"),
            "time_start": self.time_start.strftime("%Hh%M"),
            "time_doors": self.time_doors.strftime("%Hh%M"),
            "price": self.price,
            "age": self.age,
            "description": self.description,
            "datetime": formated_datetime(self.date, self.time_start),
            "reminder_id": self.reminder_id,
        }

        if edit:
            event["time_start"] = event["time_start"].replace("h", ":")
            event["date"] = event["date"].replace("h", ":")
            event["time_doors"] = event["time_doors"].replace("h", ":")

        if self.trigger_warnings is not None:
            event["trigger_warnings"] = self.trigger_warnings
            if edit:
                event["trigger_warnings"] = str(event["trigger_warnings"])

        return event


def get_database():
    engine = create_engine("sqlite:///./data/website.sqlite")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def get_subtitle(event: Event) -> str:
    subtitle = event.type1
    if event.type2 is not None and event.type2 != "":
        subtitle += f" · {event.type2}"
    if event.type3 is not None and event.type3 != "":
        subtitle += f" · {event.type3.lower().strip()}"
    return subtitle


def formated_datetime(date: date, start: time):
    return date.strftime(DATE_FORMAT) + "-" + start.strftime(TIME_FORMAT)


def fetch_event(db: Session, event_datetime: str) -> Event:
    splitted = event_datetime.split("-")
    if len(splitted) != 5:
        raise ValueError("Invalid datetime format")
        # return HTMLResponse("<p>Event invalid</p>", status_code=404)
    date, time_start = "-".join(splitted[:3]), "-".join(splitted[3:])

    date = datetime.strptime(date, DATE_FORMAT).date()
    time_start = datetime.strptime(time_start, TIME_FORMAT).time()

    event = (
        db.query(Event)
        .filter(Event.date == date)
        .filter(Event.time_start == time_start)
        .first()
    )

    if not event:
        raise ValueError("Not found")

    return event


def fetch_past_events(db: Session) -> list[Event]:
    return (
        db.query(Event)
        .filter(Event.date < datetime.now())
        .order_by(Event.date.des())
        .all()
    )


def fetch_future_events(db: Session) -> list[Event]:
    return (
        db.query(Event)
        .filter(Event.date >= datetime.now() - timedelta(days=1))
        .order_by(Event.date.asc())
        .all()
    )
