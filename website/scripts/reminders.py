import requests

host = "http://localhost:8001"

res = requests.get(
    f"{host}/reminders",
)

for reminder in res.json():
    print("#")
    print("#")
    print("#")
    print()
    print(reminder["id"])
    print(reminder["date"])
    print("---------------")
    print(reminder["text"])
    print("---------------")
    print()
