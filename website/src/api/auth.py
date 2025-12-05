import logging 

from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from config import templates, INFOMANIAK_CLIENT_ID, INFOMANIAK_CLIENT_SECRET, INFOMANIAK_REDIRECT_URI
from db import User, get_database
from utils import verify_password


log = logging.getLogger("auth")

oauth = OAuth()
oauth.register(
    name="infomaniak",
    client_id=INFOMANIAK_CLIENT_ID,
    client_secret=INFOMANIAK_CLIENT_SECRET,
    server_metadata_url="https://login.infomaniak.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid profile email"},
)


router = APIRouter(tags=["Auth"])


@router.get("/login", response_class=HTMLResponse)
async def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})



@router.post("/login")
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_database),
):
    username, password = form_data.username, form_data.password

    db_user = db.query(User).filter(User.username == username).first()
    if db_user is None:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid credentials"},
        )

    if not verify_password(password, db_user.hashed_password):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid credentials"},
        )

    request.session["user"] = username
    return RedirectResponse(url="/", status_code=303)

@router.get("/login/infomaniak")
async def login_infomaniak(request: Request):
    return await oauth.infomaniak.authorize_redirect(request, INFOMANIAK_REDIRECT_URI)


@router.get("/login/infomaniak/callback")
async def auth_infomaniak_callback(request: Request):
    token = await oauth.infomaniak.authorize_access_token(request)
    userinfo = token.get("userinfo")
    if not userinfo:
        resp = await oauth.infomaniak.get("userinfo", token=token)
        userinfo = resp.json()

    email = userinfo.get("email")
    sub = userinfo.get("sub")
    name = userinfo.get("name")

    if not email:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid email"},
        )

    domain = email.split("@")[-1].lower()
    if domain != "oblo.ch":
        log.error(f"Invalid email: {email}")
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid email"},
        )

    request.session["user"] =  name

    return RedirectResponse(url="/", status_code=303)


@router.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return Response(status_code=200, headers={"HX-Redirect": "/"})
