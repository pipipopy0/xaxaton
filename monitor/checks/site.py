import requests


def check_site():

    try:

        r = requests.get(
            "https://calendator.online",
            timeout=5
        )


        return {
            "name": "Site",
            "ok": r.status_code == 200,
            "value": str(r.status_code)
        }


    except Exception as e:

        return {
            "name": "Site",
            "ok": False,
            "value": str(e)
        }