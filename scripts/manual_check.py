import requests

r = requests.post(
    "http://localhost:8000/api/guess", json={"guess": "DADOS", "day_index": 0, "attempt_number": 6}
)

print(r.json())
