"""Point everything at a throwaway directory and a small cohort BEFORE src.config is imported."""
import os
import tempfile

_tmp = tempfile.mkdtemp(prefix="flareguard_test_")
os.environ.setdefault("FLAREGUARD_DATA_DIR", os.path.join(_tmp, "data"))
os.environ.setdefault("FLAREGUARD_MODEL_DIR", os.path.join(_tmp, "models"))
os.environ.setdefault("FLAREGUARD_N_PATIENTS", "24")
os.environ.setdefault("FLAREGUARD_N_DAYS", "300")
