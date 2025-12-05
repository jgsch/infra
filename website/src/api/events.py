import html
import logging
import random
import sys
from datetime import datetime, time, timedelta
from pathlib import Path

import httpx
from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, Response
from sqlalchemy.orm import Session

from config import EVENT_TYPES, TELEGRAM_HOST, TELEGRAM_PUBLICATION, TIMEZONE, templates
from db import Event, fetch_event, get_database, get_subtitle
from utils import encode_image, get_current_user, html_to_telegram, is_authenticated
from bot import ChildReminder, Reminder


log = logging.getLogger("events")


router = APIRouter(prefix="/events", tags=["Events"])


def validation(params: dict, edit: bool = False):
    params["title"] = params["title"].upper()

    # types

    if params["type1"] == params["type2"]:
        raise ValueError("Le type1 et le type2 ne peuvent pas être pareil")
    if params["type1"] == params["type3"]:
        raise ValueError("Le type1 et le type3 ne peuvent pas être pareil")

    if params["type3"] != "" and params["type3"] is not None:
        params["type3"] = params["type3"].lower().strip()
        if params["type2"] == params["type3"]:
            raise ValueError("Le type2 et le type3 ne peuvent pas être pareil")

    # date

    params["date"] = datetime.strptime(params["date"], "%Y-%m-%d").date()
    if not edit:
        if datetime.now().date() > params["date"]:
            raise ValueError("Un événement ne peut pas être ajouté dans le passé")

    params["time_start"] = datetime.strptime(params["time_start"], "%H:%M").time()
    params["time_doors"] = datetime.strptime(params["time_doors"], "%H:%M").time()
    if params["time_doors"] > params["time_start"]:
        raise ValueError(
            "L'heure de début doit être après l'heure d'ouverture des portes"
        )

    # age

    if params["age"] < 0:
        raise ValueError("Invalid age")

    # trigger warnings

    if params["trigger_warnings"] is not None:
        params["trigger_warnings"] = list(
            set([tw.strip().lower() for tw in params["trigger_warnings"]])
        )

    if params["description"] in ["", "<p><br></p>", None]:
        raise ValueError("La description ne peut pas être vide")

    return params


#
# Telegram bot utils
#


def _get_reminder_date(event_date: datetime, when: str) -> datetime:
    match when:
        case "deux semaines avant":
            date = event_date - timedelta(days=14)
            date = datetime.combine(date, time(21, 0), tzinfo=TIMEZONE)
        case "une semaine avant":
            date = event_date - timedelta(days=7)
            date = datetime.combine(date, time(21, 0), tzinfo=TIMEZONE)
        case "un jour avant":
            date = event_date - timedelta(days=1)
            date = datetime.combine(date, time(21, 0), tzinfo=TIMEZONE)
        case "jour même":
            date = datetime.combine(event_date, time(12, 0), tzinfo=TIMEZONE)
        case "maintenant":
            date = datetime.now(TIMEZONE) + timedelta(seconds=15)
        case _:
            raise ValueError("Invalid publication timeline")

    date = date.astimezone(TIMEZONE)

    now = datetime.now(TIMEZONE)
    if now > date:
        raise ValueError(
            "La publication telegram ne peut pas être faite dans le passé\n"
            + f"(now={now}, reminder_date={date})"
        )

    return date


class TelegramReminder:
    def __init__(
        self,
        event: Event,
        when: datetime,
        child_when: datetime | None,
        image: str | None,
    ):
        reminder = Reminder(
            text=self._get_reminder_text(event),
            date=when,
            image=image,
        )

        if child_when is not None:
            reminder.child = ChildReminder(
                text=self._get_second_reminder_text(),
                date=child_when,
            )

        self.reminder = reminder

    def _get_reminder_text(self, event: Event) -> str:
        text = (
            f"<b>{event.title}</b>\n\n"
            + html_to_telegram(event.description)
            + "\n\n"
            + f"⁉ {get_subtitle(event)}\n"
            + f"📅 {event.date.strftime('%A %d %B')}\n"
            + f"⏰ portes : {event.time_doors.strftime('%Hh%M')} début : {event.time_start.strftime('%Hh%M')}\n"
            + f"💰 {event.price} (cash uniquement)"
        )

        text_len, max_length = len(text), 4000
        if text_len > max_length:
            raise ValueError(
                f"La publication Telegram ne peut pas dépasser {max_length} "
                + f"caractères (actuellement, elle en contient {text_len}). Veuillez "
                + "réduire la longueur de la description ou choisir de ne pas "
                + "publier sur Telegram. La publication telegram ne peut pas être de "
            )

        return text

    def _get_second_reminder_text(self) -> str:
        emojis = ["😁", "🤩", "🥳", "🔥", "💯", "", "😎"]
        texts = ["c'est aujourd'hui", "aujourd'hui", "ce soir", "c'est ce soir"]

        text = (
            random.choice(texts)
            + " "
            + random.randint(1, 3) * "!"
            + " "
            + random.randint(1, 2) * random.choice(emojis)
        )
        text = text.strip()

        if random.randrange(0, 100) > 50:
            text = text.upper()

        return text

    async def post(self) -> str:
        async with httpx.AsyncClient() as client:
            host = f"{TELEGRAM_HOST}/reminders"
            log.debug(f"push reminder to '{host}'")
            res = await client.post(host, json=self.reminder.model_dump(mode="json"))

        if res.status_code != 200:
            raise ValueError(res.json()["detail"])

        return res.json()["id"]


async def get_reminder(reminder_id: str) -> Reminder | None:
    async with httpx.AsyncClient() as client:
        res = await client.get(f"{TELEGRAM_HOST}/reminders/{reminder_id}")

    if res.status_code != 200:
        log.error(f"Fail to get reminder (id={reminder_id}): {res.text}")
        return None

    return Reminder(**res.json())


async def cancel_reminder(reminder_id: str):
    async with httpx.AsyncClient() as client:
        res = await client.delete(f"{TELEGRAM_HOST}/reminders/{reminder_id}")
        if res.status_code == 200:
            log.debug(f"Reminder '{reminder_id}' cancelled!")
        else:
            log.debug(f"Reminder '{reminder_id}' cancellation failed: {res.text}")


#
# API
#


@router.post("")
async def create_event(
    request: Request,
    title: str = Form(...),
    type1: str = Form(...),
    type2: str | None = Form(None),
    type3: str | None = Form(None),
    date: str = Form(...),
    time_start: str = Form(...),
    time_doors: str = Form(...),
    age: int = Form(...),
    price: str = Form(...),
    trigger_warnings: list[str] | None = Form(None),
    description: str = Form(...),
    telegram_post: bool = Form(False),
    telegram_when_publish: str | None = Form(None),
    telegram_add_second_reminder: bool = Form(True),
    telegram_image: UploadFile = File(None),
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_database),
):
    data = {
        "title": title,
        "type1": type1,
        "type2": type2,
        "type3": type3,
        "date": date,
        "time_start": time_start,
        "time_doors": time_doors,
        "age": age,
        "price": price,
        "trigger_warnings": trigger_warnings,
        "description": description,
    }

    try:
        data = validation(data)
    except ValueError as e:
        data["time_start"] = data["time_start"].strftime("%H:%M")  # type: ignore
        data["time_doors"] = data["time_doors"].strftime("%H:%M")  # type: ignore
        return add_page_template(request, data, str(e))

    event = Event(**data, reminder_id=None, user_id=current_user)

    # check if an events has already been planned for this moment

    already_planned_events = (
        db.query(Event)
        .filter(Event.date == event.date)
        .filter(Event.time_start == event.time_start)
        .all()
    )
    if len(already_planned_events) > 0:
        error = "À événement est déjà prévu à cette date et heure d'ouverture"
        log.error(error)
        return add_page_template(request, event.to_dict(edit=True), error)

    # add a telegram reminder if wanted

    if telegram_post and telegram_when_publish:
        try:
            image = None
            if telegram_image.size != 0:
                image = await encode_image(telegram_image)

            when = _get_reminder_date(event.date, telegram_when_publish)

            child_when = None
            if telegram_add_second_reminder and telegram_when_publish != "jour même":
                child_when = _get_reminder_date(event.date, "jour même")

            reminder = TelegramReminder(event, when, child_when, image)

            event.reminder_id = await reminder.post()
            log.debug(f"Reminder added! (id={event.reminder_id})")
        except Exception as error:
            err = f"Adding telegram reminder failed: {error}"
            log.error(err)
            return add_page_template(request, event.to_dict(edit=True), err)

    # add a telegram reminder if wanted

    db.add(event)
    db.commit()
    db.refresh(event)

    log.info(f"New event added (title='{event.title}', " + f"date='{event.date})")

    return templates.TemplateResponse(
        "event.html",
        {
            "request": request,
            **event.to_dict(),
            "is_authenticated": is_authenticated(request),
        },
    )


def add_page_template(request, parameters: dict = {}, error: str | None = None):
    template_parameter = {
        "request": request,
        "today": datetime.now().strftime("%Y-%m-%d"),
        "event_types": EVENT_TYPES,
        "telegram_when_publish": TELEGRAM_PUBLICATION,
        "is_authenticated": is_authenticated(request),
        **parameters,
    }

    if error is not None:
        template_parameter["error"] = error

    return templates.TemplateResponse("event-add-or-modify.html", template_parameter)


@router.get("/add", response_class=HTMLResponse)
async def add_event_page(
    request: Request,
    _: str = Depends(get_current_user),
):
    return add_page_template(request)


@router.get("/{event_datetime}", response_class=HTMLResponse)
async def get_event_page(
    event_datetime: str,
    request: Request,
    db: Session = Depends(get_database),
):
    event = fetch_event(db, event_datetime).to_dict()

    event["description"] = html.unescape(html.unescape(event["description"]))

    return templates.TemplateResponse(
        "event.html",
        {
            "request": request,
            **event,
            "is_authenticated": is_authenticated(request),
        },
    )


@router.get("/{event_datetime}/edit", response_class=HTMLResponse)
async def edit_event_page(
    event_datetime: str,
    request: Request,
    _: str = Depends(get_current_user),
    db: Session = Depends(get_database),
):
    event = fetch_event(db, event_datetime).to_dict(edit=True)

    if event["reminder_id"] is not None:
        try:
            reminder = await get_reminder(event["reminder_id"])
            if reminder is not None:
                event["reminder_date"] = reminder.date.strftime("%A %d %B à %Hh%M")
                if reminder.child is not None:
                    event["telegram_add_second_reminder"] = True
        except Exception:
            log.error("Failed to communicate with the Telegram bot.")

    return templates.TemplateResponse(
        "event-add-or-modify.html",
        {
            "request": request,
            **event,
            "today": datetime.now().strftime("%Y-%m-%d"),
            "is_authenticated": is_authenticated(request),
            "event_types": EVENT_TYPES,
            "telegram_when_publish": TELEGRAM_PUBLICATION,
        },
    )


@router.post("/{event_datetime}")
async def edit_event(
    request: Request,
    event_datetime: str,
    title: str = Form(...),
    type1: str = Form(...),
    type2: str | None = Form(None),
    type3: str | None = Form(None),
    date: str = Form(...),
    time_start: str = Form(...),
    time_doors: str = Form(...),
    age: int = Form(...),
    price: str = Form(...),
    trigger_warnings: list[str] | None = Form(None),
    description: str = Form(...),
    telegram_post: bool = Form(False),
    telegram_post_cancel: bool = Form(False),
    telegram_when_publish: str = Form(...),
    telegram_add_second_reminder: bool = Form(False),
    telegram_image: UploadFile = File(None),
    current_user: str = Depends(get_current_user),
    db: Session = Depends(get_database),
):
    data = {
        "title": title,
        "type1": type1,
        "type2": type2,
        "type3": type3,
        "date": date,
        "time_start": time_start,
        "time_doors": time_doors,
        "age": age,
        "price": price,
        "trigger_warnings": trigger_warnings,
        "description": description,
        "user": current_user,
    }

    try:
        data = validation(data, edit=True)
    except ValueError as e:
        if isinstance(data["time_start"], datetime):
            data["time_start"] = data["time_start"].strftime("%H:%M")  # type: ignore
        if isinstance(data["time_doors"], datetime):
            data["time_doors"] = data["time_doors"].strftime("%H:%M")  # type: ignore
        log.error(e)
        return add_page_template(request, data, str(e))

    #

    event = fetch_event(db, event_datetime)
    if event is None:
        raise ValueError("Event not found")

    # set new values

    for key, value in data.items():
        setattr(event, key, value)

    # telegram

    if telegram_post and telegram_post_cancel:
        error = "Vous ne pouvez pas annuler la publication sur telegram et publier en même temps"
        return add_page_template(request, event.to_dict(edit=True), error)

    reminder_id = None
    previous_reminder = None
    if event.reminder_id is not None:
        try:
            previous_reminder = await get_reminder(event.reminder_id)
            if previous_reminder is not None:
                await cancel_reminder(event.reminder_id)
            else:
                event.reminder_id = None
        except Exception:
            event.reminder_id = None

    if (telegram_post or event.reminder_id) and not telegram_post_cancel:
        try:
            image = None
            if telegram_image.size != 0:
                image = await encode_image(telegram_image)
            elif previous_reminder is not None:
                image = previous_reminder.image

            if telegram_post:
                when = _get_reminder_date(event.date, telegram_when_publish)
            elif previous_reminder:
                when = previous_reminder.date
            else:
                raise ValueError("Impossible to determinate posting date")

            child_when = None
            if (
                telegram_add_second_reminder
                and telegram_when_publish != "jour même"
                and telegram_when_publish != "maintenant"
            ):
                child_when = _get_reminder_date(event.date, "jour même")

            reminder = TelegramReminder(
                event,
                when,
                child_when,
                image,
            )
            reminder_id = await reminder.post()
        except Exception as e:
            log.error(f"Fail to add reminder: {e}")
            return add_page_template(request, event.to_dict(edit=True), str(e))

    event.reminder_id = reminder_id

    # push modifications

    db.commit()

    return templates.TemplateResponse(
        "event.html",
        {
            "request": request,
            **event.to_dict(),
            "is_authenticated": is_authenticated(request),
        },
    )


@router.delete("/{event_datetime}")
async def delete_event(
    event_datetime: str,
    db: Session = Depends(get_database),
    _: str = Depends(get_current_user),
):
    event = fetch_event(db, event_datetime)
    db.delete(event)
    db.commit()
    return Response(status_code=200, headers={"HX-Redirect": "/"})
