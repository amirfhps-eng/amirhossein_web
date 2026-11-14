---
title: Notes on Practical Statistics, chapter 3
stage: budding
tags:
  - statistics
  - pandas
  - book notes
date: 2026-11-14
summary: A permutation test in pandas, and what a p-value does and does not say.
---

Chapter 3 is about statistical experiments and significance testing: how to tell whether a difference between two groups is real or just chance.

## The idea in one paragraph

A permutation test shuffles the group labels many times and asks how often chance alone produces a difference as large as the one you actually saw. If that happens rarely, the difference is probably not luck.

## A permutation test with pandas

```python
import numpy as np
import pandas as pd

def mean_diff(df):
    means = df.groupby("group")["value"].mean()
    return means["B"] - means["A"]

def permutation_test(df, n_perm=5000, seed=0):
    rng = np.random.default_rng(seed)
    observed = mean_diff(df)
    perm_diffs = np.array([
        mean_diff(df.assign(group=rng.permutation(df["group"].to_numpy())))
        for _ in range(n_perm)
    ])
    p_value = (np.abs(perm_diffs) >= abs(observed)).mean()
    return observed, p_value
```

## What I want to remember

- A p-value is how often you would see a result at least this extreme if there were no real effect. It is not the probability that the hypothesis is true.
- Resampling needs very few assumptions, which makes it a good first tool.
- Use many more shuffles than feels necessary, then check that the answer stays stable between seeds.

## Still to figure out

How does this change when the two groups are very different in size?

*This note is part of a bigger plan: see [[how-this-garden-works]] for how notes grow on this site.*
