from datetime import timedelta, datetime, timezone
from logger_config import logger
import requests

def get_correct_time():
    now_utc = datetime.now(timezone.utc)
    options = []
    for offset in range(-12,13):
        local_time = now_utc + timedelta(hours=offset)
        options.append({
            "offset": offset,
            "local_time": local_time.strftime("%d.%m.%Y %H:%M")
        })
    return options

def parser_duckling(time_text: str, user_offset: str):
    #time_text in 50 minutes
    utc_now = datetime.now(timezone.utc)
    reftime_ms = int(utc_now.timestamp() * 1000)

    try:
        response = requests.post(
            'http://localhost:8001/parse',
            data={'text': time_text, 'locale': 'en_US', 'reftime': reftime_ms, 'tz': user_offset},
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            if data:
                value = data[0].get('value', {})
                value_type = value.get('type')
                
                if value_type == 'value':
                    dt_str = value.get('value') 
                    parsed_data = datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S.%f%z")
                    return parsed_data
                elif value_type == 'interval':
                    from_str = value.get('from', {}).get('value')
                    to_str = value.get('to', {}).get('value')
                    if from_str and to_str:
                        start = datetime.strptime(from_str, "%Y-%m-%dT%H:%M:%S.%f%z")
                        end = datetime.strptime(to_str, "%Y-%m-%dT%H:%M:%S.%f%z")
                        return (start, end)
    except Exception as e:
        logger.error(f"Duckling error: {e}")
    return None