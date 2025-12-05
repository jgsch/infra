import uvicorn
from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from api import archive, auth, events, infos, newsletter, users
from config import admin_secret_key, templates
from db import fetch_future_events, get_database
from utils import is_authenticated

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

app.add_middleware(SessionMiddleware, secret_key=admin_secret_key, max_age=3600)

app.mount("/assets", StaticFiles(directory="./assets"), name="assets")

app.include_router(archive.router)
app.include_router(auth.router)
app.include_router(events.router)
app.include_router(infos.router)
app.include_router(newsletter.router)
app.include_router(users.router)


@app.get("/", response_class=HTMLResponse)
def index(request: Request, db: Session = Depends(get_database)):
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "events": [event.to_dict() for event in fetch_future_events(db)],
            "is_authenticated": is_authenticated(request),
        },
    )


@app.get("/cinema", response_class=HTMLResponse)
def cinema():
    # legacy path
    return RedirectResponse(url="/")


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
