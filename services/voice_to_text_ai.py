import base64
import time
import aiohttp
import subprocess
import json

from dotenv import load_dotenv
from os import getenv

from logger_config import logger, debug_logger

load_dotenv()

POLZA_API = getenv("POLZA_API")
POLZA_AUDIO_URL = getenv("POLZA_AUDIO_URL")

WHISPER_LARGE_V3_TURBO = getenv("WHISPER_LARGE_V3_TURBO")
WHISPER_1 = getenv("WHISPER_1")
GPT_4O_MINI_TRANSCRIBE = getenv("GPT_4O_MINI_TRANSCRIBE")


EXCHANGE_RATE = float(getenv("EXCHANGE_RATE"))

TRANSCRIPTION_CHAIN = [
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
        with open(file_path, "rb") as f:
            audio_b64 = base64.b64encode(f.read()).decode()
               
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