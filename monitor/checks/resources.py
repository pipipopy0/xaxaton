import psutil


def check_resources():
    #cpu_percent = psutil.cpu_percent(interval=0.5)
    return [
        {
            "name":"RAM",
            "ok": psutil.virtual_memory().percent < 85,
            "value": f"{psutil.virtual_memory().percent}%"
        },
        #{
        #    "name": "CPU",
        #    "ok": cpu_percent < 80,
        #    "value": f"{cpu_percent}%"
        #},
        {
            "name":"Disk",
            "ok": psutil.disk_usage('/').percent < 80,
            "value": f"{psutil.disk_usage('/').percent}%"
        }
    ]