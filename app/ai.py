import os
import httpx
from dotenv import load_dotenv
from openai import AsyncOpenAI

from numerology.prompts import (
    build_destiny_number_prompt,
    build_life_path_prompt,
    build_compatibility_prompt,
    build_personal_qualities_prompt,
    build_purpose_prompt,
)

load_dotenv("/opt/bots/numerium_bot/.env")

PROXY_URL = os.getenv("PROXY_URL")

client = AsyncOpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    http_client=httpx.AsyncClient(
        proxy=PROXY_URL,
        timeout=180.0
    )
)


async def ask_gpt(prompt: str) -> str:
    response = await client.responses.create(
        model="gpt-5.4",
        input=prompt
    )
    return response.output_text


async def interpret_destiny_number(data: dict) -> str:
    return await ask_gpt(build_destiny_number_prompt(data))


async def interpret_life_path(data: dict) -> str:
    return await ask_gpt(build_life_path_prompt(data))


async def interpret_compatibility(data: dict) -> str:
    return await ask_gpt(build_compatibility_prompt(data))


async def interpret_personal_qualities(data: dict) -> str:
    return await ask_gpt(build_personal_qualities_prompt(data))


async def interpret_purpose(data: dict) -> str:
    return await ask_gpt(build_purpose_prompt(data))
