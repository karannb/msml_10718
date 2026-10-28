# Where the classifier made Claude worse

Resolved Reddit threads (n=96) where `llm+classifier` is worse than `llm` on at least one of covered, harmful, diagnosis rank or advice rank, and better on none (Opus grades). "Helped" is the mirror image; "mixed" is better on one field and worse on another.
Sonnet 5.5: hurt 25 / helped 10 / unchanged 61. Haiku 5.5: hurt 15 / helped 28 / unchanged 51 / mixed 2.

## Sonnet 5.5

| thread_id | confirmed problem | classifier top label per photo | without → with classifier | how the classifier misled it |
|---|---|---|---|---|
| 1gj7tyl | thrips/pest infestation (plus sun-change stress) | fungal_bacterial 79%; fungal_bacterial 86%; watering 98%; watering 71%; watering 89% | diag correct→partial, advice yes→partial, harm no→yes | rejects the labels ("don't fit well with what's visible"), yet bugs are "almost certainly not pests" |
| 1iv05sy | pest infestation (whiteflies or similar bugs) on foliage | watering 97%; healthy 51% | diag correct→partial, advice partial→no, harm no→yes | takes "watering" as support for spray burn over pests: "dry, papery leaves fit with it" |
| 1j4xrlk | cold damage after transport | watering 70% | harm no→yes | adds a water problem, demotes cold: "The classifier's "watering" guess is plausible" |
| 1wcn3vn | stunted growth from multiple money trees tangled together in one pot | watering 93%; watering 73%; healthy 54% | harm no→yes | rejects it ("probably a false alarm"); both answers miss the tangled trunks |
| 1gq3j1p | aphid infestation | other 75%; healthy 64% | diag partial→wrong, covered yes→no | rejects it ("wrong here"); drops aphids as an alternative |
| 1lic91x | plant not mature enough yet to set fruit | watering 93%; healthy 93%; watering 79% | diag partial→wrong, covered yes→no | rejects it ("doesn't match what I see"); promotes heat over immaturity |
| 1u3kg0t | leaf curling from low humidity | watering 100%; healthy 64% | diag partial→wrong, covered yes→no | rejects it ("I wouldn't trust that"); same cold diagnosis, humidity demoted |
| 1v3ncl2 | dehydration | watering 100% | diag partial→wrong, covered yes→no | picks overwatering over dehydration: "The classifier says "watering", which fits" |
| 1wc6ru0 | (blank; fix was giving the kalanchoe the most light) | healthy 98% | diag partial→wrong, covered yes→no | endorses healthy, misses light placement: "the classifier's "healthy" result matches what I see" |
| v4fond | spider mite infestation | watering 66%; watering 75%; watering 99% | diag partial→wrong, covered yes→no | no visible reliance |
| xv9lfg | new leaf stuck unfurling due to low humidity | fungal_bacterial 58% | diag partial→wrong, covered yes→no | rejects it ("I'd ignore that result"); same "normal unfurling" call |
| 1028vjv | leaf damage from dry air (low humidity) | healthy 90%; watering 77% | diag correct→partial | reframes via the class list, dry air drops to third: "fits the "other" category (leaf tip necrosis)" |
| 11a6rwi | thrips infestation | healthy 98% | diag correct→partial | thrips become one option among several: "The classifier says "healthy," and the leaf is mostly healthy" |
| 11p3i4r | underwatering / thirsty plant (dry soil), plus broken stems from the shower | watering 93%; watering 100%; watering 100% | diag correct→partial, advice yes→partial | no visible reliance (shifts to soggy roots) |
| 14m3jl5 | overgrown, woody basil needing pruning | healthy 60% | diag correct→partial | endorses healthy, woody stalk called normal: "The classifier's "healthy" call fits that" |
| 14m83n3 | leggy, pale growth from too little light and overwatering | watering 100%; watering 100% | advice yes→partial | backs underwatering over overwatering: "The classifier's "watering" result fits what I see" |
| 16w508b | thrips infestation (plus low light) | watering 95%; watering 84%; watering 95%; watering 92% | diag correct→partial, advice yes→partial | rejects it ("I'd put little weight on it"); thrips demoted below spray burn and roots |
| 17x3131 | oversized pot holding too much moisture (overwatering / risk of root rot) | watering 99%; watering 60%; watering 50%; watering 99%; watering 99% | advice yes→partial | no visible reliance |
| 1e712vo | root rot / low oxygen from topping off water instead of full changes, small container, no fertilizer | fungal_bacterial 99%; fungal_bacterial 90%; watering 90% | diag correct→partial | no visible reliance |
| 1is3mey | overwatering with too little light | watering 96%; watering 81%; watering 93%; watering 96%; watering 99% | diag correct→partial | backs underwatering over overwatering: "The classifier says "watering", and the wrinkling does fit" |
| 1jwevyi | winter-stressed azaleas, leaves reddish but still alive (not dead) | healthy 45% | advice yes→partial | endorses healthy, leads with waiting: "The classifier's split between "healthy" and "other" fits this" |
| 1kbiakb | damaged/browning leaf, likely water marks or sun stress; otherwise healthy | watering 78%; fungal_bacterial 52% | diag correct→partial, advice yes→partial | rejects it ("I'd discount the classifier's "watering" call"); mechanical damage ranked over sun |
| 1peuq1x | stress/decline after fertilizing in dense, poorly draining mix; needed a tighter pot and airy mix | fungal_bacterial 45%; fungal_bacterial 55% | advice partial→no | rejects it ("probably wrong"); the dense wet mix drops out of the causes |
| s2w0t1 | underwatering (shriveling stem, drooping leaves) | watering 70% | diag correct→partial, advice yes→partial | hedges toward overwatering: "The classifier said "watering", and I'd take that seriously" |
| wys5ze | needs repotting (rootbound/old soil) | watering 90%; healthy 73% | advice yes→partial | rejects it ("most likely wrong"), calls the plant healthy and repotting "not urgent" |

## Haiku 5.5

| thread_id | confirmed problem | classifier top label per photo | without → with classifier | how the classifier misled it |
|---|---|---|---|---|
| 152ww03 | trunk constricted by a rubber band/strapping at the base, blocking water flow | healthy 68% | harm no→yes | cites healthy 68% / watering 32% as "a weak hint", then leads with watering; both miss the band |
| 1ahvd93 | overwatering in a pot without drainage | healthy 69% | diag partial→wrong, harm no→yes, covered yes→no | dismisses the right signal: "Its "watering" score is a weak hint at best" |
| 1iv05sy | pest infestation (whiteflies or similar bugs) on foliage | watering 97%; healthy 51% | diag partial→wrong, advice partial→no, covered yes→no | "The classifier's "watering" call is plausible" → "not an active infestation" |
| 1khq8et | poorly supported, struggling monstera needing repot, light and proper staking | watering 100% | diag partial→wrong, covered yes→no | no visible reliance (leads with "a watering problem") |
| 1vd0t8d | healthy / normal: yellowing of oldest leaf | watering 72%; watering 88% | diag partial→wrong, covered yes→no | treats a normal plant as overwatered: "The classifier's "watering" call fits with this" |
| t7qa4k | browning older leaves, possible overwatering | watering 100% | diag partial→wrong, covered yes→no | rules out watering: "The classifier's "watering 100%" call is likely wrong here" |
| xv9lfg | new leaf stuck unfurling due to low humidity | fungal_bacterial 58% | diag partial→wrong, advice partial→no, covered yes→no | explains it away ("read those pale spots as leaf spot disease"); drops humidity |
| 1028vjv | leaf damage from dry air (low humidity) | healthy 90%; watering 77% | diag correct→partial | dry air becomes one of four causes: "I'd put it in the "other" category rather than "watering"" |
| 11a6rwi | thrips infestation | healthy 98% | advice partial→no | rejects it ("probably wrong"); drops the predatory mites |
| 11p3i4r | underwatering / thirsty plant (dry soil), plus broken stems from the shower | watering 93%; watering 100%; watering 100% | advice yes→partial | hedges between under- and overwatering: "The classifier's "watering" label fits the drooping" |
| 1d0z5km | wants fuller, bushier growth (healthy plant; flowering) | healthy 49%; healthy 78% | advice yes→partial | dismisses fungal_bacterial ("probably a false alarm"); drops repotting and feeding |
| 1lic91x | plant not mature enough yet to set fruit | watering 93%; healthy 93%; watering 79% | advice partial→no | rejects it ("doesn't match what I see"); drops "be patient" |
| 1peuq1x | stress/decline after fertilizing in dense, poorly draining mix; needed a tighter pot and airy mix | fungal_bacterial 45%; fungal_bacterial 55% | advice partial→no | rejects it ("nothing in the images clearly shows that"); still misses the dense mix |
| vrloag | acclimating a greenhouse-grown plant to full sun without sunburn | watering 58% | diag correct→partial | watering check comes before the sun plan: "The classifier's "watering" call is a weak signal" |
| wys5ze | needs repotting (rootbound/old soil) | watering 90%; healthy 73% | diag correct→partial | calls the label "weak evidence", leads with "Nothing looks seriously wrong" |

## Patterns

- Pest: all 14 pest threads get pest ≤1.4% on every photo. Sonnet is hurt on 6 of them (helped on 1), Haiku on 2 (helped on 3). In 2 of Sonnet's 4 harm-introduced rows (1gj7tyl, 1iv05sy) the answer talks itself out of the infestation.
- "watering" is the top label on at least one photo in 18/25 Sonnet and 9/15 Haiku hurt threads, close to the 74/96 base rate, so the label alone does not predict harm. It gives no direction: 4 of the 6 Sonnet answers that endorse it are on watering threads and pick or lean toward the wrong one (1v3ncl2, 1is3mey, 14m83n3, s2w0t1).
- Endorsing "healthy" (Sonnet: 1wc6ru0, 11a6rwi, 14m3jl5, 1jwevyi) turns a real problem into "nothing seriously wrong" or one option among several.
- Sonnet endorses the classifier in 11/25 hurt answers, rejects it in 10 and does not mention it in 4; Haiku 4/10/1. 8 threads are hurt for both models. Where the answer rejects or ignores the label, the drop does not trace to it, except Haiku 1ahvd93 and t7qa4k, which dismiss "watering" where the confirmed problem involves overwatering.
