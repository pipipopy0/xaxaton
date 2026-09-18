import subprocess


SERVICES = [
    "main.service",
    "flask.service",
    "nginx.service",
    "postgresql@18-main.service"
]


def check_systemd():

    result = []

    for service in SERVICES:

        status = subprocess.run(
            [
                "systemctl",
                "is-active",
                service
            ],
            capture_output=True,
            text=True
        ).stdout.strip()


        result.append({
            "name": service,
            "ok": status == "active",
            "value": status
        })


    return result