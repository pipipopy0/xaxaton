import ssl
import socket
from datetime import datetime


def check_ssl():

    try:

        ctx = ssl.create_default_context()

        with socket.create_connection(
            ("calendator.online",443)
        ) as sock:

            with ctx.wrap_socket(
                sock,
                server_hostname="calendator.online"
            ) as ssock:

                cert = ssock.getpeercert()


        expire = datetime.strptime(
            cert["notAfter"],
            "%b %d %H:%M:%S %Y %Z"
        )


        days = (
            expire -
            datetime.utcnow()
        ).days


        return {
            "name":"SSL",
            "ok": days > 7,
            "value": f"{days} дней"
        }


    except Exception as e:

        return {
            "name":"SSL",
            "ok":False,
            "value":str(e)
        }