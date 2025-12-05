import base64
import html
import html as ihtml
import re
from io import BytesIO
from typing import Any
from urllib.parse import parse_qs, urlencode

import bcrypt
from bs4 import BeautifulSoup, NavigableString, Tag
from fastapi import HTTPException, Request, UploadFile
from PIL import Image, UnidentifiedImageError


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


def encode(image: bytes) -> str:
    return base64.b64encode(image).decode("utf-8")


def decode(image: str) -> bytes:
    return base64.b64decode(image)


async def encode_image(upload_file: UploadFile) -> str:
    image = await upload_file.read()
    try:
        Image.open(BytesIO(image)).verify()
    except UnidentifiedImageError:
        raise ValueError("L'image de la publication telegram n'est pas valide")
    return encode(image)


def decode_image(encoded_image: str) -> BytesIO:
    image = Image.open(BytesIO(decode(encoded_image)))
    if image.mode in ("RGBA", "P"):
        image = image.convert("RGB")

    # Resize while preserving aspect ratio
    width, height = image.size
    scale = 1280 / max(width, height)
    if scale < 1:  # Only shrink if too big
        new_size = (int(width * scale), int(height * scale))
        image = image.resize(new_size)

    image_bytes = BytesIO()
    image.save(image_bytes, format="JPEG", quality=75, optimize=True)
    image_bytes.seek(0)

    return image_bytes


# telegram utils


def _watch_url(video_id: str, qs: str | None) -> str:
    params = parse_qs(qs or "")
    keep = {}
    # preserve start time & playlist
    if params.get("start"):  # embed param
        keep["t"] = params["start"][0]
    elif params.get("t"):  # already a t= param
        keep["t"] = params["t"][0]
    if params.get("list"):
        keep["list"] = params["list"][0]
    return (
        "https://www.youtube.com/watch?v="
        + video_id
        + (("&" + urlencode(keep)) if keep else "")
    )


def html_to_telegram(html: str) -> str:
    """ """

    soup = BeautifulSoup(html or "", "html.parser")

    root_children = (soup.body or soup).children

    ctx = {"indent": 0, "in_pre": False}
    out_parts = []

    for node in root_children:
        out_parts.append(_walk(node, ctx))

    out = "".join(out_parts).strip()
    out = re.sub(r"\n{3,}", "\n\n", out)
    # out = _split_telegram(out, max_len)

    return out


def _walk(node: Any, ctx: dict[str, Any]) -> str:
    if isinstance(node, NavigableString):
        text = str(node)
        if ctx["in_pre"]:
            return _escape_text(text)  # preserve whitespace
        return _escape_text(re.sub(r"\s+", " ", text))

    text = node.get_text()
    if "iframe" in text:
        if "youtube" in text:
            pattern = re.compile(r"/embed/([A-Za-z0-9_-]{11})")
            match = pattern.search(text)
            if match is None:
                return ""
            return f"https://youtu.be/{match.group(1)}\n"
        elif "vimeo" in text:
            pattern = re.compile(r"/video/(\d+)")
            match = pattern.search(text)
            if match is None:
                return ""
            return f"https://vimeo.com/{match.group(1)}\n"
        elif "soundcloud" in text:
            pattern = re.compile(
                r"""href=(['"])(https?://soundcloud\.com/[^/'"\s?#]+/[^'"\s?#]+)\1""",
                re.IGNORECASE | re.VERBOSE,
            )
            match = pattern.search(text)
            if match is None:
                return ""
            link = match.group(2)
            return link + "\n"
        elif "bandcamp" in text:
            pattern = re.compile(
                r"""href=(['"])(https?://[a-z0-9-]+\.bandcamp\.com/album/[^'"\s?#]+)\1""",
                re.IGNORECASE | re.VERBOSE,
            )
            match = pattern.search(text)
            if match is None:
                return ""
            link = match.group(2)
            return link + "\n"
        else:
            return ""

    if not isinstance(node, Tag):
        return ""

    tag = (node.name or "").lower()

    if tag in ("p", "div"):
        inner = _children_to_text(node, ctx)
        return _trim(inner) + "\n"

    if tag == "br":
        return "\n"

    if tag in ("strong", "b"):
        return _wrap_non_empty("<b>", _children_to_text(node, ctx), "</b>")
    if tag in ("em", "i"):
        return _wrap_non_empty("<i>", _children_to_text(node, ctx), "</i>")
    if tag in ("u", "ins"):
        return _wrap_non_empty("<u>", _children_to_text(node, ctx), "</u>")
    if tag in ("s", "del", "strike"):
        return _wrap_non_empty("<s>", _children_to_text(node, ctx), "</s>")

    if tag == "a":
        href = (node.get("href") or "").strip()
        text = _trim(_children_to_text(node, ctx))
        if not href or not text:
            return text
        return f'<a href="{_escape_attr(href)}">{text}</a>'

    if tag == "ul":
        items = [c for c in node.children if isinstance(c, Tag) and c.name == "li"]
        lines = []
        for li in items:
            line = (
                _indent(ctx["indent"])
                + "• "
                + _trim(_walk_children(li, {**ctx, "indent": ctx["indent"] + 2}))
            )
            lines.append(line)
        return "\n".join(lines) + "\n"

    if tag == "ol":
        items = [c for c in node.children if isinstance(c, Tag) and c.name == "li"]
        lines = []
        for idx, li in enumerate(items, start=1):
            line = (
                _indent(ctx["indent"])
                + f"{idx}. "
                + _trim(_walk_children(li, {**ctx, "indent": ctx["indent"] + 2}))
            )
            lines.append(line)
        return "\n".join(lines) + "\n"

    if tag == "li":
        return (
            _indent(ctx["indent"]) + "• " + _trim(_children_to_text(node, ctx)) + "\n"
        )

    if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
        t = _trim(_children_to_text(node, ctx))
        return (f"<b>{t}</b>\n\n") if t else ""

    return _children_to_text(node, ctx)


def _children_to_text(el: Tag, ctx: dict[str, Any]) -> str:
    return "".join(_walk(c, ctx) for c in el.children)


def _walk_children(el: Tag, ctx: dict[str, Any]) -> str:
    return _children_to_text(el, ctx)


def _raw_code_text(el: Tag) -> str:
    t = el.get_text()
    return _escape_text(t)


def _inline_code_text(el: Tag) -> str:
    t = re.sub(r"\s+", " ", el.get_text())
    return _escape_text(t)


def _escape_text(s: str) -> str:
    return ihtml.escape(s, quote=False)


def _escape_attr(s: str) -> str:
    return ihtml.escape(s, quote=True)


def _wrap_non_empty(prefix: str, inner: str, suffix: str) -> str:
    return f"{prefix}{inner}{suffix}" if inner.strip() else ""


def _trim(s: str) -> str:
    return re.sub(r"^\s+|\s+$", "", s)


def _indent(n: int) -> str:
    return " " * max(0, n)


def _split_telegram(s: str, max_len: int) -> list[str]:
    if len(s) <= max_len:
        return [s] if s else []
    parts = []
    rest = s
    while len(rest) > max_len:
        cut = rest.rfind("\n\n", 0, max_len)
        if cut < int(max_len * 0.6):
            cut = rest.rfind("\n", 0, max_len)
        if cut < int(max_len * 0.6):
            cut = max_len  # hard split
        parts.append(rest[:cut].rstrip())
        rest = rest[cut:].lstrip()
    if rest:
        parts.append(rest)
    return parts


def remove_iframes(text: str):
    soup = BeautifulSoup(html.unescape(text), "html.parser")
    for iframe in soup.find_all("iframe"):
        iframe.decompose()
    return str(soup).replace("<p><br/></p>", "")


# def remove_images(text: str):
#     soup = BeautifulSoup(html.unescape(text), "html.parser")
#     for iframe in soup.find_all("img"):
#         iframe.decompose()
#     return str(soup).replace("<p><br/></p>", "")
#
#
# def remove_links(text: str):
#     soup = BeautifulSoup(text, "html.parser")
#     for a in soup.find_all("a"):
#         a.unwrap()
#     return str(soup)


def is_authenticated(request: Request):
    return request.session.get("user") is not None


def get_current_user(request: Request):
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Access denied")
    return user
