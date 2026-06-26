import base64
import json
from pathlib import Path

from .prompts import OUTPUT_SCHEMA, SYSTEM, USER

MODEL = "claude-opus-4-8"


def _client():
    import anthropic

    return anthropic.Anthropic()


def extract_records(pdf_path: str | Path, client=None) -> list[dict]:
    client = client or _client()
    data = base64.standard_b64encode(Path(pdf_path).read_bytes()).decode()

    with client.messages.stream(
        model=MODEL,
        max_tokens=32000,
        thinking={"type": "adaptive"},
        output_config={
            "effort": "high",
            "format": {"type": "json_schema", "schema": OUTPUT_SCHEMA},
        },
        system=[{"type": "text", "text": SYSTEM, "cache_control": {"type": "ephemeral"}}],
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": data,
                        },
                    },
                    {"type": "text", "text": USER},
                ],
            }
        ],
    ) as stream:
        message = stream.get_final_message()

    text = next((b.text for b in message.content if b.type == "text"), "{}")
    return json.loads(text).get("samples", [])


def extract_records_from_text(text: str, client=None) -> list[dict]:
    import anthropic

    client = client or anthropic.Anthropic(max_retries=8)
    with client.messages.stream(
        model=MODEL,
        max_tokens=16000,
        thinking={"type": "adaptive"},
        output_config={
            "effort": "medium",
            "format": {"type": "json_schema", "schema": OUTPUT_SCHEMA},
        },
        system=[{"type": "text", "text": SYSTEM, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": f"{USER}\n\nArticle text:\n{text}"}],
    ) as stream:
        message = stream.get_final_message()
    out = next((b.text for b in message.content if b.type == "text"), "{}")
    return json.loads(out).get("samples", [])
