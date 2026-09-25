import re
import time

from openai import OpenAI

from os import getenv
from dotenv import load_dotenv

from datetime import datetime, timedelta, timezone

from logger_config import logger
from handlers.answer_texts.TEXT import get_text

from zoneinfo import ZoneInfo


import json

load_dotenv()

POLZA_API = getenv("POLZA_API")
POLZA_URL = getenv("POLZA_URL")
GEMINI_FLASH_3 = getenv("GEMINI_FLASH_3")
EXCHANGE_RATE = float(getenv("EXCHANGE_RATE"))
PROVIDERS = {
    "primary": {
        "name": "polza",
        "base_url": POLZA_URL,
        "api_key": POLZA_API,
        "model": GEMINI_FLASH_3,
        "timeout": 30
    }
}
def create_client(provider_config):
    return OpenAI(
        base_url=provider_config["base_url"],
        api_key=provider_config["api_key"],
        timeout=provider_config["timeout"]

    )

def clean_json_response(content: str) -> str:

    if not content:
        return "{}"
    
    content = re.sub(r'```json\s*', '', content)
    content = re.sub(r'```\s*', '', content)
    
    content = content.strip()
    

    match = re.search(r'(\{.*\}|\[.*\])', content, re.DOTALL)
    if match:
        return match.group(1)
    
    return content

def calculate_cost(response, provider_key):
    try:
        usage = response.usage
            
        if provider_key == "primary":
            if hasattr(usage, "cost") and usage.cost is not None:
                return float(usage.cost)  
            else:
                prompt_tokens = getattr(usage, "prompt_tokens", 0)
                completion_tokens = getattr(usage, "completion_tokens", 0)
       
                input_p_gemini_3 = 49.93  
                output_p_gemini_3 = 299.6 
                return (prompt_tokens / 1_000_000) * input_p_gemini_3 + (completion_tokens / 1_000_000) * output_p_gemini_3
        
        
        return 0.0
            
    except Exception as e:
        logger.error(f"Ошибка расчета стоимости: {e}")
        return 0.0
    
def create_prompt(user_text: str, system_prompt: str, user_offset: str = None, history : list = None):
    if system_prompt.endswith(".txt"):
        with open(f"prompts/{system_prompt}", "r", encoding="utf-8") as file:
            SYSTEM_PROMPT = file.read()
    else:
        SYSTEM_PROMPT = system_prompt

    utc_now = datetime.now(timezone.utc)

    try:
        user_tz = ZoneInfo(user_offset)
        user_now = utc_now.astimezone(user_tz)
    except Exception as e:
        logger.error(e)
        user_now = utc_now
        
    time_now = user_now.strftime("%d.%m.%Y %H:%M")
    weekdays = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
    weekday_ru = weekdays[user_now.weekday()]
    history_text = "пустая"
    if history and isinstance(history, list) and len(history) > 0:
        history_parts = []
        for msg in history:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            history_parts.append(f"{role}: {content}")
        history_text = "\n".join(history_parts)
    system_content = (
        f"{SYSTEM_PROMPT}\n\n"
        f"СЕЙЧАС ВРЕМЯ: {time_now}, ДЕНЬ НЕДЕЛИ: {weekday_ru}\n"
        f"история взаимодействия: {history_text}"
    )
    messages=[
            {
                "role": "system", 
                "content": system_content
            },
            {
                "role": "user",
                "content": user_text
            }
        ]
    logger.info(f"Local time for user (offset={user_offset}): {time_now}, weekday={weekday_ru}")
    return messages

def ai_answer(user_text: str, system_prompt: str, history : list = None, user_offset: str = None, max_id = None):

    start = time.time()
    
    messages = create_prompt(user_text, system_prompt, user_offset, history)
    
    providers_to_try = ["primary"]

    for provider_key in providers_to_try:
        provider_config = PROVIDERS[provider_key]
        max_retries = 2
        last_error = None

        for attempt in range(max_retries):
            try:
                logger.info(f"Пробуем {provider_key} (попытка {attempt + 1}/{max_retries})")
                client = create_client(provider_config=provider_config)
                response = client.chat.completions.create(
                    model=provider_config["model"],
                    messages=messages,
                    temperature=0.25,
                    timeout=provider_config["timeout"]
                )
                response_cost = calculate_cost(response=response, provider_key=provider_key)
                logger.info(f"Cost response from {provider_key}: {response_cost:.6f}")
                end = time.time()
                logger.info(f"AI response time: {end - start:.2f} seconds")
                content = response.choices[0].message.content
                
                if content is None:
                    raise Exception("Empty AI Answer")
                
                cleaned_content = clean_json_response(content)
                
                try:
                    response_data = json.loads(cleaned_content)
                except json.JSONDecodeError as e:
                    logger.error(f"Error parsing json {provider_key}: {e}")
                    logger.error(f"Original: {content}")
                    logger.error(f"Clear: {cleaned_content}")
                    text_error = get_text(key="ai_not_understood", max_id=max_id)
                    response_data = {"action": "chat", "text": text_error}
                
                logger.info(f"Успешный ответ от {provider_key}")
                return {
                    "response": response_data,
                    "response_cost": response_cost,
                    "provider": provider_key,
                    "tokens": {
                        "input": getattr(response.usage, "prompt_tokens", 0),
                        "output": getattr(response.usage, "completion_tokens", 0),
                        "total": getattr(response.usage, "total_tokens", 0)
                    }
                }
                
            except TimeoutError as e:
                last_error = e
                logger.error(f"Timeout {provider_key} (attempt {attempt+1}): {e}")
                time.sleep(0.5 * (attempt + 1))  
                
            except ConnectionError as e:
                last_error = e
                logger.error(f"Connection error {provider_key} (attempt {attempt+1}): {e}")
                time.sleep(0.5 * (attempt + 1))
                
            except Exception as e:
                last_error = e
                logger.error(f"Error {provider_key} (attempt {attempt+1}): {e}")
                time.sleep(0.5 * (attempt + 1))
        
        logger.warning(f"Provider {provider_key} didn`t work reconnect to another")
    
    logger.error(f"All providers are unavailable. Last erorr: {last_error}")
    text_error = get_text(key="error_ai_response", max_id=max_id)
    return {
        "response": {"action": "chat", "text": text_error},
        "response_cost": 0,
        "provider": "none",
        "error": str(last_error) if last_error else "Unknown error"
    }