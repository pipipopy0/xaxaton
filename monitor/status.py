from monitor.checks.system import check_systemd
from monitor.checks.duckling_docker import check_duckling
from monitor.checks.database import check_database
from monitor.checks.site import check_site
from monitor.checks.ssl import check_ssl
from monitor.checks.resources import check_resources
from monitor.checks.journal import check_journal
from monitor.checks.balance import get_balance_statuses

def get_full_status():

    result = []

    result += check_systemd()
    result.append(check_duckling())
    result.append(check_database())
    result.append(check_site())
    result.append(check_ssl())
    result += check_resources()
    result += get_balance_statuses()
    result += check_journal()
    

    return result


def format_status(status):

    text = "📊 Calendator Status\n\n"

    for item in status:

        icon = "🟢" if item["ok"] else "🔴"

        text += (
            f"{icon} {item['name']}: "
            f"{item['value']}\n"
        )

        if not item["ok"] and item.get("details"):
            text += (
                f"   {item['details']}\n"
            )

    return text