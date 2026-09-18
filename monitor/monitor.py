import time


from monitor.status import get_full_status, format_status
from monitor.notifier import send_alert

from . import state

import sys
sys.path.insert(0, '/root/Calendator')


def get_errors(status):

    errors = set()

    for item in status:

        if not item["ok"]:
            errors.add(
                item["name"]
            )

    return errors



while True:


    status = get_full_status()


    errors = get_errors(status)



    # новые ошибки
    if errors != state.last_errors:


        if errors:

            send_alert(
                "🚨 Calendator проблемы\n\n"
                +
                format_status(status)
            )

        else:

            send_alert(
                "✅ Все сервисы восстановлены"
            )

    state.last_errors = errors


    time.sleep(700)