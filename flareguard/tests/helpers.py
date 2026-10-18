from functools import lru_cache

from src.datagen.generate import simulate_cohort


@lru_cache(maxsize=1)
def cohort():
    return simulate_cohort()  # (df, truths), sized by conftest env vars
