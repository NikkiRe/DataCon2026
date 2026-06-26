import json
import re
import os
import anthropic
from pathlib import Path
from dotenv import load_dotenv

from .pdf_parser import pdf_to_markdown, image_to_base64
from .smiles_lookup import enrich_smiles

load_dotenv()

EXTRACT_MODEL = "claude-sonnet-4-6"
VERIFY_MODEL = "claude-opus-4-8"
DESCRIBE_MODEL = "claude-haiku-4-5-20251001"

IMAGE_DESCRIBE_PROMPT = (
    "Describe all chemical structures, tables, and data visible in this image. "
    "Include molecule names, SMILES if shown, numerical values, units, and any labels. "
    "Be precise and complete."
)


def _client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


def describe_images(image_paths: list[str]) -> dict[str, str]:
    """Return {image_path: description} for each image. All images in one API call."""
    if not image_paths:
        return {}
    client = _client()

    content = []
    for i, path in enumerate(image_paths):
        ext = Path(path).suffix.lower().lstrip(".")
        media_type = f"image/{'jpeg' if ext == 'jpg' else ext}"
        content.append({"type": "text", "text": f"Image {i+1} ({Path(path).name}):"})
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": image_to_base64(path),
            },
        })

    content.append({
        "type": "text",
        "text": (
            "For each image above, describe all chemical structures, tables, and data visible. "
            "Include molecule names, SMILES if shown, numerical values, units, and labels. "
            "Format your response as:\nImage 1: <description>\nImage 2: <description>\netc."
        ),
    })

    resp = client.messages.create(
        model=DESCRIBE_MODEL,
        max_tokens=2048,
        messages=[{"role": "user", "content": content}],
    )
    raw = resp.content[0].text

    descriptions = {}
    for i, path in enumerate(image_paths):
        marker = f"Image {i+1}:"
        next_marker = f"Image {i+2}:"
        start = raw.find(marker)
        end = raw.find(next_marker) if next_marker in raw else len(raw)
        if start != -1:
            descriptions[path] = raw[start + len(marker):end].strip()
        else:
            descriptions[path] = ""
    return descriptions


def inject_descriptions(markdown: str, descriptions: dict[str, str]) -> str:
    """Replace image references in markdown with their descriptions."""
    result = markdown
    for path, desc in descriptions.items():
        filename = Path(path).name
        tag = f"<DESCRIPTION_FROM_IMAGE>\n{desc}\n</DESCRIPTION_FROM_IMAGE>"
        result = result.replace(f"![]({filename})", tag)
        result = result.replace(f"![](./{filename})", tag)
    return result


def extract_json(text: str) -> list[dict]:
    """Extract JSON array from model response."""
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if match:
        return json.loads(match.group())
    return json.loads(text)


def extract_from_markdown(markdown: str, domain) -> list[dict]:
    """Run extraction LLM on described markdown."""
    client = _client()
    prompt = domain.build_prompt(markdown)
    resp = client.messages.create(
        model=EXTRACT_MODEL,
        max_tokens=4096,
        system=domain.system_prompt,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = resp.content[0].text
    try:
        return extract_json(raw)
    except Exception:
        return []


def verify_records(records: list[dict], domain, markdown: str) -> list[dict]:
    """Second-pass: ask model to verify and fix extracted records."""
    if not records:
        return records
    client = _client()
    prompt = f"""You extracted these records from a chemistry paper:

{json.dumps(records, indent=2, ensure_ascii=False)}

Check each record against the paper text below and fix any errors:
- Correct chemical names, ratios, and photostability values
- photostability_change MUST be one of: "increases", "decreases", "does not change"
- Remove duplicate records
- Return the corrected JSON array only.

--- PAPER START ---
{markdown[:4000]}
--- PAPER END ---

Corrected JSON array:"""

    resp = client.messages.create(
        model=VERIFY_MODEL,
        max_tokens=4096,
        system=domain.system_prompt,
        messages=[{"role": "user", "content": prompt}],
    )
    try:
        return extract_json(resp.content[0].text)
    except Exception:
        return records


def run_pipeline(pdf_path: str, domain, work_dir: str = "/tmp/chemx_work") -> list[dict]:
    """Full pipeline: PDF → extracted + enriched records."""
    print(f"[1/5] Parsing PDF: {pdf_path}")
    markdown, image_paths = pdf_to_markdown(pdf_path, work_dir)

    print(f"[2/5] Describing {len(image_paths)} images...")
    descriptions = describe_images(image_paths)

    print("[3/5] Injecting image descriptions...")
    described_md = inject_descriptions(markdown, descriptions)

    print("[4/5] Extracting structured data...")
    records = extract_from_markdown(described_md, domain)

    print("[5/5] Verifying and enriching SMILES...")
    records = verify_records(records, domain, described_md)
    for name_field, smiles_field in domain.smiles_pairs:
        records = enrich_smiles(records, name_field, smiles_field)

    return records
