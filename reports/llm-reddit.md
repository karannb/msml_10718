# Claude on Reddit plant photos, with and without the classifier: first look (3 cases)

`diagnose.py` sends a Reddit-style post (photo, title, body) to Claude with the question "What is wrong with my plant?":

- **without the classifier**: photo, post and question only;
- **with the classifier**: the same, plus the DINOv2 classifier's probabilities for the photo (4-dataset model, 224 px), its 5 classes, and a warning that it is often wrong and overconfident on phone photos.

Models: `claude-haiku-5-5` and `claude-opus-5-5`, effort medium. Only 3 of the 13 Reddit cases have photos here, and the post text was not available. So each run got the photo and the post title (taken from the URL) with an empty body. Full prompts and answers are in `results/llm/case<N>-<model>.json`.

## Reference answers

Taken from the Reddit threads (`data/reddit/cases.csv`):

| Case | Photo | Reddit reference |
|---|---|---|
| 1 | Fatsia with drooping leaves | cold exposure (confirmed by the poster) |
| 2 | snake plant off its roots | no confirmed cause: roots lost, rot suspected but not established |
| 4 | Monstera adansonii | no disease: commenters advised more light and a support to climb |

## Answers

| Case | Classifier output | Haiku | Haiku with classifier | Opus | Opus with classifier |
|---|---|---|---|---|---|
| 1 | watering 99% | low light; spots from sun, watering or dry air | watering, plus low light | wilting: check soil, probably thirst; mentions dry indoor air | watering, citing the classifier |
| 2 | healthy 68% | base rot from overwatering; cut, dry, repot | same; says the classifier's "healthy" is wrong | base rot; names cultivar 'Hahnii'; re-root as a cutting | same; says the classifier only sees the leaves |
| 4 | watering 99% | leggy from low light; loosen ties | same; says the 99% "watering" is wrong | low light; give it a moss pole to climb | low light, needs support, maybe slightly thirsty |

## What this shows (3 cases, so anecdotes only)

- **No run found the cold damage in case 1.** With only the title "SOS", nothing pointed to cold. With the classifier added, both models moved toward "watering", and Opus cited the classifier as support.
- **In cases 2 and 4, both models set aside the classifier when it was wrong** and gave the same answer as without it.
- **Opus matched the Reddit advice for case 4 best** (more light and a climbing support), and its answers are more specific than Haiku's. Opus costs about 40x more per call; one Haiku call here costs about $0.001.
- **A fair comparison needs more.** It needs the remaining cases, the real post text as input, and the threads' answers as reference.
