"""Ask Claude what is wrong with a plant, from a Reddit-style post: photo(s) + title + body text.

    python diagnose.py --image photo.jpg --title "SOS" --body "Leaves went black overnight..."            # both options
    python diagnose.py --image a.jpg --image b.jpg --title "..." --body "..." --mode llm                    # option 1 only
    python diagnose.py ... --mode llm+classifier --out results/llm/case1.json                               # option 2, saved

Option 1 (`llm`): the photos, the post and the question are sent to Claude.
Option 2 (`llm+classifier`): the same, plus the DINOv2 classifier's probabilities for each photo, with the list of its
5 classes and a warning that it is often wrong. The API key is read from ANTHROPIC_API_KEY or from the file .env
(one line: ANTHROPIC_API_KEY=sk-ant-...), which git ignores.
"""

import argparse
import base64
import io
import json
import os
from pathlib import Path

import anthropic
import nb
from dotenv import load_dotenv
from PIL import Image, ImageOps

MODEL = "claude-haiku-5-5"
QUESTION = "What is wrong with my plant?"

CLASSIFIER_NOTE = """An automatic image classifier was also run on each photo. It only knows 5 classes:
- healthy: no visible problem
- watering: wilting or withering from too little or too much water
- fungal_bacterial: leaf spots, rust, anthracnose, blight, rot, bacterial wilt
- pest: visible insects or mites (trained almost only on cochineal scale on cactus)
- other: anything else, e.g. sunburn, nutrient or mineral problems, viruses, leaf tip necrosis, cold damage

The classifier is not perfect. It was trained mostly on curated dataset photos, not on phone photos like these,
and on such photos it is often wrong while still reporting a very high probability. Treat it as one weak hint:
rely on what you see in the photos and on the post first.

Classifier output (probability of each class):
{outputs}"""


def image_block(path, max_side=1568):
    """Photo as the phone shows it (EXIF rotation applied), longest side at most 1568 px, sent as JPEG."""
    img = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
    img.thumbnail((max_side, max_side))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                        "data": base64.standard_b64encode(buf.getvalue()).decode()}}


def classifier_outputs(head, images):
    from predict import probabilities  # loads DINOv2 only when option 2 is used
    labels, prob = probabilities(head, images)
    lines = []
    for i, row in enumerate(prob, 1):
        ranked = sorted(zip(labels, row), key=lambda x: -x[1])
        lines.append(f"Photo {i}: " + ", ".join(f"{l} {p:.0%}" for l, p in ranked))
    return "\n".join(lines)


@nb.core
def build_prompt(title, body, classifier=None):
    text = f"Reddit post, r/houseplants.\nTitle: {title}\n\n{body}".rstrip()
    if classifier is not None:
        text += "\n\n" + CLASSIFIER_NOTE.format(outputs=classifier)
    return text + "\n\n" + QUESTION


def ask(client, images, prompt, model=MODEL):
    # Opus / Sonnet: if a safety classifier declines the request, it is retried on a fallback model (Haiku has no fallback)
    extra = {} if "haiku" in model else dict(betas=["server-side-fallback-2026-07-01"], fallbacks="default")
    response = (client.beta.messages if extra else client.messages).create(
        model=model,
        max_tokens=16000,
        output_config={"effort": "medium"},
        **extra,
        messages=[{"role": "user", "content": [image_block(p) for p in images] + [{"type": "text", "text": prompt}]}],
    )
    if response.stop_reason == "refusal":
        return f"[declined: {response.stop_details.category if response.stop_details else 'unknown'}]", response
    return "".join(b.text for b in response.content if b.type == "text"), response


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--image", action="append", required=True, help="repeat for several photos")
    p.add_argument("--title", default="")
    p.add_argument("--body", default="")
    p.add_argument("--mode", choices=["llm", "llm+classifier", "both"], default="both")
    p.add_argument("--head", default="results/all-224px/head.npz", help="classifier used by option 2")
    p.add_argument("--model", default=MODEL, help="e.g. claude-opus-5-5 (default: the cheap Haiku)")
    p.add_argument("--out", help="save prompts and answers to this JSON file")
    p.add_argument("--dry_run", action="store_true", help="print the prompts without calling the API")
    args = p.parse_args()

    load_dotenv(Path(__file__).parent / ".env")
    if not args.dry_run and not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("No API key: put ANTHROPIC_API_KEY=sk-ant-... in .env (see the README).")
    client = None if args.dry_run else anthropic.Anthropic()

    modes = ["llm", "llm+classifier"] if args.mode == "both" else [args.mode]
    record = {"images": args.image, "title": args.title, "body": args.body, "model": args.model, "answers": {}}
    for mode in modes:
        cls = classifier_outputs(args.head, args.image) if mode == "llm+classifier" else None
        prompt = build_prompt(args.title, args.body, cls)
        if args.dry_run:
            print(f"===== {mode} prompt ({len(args.image)} photo(s) attached) =====\n{prompt}\n")
            continue
        answer, response = ask(client, args.image, prompt, args.model)
        record["answers"][mode] = {"prompt": prompt, "answer": answer, "served_by": response.model,
                                   "input_tokens": response.usage.input_tokens, "output_tokens": response.usage.output_tokens}
        print(f"===== {mode} =====")
        if cls is not None:
            print(f"[classifier] {cls}\n")
        print(answer, "\n", flush=True)

    if args.out:
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        json.dump(record, open(args.out, "w"), indent=2)
        print(f"saved {args.out}")


if __name__ == "__main__":
    main()
