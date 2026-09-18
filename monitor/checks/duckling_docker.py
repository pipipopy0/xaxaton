import requests


def check_duckling():

    try:

        r = requests.post(
            "http://127.0.0.1:8001/parse",
            data={
                "text": "tommorow",
                "locale": "en_US"
            },
            timeout=5
        )
        if r.status_code == 200:
            data = r.json()
            if data:
                data_str = data[0]["value"]["value"]
                date_part = data_str.split("T")[0]
                year,month,day = date_part.split("-")
                str_answer = f"tommorrow: {day}.{month}.{year}"
                return {
                    "name": "Duckling",
                    "ok": r.status_code == 200,
                    "value": str_answer
                }


    except Exception as e:

        return {
            "name": "Duckling",
            "ok": False,
            "value": str(e)
        }