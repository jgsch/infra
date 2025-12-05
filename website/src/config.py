import locale
import logging
import os
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from fastapi.templating import Jinja2Templates
from rich.logging import RichHandler

load_dotenv()

EVENT_TYPES = [
    "long-métrage",
    "court-métrage",
    "animation",
    "documentaire",
    "ciné-concert",
    "concert",
    "concerts",
    "performance",
    "performances",
    "lecture",
    "discussion",
]


TELEGRAM_PUBLICATION = [
    "deux semaines avant",
    "une semaine avant",
    "un jour avant",
    "maintenant",
]


TIMEZONE = ZoneInfo("Europe/Paris")

templates = Jinja2Templates(directory="templates")

# locale.setlocale(locale.LC_ALL, "fr_CH.UTF-8")

#
# get needed environement variable
#


def get_env(var: str):
    if var not in os.environ:
        raise EnvironmentError(f"Missing environment varible '{var}'")
    return os.environ[var]


admin_secret_key = get_env("WEBSITE_ADMIN_SECRET_KEY")

TELEGRAM_HOST = get_env("BOT_TELEGRAM_HOST")

#
#
#


INFOMANIAK_CLIENT_ID = get_env("WEBSITE_INFOMANIAK_SSO_CLIENT_ID")
INFOMANIAK_CLIENT_SECRET = get_env("WEBSITE_INFOMANIAK_SSO_CLIENT_SECRET") 
INFOMANIAK_REDIRECT_URI = get_env("WEBSITE_INFOMANIAK_SSO_REDIRECT_URI") 

#
# setup logging
#


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
