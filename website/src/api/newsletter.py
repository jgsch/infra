import html
import re
import textwrap

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from config import templates
from db import Event, fetch_future_events, get_database, get_subtitle
from utils import get_current_user, is_authenticated, remove_iframes

router = APIRouter(prefix="/newsletter", tags=["Newsletter"])


@router.get("")
def get_newsletter_page(
    request: Request,
):
    return templates.TemplateResponse(
        "newsletter.html",
        {
            "request": request,
            "is_authenticated": is_authenticated(request),
        },
    )


@router.get("/new")
def get_newsletter_new_page(
    request: Request,
    db: Session = Depends(get_database),
    _: str = Depends(get_current_user),
):
    return templates.TemplateResponse(
        "newsletter-new.html",
        {
            "request": request,
            "events": [event.to_dict() for event in fetch_future_events(db)],
            "is_authenticated": is_authenticated(request),
        },
    )


@router.post("/generate", response_class=HTMLResponse)
async def generate_newsletter(
    request: Request,
    db: Session = Depends(get_database),
    _: str = Depends(get_current_user),
):
    form_data = await request.form()

    def clean(text):
        return re.sub(r"(<p><br></p>){2,}", r"<p><br></p>", text)

    introduction_text = clean(form_data.getlist("description")[0])

    if introduction_text == "<p><br></p>":
        introduction_text = None

    events = ""
    for event_id in form_data.getlist("selected_events"):
        event = db.query(Event).filter(Event.id == event_id).first()
        if event is None:
            continue

        subtitle = get_subtitle(event)
        doors = event.time_doors.strftime("%Hh%M")
        start = event.time_start.strftime("%Hh%M")

        description = remove_iframes(event.description)

        events += f"""
          <tr>
            <td>
              <div>{event.date.strftime("%A %d %B")}</div>
              <div class="event-title">{event.title}</div>
              <div class="event-details">{subtitle}</div>
              {description}
              <div class="event-details">portes : {doors} / début : {start}</div>
              <div class="event-details">entrée : {event.price}</div>
            </td>
          </tr>
        """
    events = clean(events)

    newsletter = templates.get_template("newsletter-email.html").render(
        {
            "introduction_text": introduction_text,
            "events": events,
        }
    )

    response = f"""
    <textarea style="width: 100%; height: 600px; padding: 10px; border: 1px solid #cccccc;" readonly>
    {html.escape(newsletter)}
    </textarea>
    """

    # clean response
    response = re.sub(r"\n\s*\n+", "\n", response)
    response = textwrap.dedent(response)
    response = response.strip()

    return response
