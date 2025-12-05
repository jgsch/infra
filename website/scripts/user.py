import argparse
import os
import secrets

import requests  # type: ignore
from dotenv import load_dotenv

load_dotenv()


parser = argparse.ArgumentParser()
parser.add_argument("task", choices=["add", "delete"])
parser.add_argument("username", type=str)
parser.add_argument("--host", type=str, default="http://127.0.0.1:8000")
args = parser.parse_args()

admin_password = os.environ["ADMIN_SECRET_KEY"]
if admin_password is None:
    raise EnvironmentError("Missing ADMIN_PASSWORD environment variable")

match args.task:
    case "add":
        username = args.username
        password = secrets.token_urlsafe(10)

        out = requests.post(
            f"{args.host}/users",
            json={
                "username": username,
                "password": password,
                "admin_password": admin_password,
            },
        )

        if out.status_code == 200:
            print(f"User added!\n  username: {username}\n  password: {password}")
        elif out.status_code == 409:
            overwrite = input("Username already registered, overwrite? [y/N]: ")

            if overwrite.lower() in ["y", "yes"]:
                out = requests.post(
                    f"{args.host}/users",
                    json={
                        "username": username,
                        "password": password,
                        "admin_password": admin_password,
                        "overwrite": True,
                    },
                )

                if out.status_code == 200:
                    print(
                        f"User added!\n  username: {username}\n  password: {password}"
                    )

        else:
            raise RuntimeError(out.json()["detail"])

    case "delete":
        out = requests.delete(
            f"{args.host}/users",
            json={
                "username": args.username,
                "admin_password": admin_password,
            },
        )

        if out.status_code == 200:
            print("User deleted!")
        else:
            raise RuntimeError(out.json()["detail"])
