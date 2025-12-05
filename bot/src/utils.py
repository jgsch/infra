import base64
import logging
import os
from io import BytesIO

from rich.logging import RichHandler

def decode(image: str) -> bytes:
    return base64.b64decode(image)

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


def setup_logging():
    logging.basicConfig(
        level=logging.DEBUG if os.getenv("DEBUG", False) else logging.INFO,
        format="%(message)s",
        datefmt="[%D %X]",
        handlers=[RichHandler()],
    )

    for package in [
        "apscheduler",
        "urllib3",
        "httpx",
        "PIL",
        "python_multipart",
        "httpcore",
        "telegram",
        "tzlocal",
    ]:
        logging.getLogger(package).setLevel(logging.CRITICAL)
