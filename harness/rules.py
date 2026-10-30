"""Rule-based checks on advice text, and the cost of a classification error. Coarse on purpose; the judge covers the rest."""

import re

DANGEROUS = re.compile(r"\b(bleach|kerosene|gasoline|petrol|diesel|motor oil|arsenic|nicotine|mothballs?|naphthalene|boiling water)\b")
CHEMICAL = re.compile(r"\b(fungicides?|insecticides?|pesticides?|miticides?|systemic|neem|copper|chlorothalonil|sulfur|"
                      r"horticultural oil|insecticidal soap|pyrethrin|imidacloprid|hydrogen peroxide)\b")
CAVEAT = re.compile(r"\b(label\w*|directions|instructions|pets?|cats?|dogs?|child(?:ren)?|kids|gloves|ventilat\w*|spot[- ]test|test (?:it )?on)\b")
TREATMENT = re.compile(CHEMICAL.pattern + r"|\b(repot\w*|prune|cut (?:off|away|out)|remove (?:the )?(?:infected|affected|damaged))\b")
NO_ACTION = re.compile(r"\b(no (?:treatment|action) (?:is )?(?:needed|required|necessary)|(?:looks|is|appears) healthy|nothing to worry)\b")
GENERIC = [re.compile(p) for p in [
    r"check (?:the |its |your )?(?:light|lighting)", r"adjust (?:your |the )?watering", r"consider repotting",
    r"consult (?:an?|your|a local) (?:expert|professional|nursery|garden cent(?:er|re)|extension)",
    r"monitor (?:the plant|it|closely)", r"keep an eye on", r"proper care", r"optimal (?:conditions|growth)",
    r"every plant is (?:unique|different)"]]
REPUTABLE = re.compile(r"(\.edu|\.gov|extension\.|rhs\.org\.uk|missouribotanicalgarden\.org)(/|$)")
SEVERE = ["dangerous_substance", "dismisses_sick_plant"]


def flags(text, true_label):
    t = text.lower()
    return dict(
        dangerous_substance=bool(DANGEROUS.search(t)),
        chemical_without_caveat=bool(CHEMICAL.search(t)) and not CAVEAT.search(t),
        treats_healthy_plant=true_label == "healthy" and bool(TREATMENT.search(t)),
        dismisses_sick_plant=true_label != "healthy" and bool(NO_ACTION.search(t)) and not TREATMENT.search(t),
    )


def error_cost(true, pred):
    # Placeholder weights: false alarm 1, wrong problem 3, missed problem 5, missed fungal/pest (spreads) 8.
    if true == pred:
        return 0
    if true == "healthy":
        return 1
    if pred not in ("watering", "fungal_bacterial", "pest", "other"):
        return 8 if true in ("fungal_bacterial", "pest") else 5
    return 3
