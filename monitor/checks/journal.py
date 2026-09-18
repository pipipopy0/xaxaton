import subprocess


def check_journal():
    errors = []

    result = subprocess.run(
        [
            "journalctl",
            "-u", "main.service",
            "--since", "10 minutes ago",
            "--no-pager",
        ],
        capture_output=True,
        text=True,
    )

    logs = result.stdout

    keywords = (
        "Traceback",
        "Exception",
        "ERROR",
        "CRITICAL",
        "IndexError",
        "KeyError",
        "ValueError",
        "TypeError",
        "RuntimeError",
    )

    if any(k in logs for k in keywords):
        errors.append({
            "name": "Journal",
            "ok": False,
            "value": "Есть ошибки",
            "details": logs[-1000:]
        })
    else:
        errors.append({
            "name": "Journal",
            "ok": True,
            "value": "OK",
            "details": ""
        })

    return errors