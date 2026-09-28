"""Gemini client for zero-shot plant-condition classification (free tier via Google AI Studio key)."""

import os
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

load_dotenv()

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")

LABELS = ["healthy", "watering", "fungal_bacterial", "pest", "other"]

PROMPT = """You are a plant health expert. Look at the photo of a plant and classify its main condition.
Answer with exactly one label:
- healthy: no visible problem.
- watering: wilting, drooping, withering or collapse caused by too little or too much water.
- fungal_bacterial: spots, lesions, rust, mildew, rot, blight or wilt caused by a fungus or bacterium.
- pest: insects, mites, scale or other animals on or damaging the plant.
- other: any other problem (sunburn, nutrient deficiency or toxicity, salt/fluoride tip burn, virus, physiological disorder)."""

MIME = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}

_client = None


def client():
    global _client
    if _client is None:
        if not os.getenv("GEMINI_API_KEY"):
            raise SystemExit("GEMINI_API_KEY is not set: copy .env.example to .env and paste your key.")
        _client = genai.Client()
    return _client


def classify(image_path, model=MODEL, retries=5):
    """Return one label from LABELS for the image at image_path."""
    path = Path(image_path)
    image = types.Part.from_bytes(data=path.read_bytes(), mime_type=MIME[path.suffix.lower()])
    config = types.GenerateContentConfig(
        temperature=0,
        response_mime_type="text/x.enum",
        response_schema={"type": "STRING", "enum": LABELS},
    )
    for attempt in range(retries):
        try:
            r = client().models.generate_content(model=model, contents=[image, PROMPT], config=config)
            return r.text.strip()
        except errors.APIError as e:
            if e.code in (429, 500, 503) and attempt < retries - 1:
                time.sleep(2 ** attempt * 10)  # rate limit or overload: back off 10s, 20s, 40s, ...
                continue
            raise
