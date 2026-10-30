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
import re
from pathlib import Path

import anthropic
import nb
from dotenv import load_dotenv
from PIL import Image, ImageOps

MODEL = "claude-haiku-5-5"
QUESTION = "What is wrong with my plant?"

# Web search (server-side tool, --search). The evaluation threads are solved Reddit posts, so Reddit, its image and
# preview hosts, and the sites that mirror or archive Reddit threads never appear in results (subdomains included).
BLOCKED_DOMAINS = ["reddit.com", "redd.it", "redditmedia.com", "redditstatic.com", "reddithelp.com",
                   "reveddit.com", "unddit.com", "removeddit.com", "camas.unddit.com", "pullpush.io", "pushshift.io",
                   "arctic-shift.photon-reddit.com", "redditsearch.io", "teddit.net", "libreddit.net", "redlib.net",
                   "safereddit.com", "redditmirror.com", "archive.org", "archive.ph", "archive.today", "archive.is"]
SEARCH_TOOL = {"type": "web_search_20250305", "name": "web_search", "max_uses": 3, "blocked_domains": BLOCKED_DOMAINS}
SEARCH_NOTES = {"always": """You can search the web (up to 3 searches). Before answering, search for the plant and the symptoms you see
to check your diagnosis and the fix against reliable sources (extension services, botanical gardens, plant-care guides).
Reddit is not available.""",
                "unsure": """You can search the web (up to 3 searches), but only do so if you are unsure of the cause or the fix after
looking at the photos and the post; then search for the plant and the symptoms in reliable sources (extension services,
botanical gardens, plant-care guides). Reddit is not available.""",
                "research": """You can search the web (up to 5 searches); use it. Identify the plant first, then look up what it needs (light,
water, soil, humidity, temperature) and the problems it commonly gets. Search for every cause that could fit what you see
and what the poster says, not only your first guess, and look up how each is cured. Prefer reliable sources (extension
services, botanical gardens, plant-care guides). Reddit is not available."""}

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

# System prompts. "plain" sends none (the first version); "guided" tells the model how to reason and answer.
SYSTEM_PROMPTS = {
    "plain": None,
    "guided": """You are an experienced houseplant doctor answering a post on a plant-help forum. The poster wants to know
what is wrong and what to do.

How to work it out:
1. Look closely at the photos and read the post: which plant, which leaves are affected (old or new, tips, edges, the
   whole plant), texture (crispy and dry, or soft and mushy), the soil and pot, the light, recent changes (repotting,
   moving, season, travel), and anything the poster says about watering.
2. Over- and underwatering look alike (drooping, yellowing), so decide from evidence:
   - underwatering: dry or shrunken soil pulling away from the pot, crispy or curled leaves, a light pot, droop that
     recovers after watering, long gaps between waterings;
   - overwatering or root rot: soil that stays wet, soft or black stems, mushy roots, a smell, no drainage hole, a big
     pot or dense soil, frequent watering.
   If the evidence does not decide, say which quick check does (finger in the soil, lifting the pot, looking at the
   roots) and what to do in each case. Never tell the poster to water less unless the soil really stays wet.
3. Light: leggy or leaning growth and small new leaves mean too little light; bleached or crispy patches on the
   sun-facing side mean too much.
4. Pests: look for webbing, stippling, silvery patches, cottony tufts, bumps on stems, sticky residue or tiny insects,
   and name the pest if you can see it.

How to answer:
- Start with the single most likely cause, stated plainly. Then at most two other possibilities, each with what would
  tell it apart.
- Then the fix: the 2 to 4 most important steps, most important first, specific enough to follow (how, how much, how
  often).
- Be concise: about 250 words, no preamble.""",
    "guided-v2": """You are an experienced houseplant doctor answering a post on a plant-help forum. The poster wants to know
what is wrong and what to do.

How to work it out:
1. Look closely at the photos and read the post: which plant, which leaves are affected (old or new, tips, edges, the
   whole plant), texture (crispy and dry, or soft and mushy), the soil and pot, the light, recent changes (repotting,
   moving, season, travel), and anything the poster says about watering.
2. Over- and underwatering look alike (drooping, yellowing), so decide from evidence:
   - underwatering: dry or shrunken soil pulling away from the pot, crispy or curled leaves, a light pot, droop that
     recovers after watering, long gaps between waterings;
   - overwatering or root rot: soil that stays wet, soft or black stems, mushy roots, a smell, no drainage hole, a big
     pot or dense soil, frequent watering.
   If the evidence does not decide, say which quick check does (finger in the soil, lifting the pot, looking at the
   roots) and what to do in each case. Never tell the poster to water less unless the soil really stays wet.
3. Light: leggy or leaning growth and small new leaves mean too little light; bleached or crispy patches on the
   sun-facing side mean too much.
4. Pests: look for webbing, stippling, silvery patches, cottony tufts, bumps on stems, sticky residue or tiny insects,
   and name the pest if you can see it.
5. Also consider: low humidity (crispy edges, curling on calatheas, ferns and other humidity lovers), cold or drafts,
   root-bound or poorly draining soil, nutrient shortage, and physical damage (ties, bands or wires cutting into stems,
   breaks, pets).
6. It may be normal. One old lower leaf yellowing while new growth looks fine, spent flowers dying off, or a plant
   adjusting after a move is often not a problem. Say so when the rest of the plant looks healthy.
7. Weigh what the poster tells you (how often they water, the pot, the soil, where the plant sits) as heavily as the
   photos. Do not dismiss a cause their details point to.

How to answer:
- Start with the single most likely cause, stated plainly. Then at most two other possibilities, each with what would
  tell it apart. If two causes are about equally likely, say so and give the check that decides, instead of guessing.
- Then the fix: the 2 to 4 most important steps, most important first, specific enough to follow (how, how much, how
  often).
- Be concise: about 250 words, no preamble.""",
}

# Elements added to guided-v2 one at a time ("guided-v2+kb", "guided-v2+kb+format", ...; see system_prompt). Written from
# general houseplant-care knowledge, without reading the evaluation threads.
V2_REASONING, _, V2_ANSWER = SYSTEM_PROMPTS["guided-v2"].partition("How to answer:")
V2_ANSWER = "How to answer:" + V2_ANSWER
ELEMENTS = {
    # generic care cheat sheet: needs of common houseplant groups, symptom -> likely causes, standard fixes
    "kb": """Reference notes on common houseplants (general knowledge; use them when they fit what you see):
- Cacti and succulents (aloe, jade, echeveria, haworthia, string-of-pearls): bright light with some direct sun; water
  deeply only when the soil is fully dry; rot from wet soil is the main killer; stretched, pale growth means too little
  light; wrinkled or shrivelled leaves mean thirst if the soil is dry, root loss if it is wet.
- Snake plant, ZZ plant: tolerate low light and drought; soft, mushy or collapsing leaves almost always mean overwatering.
- Pothos, philodendron, monstera and other aroids: bright indirect light; water when the top few cm are dry; yellow lower
  leaves with wet soil mean overwatering, crispy brown edges with dry soil mean underwatering; need support to climb.
- Calathea, maranta, ferns, fittonia: evenly moist soil and high humidity; brown tips and curling come from dry air,
  drying out, or minerals in tap water; fittonia and peace lily wilt dramatically when dry and recover within hours.
- Ficus (fiddle-leaf fig, rubber plant, weeping fig): drop leaves after moves, drafts or cold; brown patches mid-leaf
  often mean root problems from wet soil; crispy edges mean dry soil or air.
- Orchids (phalaenopsis): in bark, watered when the roots turn silvery; no water left in the crown; limp, wrinkled
  leaves mean the roots are dead or dry.
- Alocasia: may go dormant and lose leaves in winter; prone to spider mites.
- Herbs, citrus, tomatoes, peppers and other edibles: need much more light than houseplants (full sun or a strong grow
  light) and regular feeding; leggy growth means too little light; young plants often drop flowers or fruit.
- In winter most plants grow slowly and need water less often; a plant moved to a new spot often drops a few leaves.

Common symptoms and their usual causes:
- Yellowing lower leaves: overwatering if the soil stays wet; underwatering if dry and crispy; normal ageing if only one
  or two old leaves while new growth is healthy; nitrogen shortage if the whole plant pales slowly.
- Brown crispy tips or edges: dry air, irregular watering, or salt and fertilizer build-up (white crust on soil or pot).
- Soft, dark, mushy stems or roots, a sour smell: root or stem rot from wet soil.
- Pale, stretched, leaning growth and small new leaves: too little light.
- Bleached, papery or brown patches on the side facing the window: sunburn, often after a move to brighter light.
- Fine speckling and webbing: spider mites. Silvery streaks with tiny black dots: thrips. White cottony tufts: mealybugs.
  Brown or tan bumps that scrape off, sticky leaves: scale. Clusters of small soft insects on new growth: aphids. Small
  flies around the soil: fungus gnats (from constantly wet soil; harmless to most plants).
- Sudden leaf drop or dark, water-soaked leaves after a cold night, a draft or transport: cold or shock.
- Roots circling the pot or growing out of the drainage holes, soil that dries in a day: root-bound.

Standard fixes:
- Root rot: unpot, cut off soft brown roots, repot in fresh, airy mix in a pot with drainage that is only slightly larger
  than the root ball, then water only when the top of the soil is dry.
- Pests: isolate the plant; rinse or wipe the leaves; spray insecticidal soap or neem on all surfaces every 5-7 days for
  3-4 rounds (eggs hatch between treatments); systemic granules or predatory mites for persistent thrips or scale;
  sticky traps and letting the soil dry (or BTi) for fungus gnats.
- Watering: water thoroughly until it drains, empty the saucer, and water again only when the plant's rule above says.
- Light: move closer to a window or add a grow light; acclimate over a week or two before full sun.""",
    # rough base rates of causes, to prefer common explanations
    "priors": """What is usually wrong: on houseplant help forums the real cause is most often a watering problem (overwatering in
dense soil or pots without drainage; underwatering in small, terracotta or sunny pots), then too little light, then
pests, then normal ageing or adjustment after a move, then dry air, a root-bound plant, sunburn or cold. Leaf diseases
from fungi or bacteria are much less common indoors than outdoors. Prefer a common cause unless the evidence points
elsewhere.""",
    # answer what was actually asked
    "question": """Some posts ask something other than what is wrong: how to get bushier growth, more flowers or fruit, when or how to
repot, how to support or propagate a plant, or whether it is dead. Answer the question the poster asks, directly, even
when nothing is wrong with the plant.""",
    # explicit differential before answering
    "differential": """Before you write the answer, think through the 3 most plausible causes and, for each, which details of the photos
and the post support or contradict it. Choose the one that best explains all the details. Do not show this list.""",
    # light format change: the fix comes first
    "lead": """Begin the answer with one sentence that says what to do first, before explaining the cause.""",
    # shorter answer (replaces "about 250 words" in the answer part)
    "short": None,
    # strict answer format; replaces the "How to answer" part
    "format": """How to answer, in exactly this format and nothing else (at most 180 words):
**Most likely cause:** one or two sentences.
**Do this first:** the single action most likely to fix it, specific (how, how much, how often).
**Then:** at most 3 more short actions, one line each; include the check that confirms the cause if it is uncertain.
**If that's not it:** at most 2 other causes, one line each, with the sign that points to them.""",
    # the evaluation's desiderata (eval_methodology.md): right cause, safe, no false alarm, at most 4 short actions;
    # replaces the "How to answer" part
    "limits": """How to answer:
- Start with the single most likely cause, stated plainly. If two causes are about equally likely, name both and make
  the first action the quick check that decides between them.
- If the plant looks healthy, or the change is normal (an old leaf dying, spent flowers, adjusting after a move), say so
  clearly and recommend no treatment. Do not invent a problem.
- Then the fix: at most 4 actions in total. Every task the owner must do counts as one action, including checks,
  "if ... then ..." steps and alternatives, so do not offer backup plans or extra options. Things to stop doing, or to
  keep doing, do not count. Number the actions and give no other advice outside that list.
- Each action must be short: under 15 minutes of work on any one day, and at most $15 beyond household supplies (water,
  scissors, dish soap, rubbing alcohol, cotton swabs, plastic bags). Name the product, the amount, how long it takes and
  how often, so the owner knows exactly what to do. A daily task counts its total minutes per day.
- Recommend a longer or riskier job (repotting, cutting roots, removing much of the plant, a pesticide) only when the
  photos or the post clearly show it is needed, and never as a precaution.
- Be safe: never advise watering more or less without first checking the soil, never combine treatments that should
  not be mixed, and never reassure the owner about a problem that needs action now (pests, rot).
- Be concise: at most 200 words, no preamble.""",
}


def system_prompt(name):
    """"plain", "guided", "guided-v2", or "guided-v2+<element>+<element>..." (elements of ELEMENTS, in the given order)."""
    base, *elements = name.split("+")
    if not elements:
        return SYSTEM_PROMPTS[name]
    assert base == "guided-v2" and all(e in ELEMENTS or re.fullmatch(r"drop[1-7]", e) for e in elements), name
    reasoning = V2_REASONING
    for e in elements:  # drop<k>: remove item k of the "How to work it out" list
        if e.startswith("drop"):
            k = int(e[4:])
            reasoning = re.sub(rf"\n{k}\. .*?(?=\n\d\. |\n\n|$)", "", reasoning, flags=re.S)
    replaces = ("format", "limits")  # elements that replace the "How to answer" part
    middle = [ELEMENTS[e] for e in elements if e not in replaces + ("short",) and not e.startswith("drop")]
    answer = next((ELEMENTS[e] for e in elements if e in replaces), V2_ANSWER)
    if "short" in elements:
        answer = answer.replace("about 250 words", "at most 150 words")
    return "\n\n".join([reasoning.rstrip()] + middle + [answer])


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


def search_tool(model, search):
    """Haiku gets the basic tool; larger models the version that filters results with code (fewer tokens)."""
    tool = dict(SEARCH_TOOL, max_uses=5 if search == "research" else 3)
    return tool if "haiku" in model else dict(tool, type="web_search_20260209")


def ask(client, images, prompt, model=MODEL, system=None, search=False, effort="medium"):
    """Returns (answer, last response, usage summed over calls, searches: [{query, results: [{url, title}]}]).
    search: False, or a key of SEARCH_NOTES ("always" if True)."""
    # Opus / Sonnet: if a safety classifier declines the request, it is retried on a fallback model (Haiku has no fallback)
    extra = {} if "haiku" in model else dict(betas=["server-side-fallback-2026-07-01"], fallbacks="default")
    messages = [{"role": "user", "content": [image_block(p) for p in images] + [{"type": "text", "text": prompt}]}]
    if search:
        note = SEARCH_NOTES["always" if search is True else search]
        system = note if not system else system + "\n\n" + note
    content, usage = [], {"input_tokens": 0, "output_tokens": 0, "web_search_requests": 0}
    for _ in range(5):  # a long server-side search turn stops with "pause_turn"; sending it back resumes it
        # streamed, since a long max-effort answer can exceed the time allowed for a single non-streamed request
        with (client.beta.messages if extra else client.messages).stream(
            model=model,
            max_tokens=64000 if effort == "max" else 16000,  # max effort can think past 16k tokens and return nothing
            output_config={"effort": effort},
            **extra,
            **({"system": system} if system else {}),
            **({"tools": [search_tool(model, search)]} if search else {}),
            messages=messages,
        ) as stream:
            response = stream.get_final_message()
        content += response.content
        usage["input_tokens"] += response.usage.input_tokens
        usage["output_tokens"] += response.usage.output_tokens
        stu = getattr(response.usage, "server_tool_use", None)
        usage["web_search_requests"] += (stu.web_search_requests or 0) if stu else 0
        if response.stop_reason != "pause_turn":
            break
        messages = messages[:1] + [{"role": "assistant", "content": content}]
    results = {b.tool_use_id: b.content for b in content if b.type == "web_search_tool_result"}
    searches = [{"query": b.input.get("query"), "results": (
                    [{"url": x.url, "title": x.title} for x in results[b.id]] if isinstance(results.get(b.id), list)
                    else [{"error": getattr(results.get(b.id), "error_code", "no result")}])}
                for b in {b.id: b for b in content if b.type == "server_tool_use" and b.name == "web_search"}.values()]
    if response.stop_reason == "refusal":
        return f"[declined: {response.stop_details.category if response.stop_details else 'unknown'}]", response, usage, searches
    # the answer is the text after the last search result (text before it is the model announcing its searches)
    last = max([i for i, b in enumerate(content) if b.type == "web_search_tool_result"], default=-1)
    return "".join(b.text for b in content[last + 1:] if b.type == "text"), response, usage, searches


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--image", action="append", required=True, help="repeat for several photos")
    p.add_argument("--title", default="")
    p.add_argument("--body", default="")
    p.add_argument("--mode", choices=["llm", "llm+classifier", "both"], default="both")
    p.add_argument("--head", default="results/all-224px/head.npz", help="classifier used by option 2")
    p.add_argument("--prompt", default="plain", help="system prompt: plain, guided, guided-v2 or guided-v2+<element>...")
    p.add_argument("--model", default=MODEL, help="e.g. claude-opus-5-5 (default: the cheap Haiku)")
    p.add_argument("--search", action="store_true", nargs="?", const="always", default=False,
                   help="let the model search the web (Reddit and its mirrors blocked): always (default) or unsure")
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
        answer, response, usage, searches = ask(client, args.image, prompt, args.model, system_prompt(args.prompt), args.search)
        record["answers"][mode] = {"prompt": prompt, "answer": answer, "served_by": response.model, **usage, "searches": searches}
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
