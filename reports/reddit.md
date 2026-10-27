# Reddit cases (phone photos, independent of all training data)

First image of each post; reference diagnosis from the Reddit thread (not expert-confirmed). Label = the reference mapped to the 5 pooled labels; blank when the thread establishes no cause.

Missing images (not scored): cases 3, 5, 6, 7, 8, 9, 10, 11, 12, H.

- All four datasets, 224 px: 0 / 1 cases with a label predicted correctly
- Indoor only, 224 px: 0 / 1 cases with a label predicted correctly
- All four datasets, 448 px: 0 / 1 cases with a label predicted correctly
- Indoor only, 448 px: 0 / 1 cases with a label predicted correctly

|   case | reference                                    | label   | All four datasets, 224 px       | Indoor only, 224 px          | All four datasets, 448 px                | Indoor only, 448 px                    |
|-------:|:---------------------------------------------|:--------|:--------------------------------|:-----------------------------|:-----------------------------------------|:---------------------------------------|
|      1 | Cold exposure (corroborated by poster)       | other   | watering 99% (then healthy 0%)  | healthy 87% (then other 10%) | watering 98% (then healthy 2%)           | healthy 97% (then other 1%)            |
|      2 | None: lost roots; rot never established      |         | healthy 68% (then watering 19%) | healthy 98% (then other 1%)  | watering 80% (then fungal_bacterial 12%) | healthy 99% (then fungal_bacterial 1%) |
|      4 | None: more light and support was advice only |         | watering 99% (then healthy 1%)  | other 71% (then healthy 27%) | watering 96% (then healthy 4%)           | healthy 90% (then other 10%)           |
