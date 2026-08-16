import os

from pathlib import Path

from dotenv import load_dotenv, find_dotenv
from langchain_groq import ChatGroq

load_dotenv(find_dotenv())

if not os.environ.get("GROQ_API_KEY"):
    raise RuntimeError("GROQ_API_KEY is not set. Add it to your .env file.")

llm = ChatGroq(
    model="qwen/qwen3.6-27b",
    temperature=0.3,
    max_tokens=None,
    reasoning_format="parsed",
    timeout=None,
    max_retries=2,
    # other params...
)

INSIGHT_PROMPT_TEMPLATE = """You are a public health assistant interpreting acoustic mosquito \
surveillance results for a non-technical field user.

Model detection results (percentage confidence):
- Anopheles (malaria vector): {anopheles}%
- Non-Anopheles mosquito: {non_anopheles}%

Environment: {environment}

Based on these results, write a short, clear safety interpretation (3-4 sentences) that:
1. States the likely risk level (low, moderate, or high).
2. Explains what the dominant detection means in plain language.
3. Gives 1-2 practical recommendations suited to the environment.

Do not mention model confidence scores or technical details. Speak directly to the person \
who will read this on the dashboard."""


def generate_insight(predictions: dict, environment: str = "unknown") -> str:
    prompt = INSIGHT_PROMPT_TEMPLATE.format(
        anopheles=predictions.get("anopheles", 0),
        non_anopheles=predictions.get("non_anopheles", 0),
        environment=environment,
    )
    response = llm.invoke(prompt)
    return response.content
