from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from config import templates

router = APIRouter(prefix="/infos", tags=["Infos"])


access = [
    "/assets/images/access-01.avif",
    "/assets/images/access-02.avif",
    "/assets/images/access-03.avif",
]


@router.get("", response_class=HTMLResponse)
def infos(request: Request):
    return templates.TemplateResponse(
        "infos.html",
        {
            "request": request,
            "access": access[0],
            "index": 0,
        },
    )


@router.get("/access/{index}/next")
async def next_access_image(request: Request, index: int):
    new_index = (index + 1) % len(access)
    return templates.TemplateResponse(
        "infos-access-carousel.html",
        {"request": request, "access": access[new_index], "index": new_index},
    )


@router.get("/access/{index}/prev")
async def prev_access_image(request: Request, index: int):
    new_index = (index - 1) % len(access)
    return templates.TemplateResponse(
        "infos-access-carousel.html",
        {"request": request, "access": access[new_index], "index": new_index},
    )
