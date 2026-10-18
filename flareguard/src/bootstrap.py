"""Create the synthetic data and trained model if they don't exist yet.

    python -m src.bootstrap            # only what's missing
    python -m src.bootstrap --force    # regenerate everything
"""
import argparse

from src import config


def ensure_artifacts(force=False):
    if force or not config.LOGS_PATH.exists() or not config.TRUTH_PATH.exists():
        from src.datagen.generate import generate_and_save
        generate_and_save()
    if force or not config.MODEL_PATH.exists():
        from src.models.train import train_and_save
        train_and_save()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ensure_artifacts(ap.parse_args().force)
    print("Data and model ready.")
