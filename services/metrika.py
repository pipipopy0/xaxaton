import csv
import io
import time
from os import getenv
from typing import Optional

import httpx
from dotenv import load_dotenv

from logger_config import logger


load_dotenv()


# ============================================================
# CONFIG
# ============================================================

METRIKA_COUNTER_ID = getenv("METRIKA_COUNTER_ID")
METRIKA_OAUTH_TOKEN = getenv("METRIKA_OAUTH_TOKEN")

if not METRIKA_COUNTER_ID:
    METRIKA_COUNTER_ID = "111688581"

if not METRIKA_OAUTH_TOKEN:
    logger.warning(
        "METRIKA_OAUTH_TOKEN is not set. "
        "Metrika offline conversions will not work."
    )


METRIKA_URL = (
    f"https://api-metrika.yandex.net/"
    f"management/v1/counter/{METRIKA_COUNTER_ID}/"
    f"offline_conversions/upload"
)


# ============================================================
# MAIN FUNCTION
# ============================================================

async def send_metrika_event(
    client_id: Optional[str],
    target: str,
    yclid: Optional[str] = None,
    extra_params: Optional[dict] = None,
    event_time: Optional[int] = None,
) -> bool:
    """
    Отправляет одну офлайн-конверсию в Яндекс.Метрику.

    Пример:

        await send_metrika_event(
            client_id="123456789",
            target="start_bot",
            yclid="1234567890"
        )

    Параметры:

    client_id:
        ClientID Яндекс.Метрики.

    target:
        ID JavaScript-цели в Яндекс.Метрике.

    yclid:
        YCLID из Яндекс.Директа.

    extra_params:
        Дополнительные параметры CSV.
        Например:
        {
            "Price": "199",
            "Currency": "RUB"
        }

    event_time:
        Unix timestamp события.
        Если не указан — используется текущее время.
    """

    # --------------------------------------------------------
    # 1. Проверяем OAuth
    # --------------------------------------------------------

    if not METRIKA_OAUTH_TOKEN:
        logger.error(
            "Metrika: METRIKA_OAUTH_TOKEN is not configured"
        )
        return False

    # --------------------------------------------------------
    # 2. Проверяем Target
    # --------------------------------------------------------

    if not target:
        logger.error(
            "Metrika: target is empty"
        )
        return False

    # --------------------------------------------------------
    # 3. Должен быть хотя бы один идентификатор
    # --------------------------------------------------------

    if not client_id and not yclid:
        logger.warning(
            "Metrika: both client_id and yclid are empty. "
            "Conversion skipped."
        )
        return False

    # --------------------------------------------------------
    # 4. Время события
    # --------------------------------------------------------

    if event_time is None:
        # Берём несколько секунд назад,
        # чтобы время гарантированно было в прошлом.
        event_time = int(time.time()) - 5

    # --------------------------------------------------------
    # 5. Формируем CSV
    # --------------------------------------------------------

    row = {
        "Target": target,
        "DateTime": event_time,
        "ClientId": client_id or "",
        "Yclid": yclid or "",
    }

    # Добавляем дополнительные поля.
    if extra_params:
        row.update(extra_params)

    # Оставляем только нужные колонки.
    fieldnames = list(row.keys())

    csv_buffer = io.StringIO(
        newline=""
    )

    writer = csv.DictWriter(
        csv_buffer,
        fieldnames=fieldnames,
        extrasaction="ignore",
    )

    writer.writeheader()
    writer.writerow(row)

    csv_data = csv_buffer.getvalue().encode("utf-8")

    logger.info(
        "Metrika: preparing conversion "
        f"target={target}, "
        f"client_id={client_id}, "
        f"yclid={yclid}, "
        f"event_time={event_time}"
    )

    # --------------------------------------------------------
    # 6. Отправляем CSV в API Яндекс.Метрики
    # --------------------------------------------------------

    headers = {
        "Authorization": f"OAuth {METRIKA_OAUTH_TOKEN}",
    }

    files = {
        "file": (
            "offline_conversion.csv",
            csv_data,
            "text/csv",
        )
    }

    params = {
        "type": "BASIC",
        "comment": f"Calendator: {target}",
    }

    try:

        async with httpx.AsyncClient(
            timeout=15
        ) as client:

            response = await client.post(
                METRIKA_URL,
                headers=headers,
                params=params,
                files=files,
            )

        # ----------------------------------------------------
        # 7. Логируем настоящий ответ Яндекса
        # ----------------------------------------------------

        logger.info(
            f"Metrika API response: "
            f"status={response.status_code}, "
            f"body={response.text[:1000]}"
        )

        # ----------------------------------------------------
        # 8. Успешная загрузка
        # ----------------------------------------------------

        if response.status_code == 200:

            try:
                data = response.json()

                uploading = data.get(
                    "uploading",
                    {}
                )

                upload_id = uploading.get("id")
                status = uploading.get("status")

                logger.info(
                    "Metrika conversion uploaded successfully: "
                    f"target={target}, "
                    f"upload_id={upload_id}, "
                    f"status={status}"
                )

            except Exception:
                logger.warning(
                    "Metrika: response is 200, "
                    "but JSON could not be parsed."
                )

            return True

        # ----------------------------------------------------
        # 9. Ошибка API
        # ----------------------------------------------------

        logger.error(
            "Metrika API error: "
            f"status={response.status_code}, "
            f"body={response.text[:2000]}"
        )

        return False

    except httpx.TimeoutException:

        logger.error(
            "Metrika API timeout"
        )

        return False

    except httpx.HTTPError as e:

        logger.error(
            f"Metrika HTTP error: {e}"
        )

        return False

    except Exception:

        logger.exception(
            "Metrika unexpected error"
        )

        return False