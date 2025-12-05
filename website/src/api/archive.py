from datetime import datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import desc, extract
from sqlalchemy.orm import Session

from config import templates
from db import Event, formated_datetime, get_database, get_subtitle
from utils import is_authenticated

router = APIRouter(prefix="/archive", tags=["Archive"])


@router.get("", response_class=HTMLResponse)
def archive(
    request: Request,
    db: Session = Depends(get_database),
):
    events = (
        db.query(Event)
        .filter(extract("year", Event.date) == datetime.now().year)
        .order_by(desc(Event.date))
        .all()
    )
    return templates.TemplateResponse(
        "archive.html",
        {
            "request": request,
            "events": events,
            "years": list(range(datetime.now().year, 2009, -1)),
            "is_authenticated": is_authenticated(request),
        },
    )


@router.get("/{year}")
async def get_events(
    request: Request,
    year: int,
    db: Session = Depends(get_database),
):
    events = (
        db.query(Event)
        .filter(extract("year", Event.date) == year)
        .filter(Event.date < datetime.now())
        .order_by(desc(Event.date))
        .all()
    )

    event_html = ""
    for event in events:
        subtitle = get_subtitle(event)

        event_html += f"""
        <a href="/events/{formated_datetime(event.date, event.time_start)}" class="block">
        <div class="flex space-x-4 py-2 cursor-pointer">
            <div class="flex-shrink-0">{event.date}</div>
            <div>
                <div class="font-semibold">{event.title}</div>
                <div> {subtitle}</div>
            </div>
        </div>
        """

    return HTMLResponse(content=event_html)
