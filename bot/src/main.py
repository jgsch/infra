import asyncio
import locale
import logging
import uuid
import os
from datetime import datetime

import uvicorn
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters

from utils import decode_image, setup_logging

locale.setlocale(locale.LC_ALL, "fr_CH.UTF-8")




def get_env(var: str):
    if var not in os.environ:
        raise EnvironmentError(f"Missing environment varible '{var}'")
    return os.environ[var]

TELEGRAM_BOT_TOKEN = get_env("BOT_TELEGRAM_TOKEN")
TELEGRAM_GROUP_ID = get_env("BOT_TELEGRAM_GROUP_ID")


#
# Logging setup
#

setup_logging()

log = logging.getLogger("telegram-bot")

#
# Telegram reminders
#

# Build the Telegram bot application using the provided token


async def delete_join_messages(update: Update, _: ContextTypes.DEFAULT_TYPE):
    await update.message.delete()


async def delete_left_messages(update: Update, _: ContextTypes.DEFAULT_TYPE):
    await update.message.delete()


bot = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
bot.add_handler(
    MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, delete_join_messages)
)
bot.add_handler(
    MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, delete_left_messages)
)

# Configure APScheduler to use a SQLite job store
jobstores = {"default": SQLAlchemyJobStore(url="sqlite:///./data/reminders.sqlite")}
scheduler = AsyncIOScheduler(jobstores=jobstores)


class ChildReminder(BaseModel):
    text: str
    date: datetime


class Reminder(BaseModel):
    text: str
    date: datetime
    image: str | None = None
    reply_to: int | None = None
    child: ChildReminder | None = None


async def send_message(reminder: Reminder, id: str):
    """ """

    try:
        img_sent = None
        if reminder.image is not None:
            img_sent = await bot.bot.send_photo(
                chat_id=TELEGRAM_GROUP_ID,
                photo=decode_image(reminder.image),
            )

        msg_sent = await bot.bot.send_message(
            chat_id=TELEGRAM_GROUP_ID,
            text=reminder.text,
            parse_mode="HTML",
            disable_web_page_preview=True,
            reply_to_message_id=reminder.reply_to,
        )

        log.debug("reminder posted")

    except Exception as e:
        log.error(f"fail to send message: {e}")

    if reminder.child is not None:
        try:
            message_id = msg_sent.message_id
            if img_sent is not None:
                message_id = img_sent.message_id

            reminder = Reminder(
                text=reminder.child.text,
                date=reminder.child.date,
                reply_to=message_id,
            )

            await post_reminders(reminder, id)

            log.debug("child reminder posted")
        except Exception as e:
            log.error(f"fail to add child reminder: {e}")


async def start_scheduler():
    """
    Start the APScheduler and wait indefinitely.
    """
    scheduler.start()
    log.info("Schedulers started")
    await asyncio.Event().wait()


async def start_bot():
    """
    Initialize and start the Telegram bot, then wait indefinitely.

    This function handles starting the bot and its polling loop.
    """
    try:
        await bot.initialize()
        await bot.start()
        await bot.updater.start_polling()  # type: ignore

        log.info("Bot started")
        await asyncio.Event().wait()
    finally:
        await bot.updater.stop()  # type: ignore
        await bot.stop()
        await bot.shutdown()


#
# API
#

api = FastAPI()


@api.post("/reminders")
async def post_reminders(reminder: Reminder, id: str | None = None):
    """
    API endpoint to create a new reminder.

    Receives reminder text, optional image, and the scheduled date.
    Returns a unique reminder ID.
    """

    if id is None:
        id = f"reminders-{str(uuid.uuid4())[:8]}"

    scheduler.add_job(
        send_message,
        run_date=reminder.date,
        args=[reminder, id],
        id=id,
    )

    log.debug(
        f"Reminder successfully added! (id='{id}'), "
        + f"date='{reminder.date}', image={reminder.image is not None}, "
        + f"child={reminder.child is not None}, "
        + f"child_date={None if reminder.child is None else reminder.child.date}):\n"
        + reminder.text
    )

    return {"id": id}


@api.get("/reminders")
def get_reminders() -> list[dict]:
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({"id": job.id, "text": job.args[0].text, "date": job.args[0].date})
    return jobs


@api.get("/reminders/{reminder_id}")
def get_reminder(
    reminder_id: str,
) -> Reminder:
    """
    API endpoint to retrieve details of a reminder by its ID.

    :param reminder_id: The unique reminder identifier.
    :return: A dictionary with reminder details or None if not found.
    """

    job = scheduler.get_job(reminder_id)

    if job is None:
        raise HTTPException(status_code=404, detail="Reminder not found")

    return job.args[0]


@api.delete("/reminders/{reminder_id}")
def delete_reminders(
    reminder_id: str,
):
    """
    API endpoint to delete a scheduled reminder by its ID.

    :param reminder_id: The unique reminder identifier.
    """
    scheduler.remove_job(reminder_id)
    log.debug(f"Reminder successfully removed! (id={reminder_id})")


async def start_api(host="127.0.0.1", port=8001):
    """
    Start the FastAPI server using uvicorn.

    :param host: Host address to bind the server.
    :param port: Port number to run the server.
    """
    config = uvicorn.Config(api, host=host, port=port, log_level="info")
    server = uvicorn.Server(config)
    log.info("API started")
    await server.serve()


async def main():
    """
    Main entry point to run the scheduler, Telegram bot, and API concurrently.
    """
    await asyncio.gather(start_scheduler(), start_bot(), start_api(host="0.0.0.0"))


if __name__ == "__main__":
    asyncio.run(main())

