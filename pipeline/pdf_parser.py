import os
import base64
from pathlib import Path
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.output import text_from_rendered


def pdf_to_markdown(pdf_path: str, output_dir: str) -> tuple[str, list[str]]:
    """Convert PDF to markdown with image paths. Returns (markdown_text, image_paths)."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    converter = PdfConverter(artifact_dict=create_model_dict())
    rendered = converter(pdf_path)
    text, _, images = text_from_rendered(rendered)

    image_paths = []
    for img_name, img in images.items():
        img_path = output_dir / img_name
        img.save(str(img_path))
        image_paths.append(str(img_path))

    md_path = output_dir / "converted.md"
    md_path.write_text(text, encoding="utf-8")

    return text, image_paths


def image_to_base64(image_path: str) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")
