from google import genai
from google.genai import types

from driftwatch.app import config

_client = genai.Client(api_key=config.GEMINI_API_KEY)


def get_embedding(text: str) -> list[float]:
    result = _client.models.embed_content(
        model="gemini-embedding-001",
        contents=text,
        config=types.EmbedContentConfig(output_dimensionality=768),
    )
    return result.embeddings[0].values
