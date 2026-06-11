import os
import httpx
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv("/opt/bots/numerium_bot/.env")

PROXY_URL = os.getenv("PROXY_URL")

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    http_client=httpx.Client(
        proxy=PROXY_URL,
        timeout=180.0
    )
)


def ask_gpt(prompt: str) -> str:
    response = client.responses.create(
        model="gpt-5.4",
        input=prompt
    )
    return response.output_text


def interpret_destiny_number(data: dict) -> str:
    from numerology.prompts import build_destiny_number_prompt
    return ask_gpt(build_destiny_number_prompt(data))


def interpret_life_path(data: dict) -> str:
    from numerology.prompts import build_life_path_prompt
    return ask_gpt(build_life_path_prompt(data))


def interpret_compatibility(data: dict) -> str:
    from numerology.prompts import build_compatibility_prompt
    return ask_gpt(build_compatibility_prompt(data))


def interpret_personal_qualities(data: dict) -> str:
    from numerology.prompts import build_personal_qualities_prompt
    return ask_gpt(build_personal_qualities_prompt(data))


def interpret_purpose(data: dict) -> str:
    from numerology.prompts import build_purpose_prompt
    return ask_gpt(build_purpose_prompt(data))
