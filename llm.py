"""Gemini client for zero-shot classification of the Indoor Plant Disease Detection dataset (16 native classes)."""

import os
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

load_dotenv()

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")

# The 16 native classes of the Indoor Plant Disease Detection dataset, with a plain description of each name.
CLASSES = {
    "Aloe_Healthy": "aloe vera, no visible problem",
    "Aloe_Anthracnose": "aloe vera with anthracnose",
    "Aloe_LeafSpot": "aloe vera with leaf spot",
    "Aloe_Rust": "aloe vera with rust",
    "Aloe_Sunburn": "aloe vera with sunburn",
    "Cactus_Healthy": "cactus, no visible problem",
    "Cactus_Dactylopius_Opuntia": "cactus infested by Dactylopius opuntiae (cochineal scale insect)",
    "Money_Plant_Healthy": "money plant (pothos), no visible problem",
    "Money_Plant_Bacterial_wilt_disease": "money plant (pothos) with bacterial wilt",
    "Money_Plant_Manganese_Toxicity": "money plant (pothos) with manganese toxicity",
    "Snake_Plant_Healthy": "snake plant, no visible problem",
    "Snake_Plant_Anthracnose": "snake plant with anthracnose",
    "Snake_Plant_Leaf_Withering": "snake plant with leaf withering",
    "Spider_Plant_Healthy": "spider plant, no visible problem",
    "Spider_Plant_Fungal_leaf_spot": "spider plant with fungal leaf spot",
    "Spider_Plant_Leaf_Tip_Necrosis": "spider plant with leaf tip necrosis",
}
LABELS = list(CLASSES)

PROMPT = "You are a plant health expert. Look at the photo, identify the plant and its condition, and answer with exactly one class:\n" + "\n".join(
    f"- {k}: {v}" for k, v in CLASSES.items())

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
