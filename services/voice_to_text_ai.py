import base64
import time
import aiohttp
import httpx
import subprocess
import json

from dotenv import load_dotenv
from os import getenv

from logger_config import logger, debug_logger

load_dotenv()

OPENROUTER_API = getenv("OPENROUTER_API")
OPENROUTER_AUDIO_URL = getenv("OPENROUTER_AUDIO_URL")
POLZA_API = getenv("POLZA_API")
POLZA_AUDIO_URL = getenv("POLZA_AUDIO_URL")

WHISPER_LARGE_V3_TURBO = getenv("WHISPER_LARGE_V3_TURBO")
WHISPER_1 = getenv("WHISPER_1")
GPT_4O_MINI_TRANSCRIBE = getenv("GPT_4O_MINI_TRANSCRIBE")


#все цены я перевожу в рубли.
EXCHANGE_RATE = float(getenv("EXCHANGE_RATE"))

TRANSCRIPTION_CHAIN = [
    {
        "provider": "fallback",
        "name": "openrouter",
        "base_url": OPENROUTER_AUDIO_URL,
        "api_key": OPENROUTER_API,
        "model": WHISPER_LARGE_V3_TURBO,
        "timeout": 30,
        "pricing" : {
            "type": "fixed",
            "price_per_minute": ((0.04/60)*EXCHANGE_RATE)#0.04$ за час.
        }
    },
    {
        "provider": "fallback",
        "name": "openrouter",
        "base_url": OPENROUTER_AUDIO_URL,
        "api_key": OPENROUTER_API,
        "model": GPT_4O_MINI_TRANSCRIBE,
        "timeout": 30,
        "pricing" : {
            "type": "api_cost"
        }
    },
    {
        "provider": "primary",
        "name": "polza",
        "base_url": POLZA_AUDIO_URL,
        "api_key": POLZA_API,
        "model": WHISPER_LARGE_V3_TURBO,
        "timeout": 30,
        "pricing" : {
            "type": "fixed",
            "price_per_minute": 0.05
        }
    },
    {
        "provider": "primary",
        "name": "polza",
        "base_url": POLZA_AUDIO_URL,
        "api_key": POLZA_API,
        "model": WHISPER_1,
        "timeout": 30,
        "pricing" : {
            "type": "fixed",
            "price_per_minute": 0.43
        }
    }
]
        
        
        


def get_ogg_duration_minutes(file_path: str) -> float:
    """Возвращает длительность OGG-файла в минутах через ffprobe."""
    cmd = [
        'ffprobe', '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'json',
        file_path
    ]
    try:
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)
        data = json.loads(output)
        duration_sec = float(data['format']['duration'])
        return duration_sec / 60.0
    except Exception as e:
        logger.error(f"ffprobe error: {e}")
        return 0.0 

async def transcribe(file_path: str):
    try:
        duration_min = get_ogg_duration_minutes(file_path)
        if duration_min > 2:
            return {
                        "text": None,
                        "voice_cost_rub": 0,
                        "duration": duration_min,
                        "provider" : None,
                        "model" : None,
                        "error": "Audio duration > 2 minutes"
                    }
        # Открываем файл в бинарном режиме
        with open(file_path, "rb") as f:
            # Читаем файл и переводим в base64
            audio_b64 = base64.b64encode(f.read()).decode()
        
        # JSON для OpenRouter
        
        last_error = None
        for provider in TRANSCRIPTION_CHAIN:
            try:
                data = None
                if provider["provider"] == "primary":
                    with open(file_path, "rb") as f:
                        form = aiohttp.FormData()
                        form.add_field("file", f)
                        form.add_field("model", provider["model"])
                        headers = {
                            "Authorization": f"Bearer {provider['api_key']}"
                        }
                            
                        async with aiohttp.ClientSession() as session:
                            async with session.post(
                                provider["base_url"],
                                data=form,  
                                headers=headers,
                                timeout=provider["timeout"]
                            ) as resp:
                                data = await resp.json()
                elif provider["provider"] == "fallback":
                    headers = {
                        "Authorization": f"Bearer {provider['api_key']}",
                        "Content-Type": "application/json"
                    }
                    payload = {
                        "model": provider["model"],
                        "input_audio": {
                            "data": audio_b64,
                            "format": "ogg"
                        }
                    }
                    async with httpx.AsyncClient() as client:
                        response = await client.post(
                            provider["base_url"],
                            json=payload,
                            headers=headers,
                            timeout=provider["timeout"]
                        ) 

                                # Ответ от сервера
                        data = response.json()

                if "text" not in data:
                    logger.error(f"{provider['name']} ({provider['model']}) response: {data}")
                    raise Exception("No text in response")
                pricing = provider["pricing"]            
                if pricing["type"] == "api_cost":
                    cost_usd = data.get("usage", {}).get("cost", 0)
                    voice_cost_rub = cost_usd * EXCHANGE_RATE
                elif pricing["type"] == "fixed":
                    voice_cost_rub = pricing["price_per_minute"] * duration_min

                logger.info(f"Transcribed: {data['text'][:50]}... (cost: {voice_cost_rub:.6f}) Provider: {provider['name']} ({provider['model']})")
                            # Возвращаем текст
                return {
                    "text" : data["text"],
                    "voice_cost_rub" : voice_cost_rub,
                    "duration" : duration_min,
                    "provider" : provider['name'],
                    "model" : provider['model'],
                    "error" : None
                    }
            except Exception as e:
                last_error = e 
                logger.error(
                    f"{provider['name']} ({provider['model']}) failed: {e}"
                )
                                    
            
            logger.warning(
                f"{provider['name']} ({provider['model']}) failed, trying next"
            )
        
        logger.error(f"All providers failed. Last error: {last_error}")
        return {
            "text": None,
            "voice_cost_rub": 0,
            "duration": duration_min,
            "provider" : None,
            "model" : None,
            "error": str(last_error) if last_error else "Unknown error"
        }
                        
    except Exception as e:
        logger.error(f"Error in transcribe: {e}", exc_info=True)
        return {
            "text": None,
            "voice_cost_rub": 0,
            "duration": 0,
            "provider" : None,
            "model" : None,
            "error": str(e)
            }