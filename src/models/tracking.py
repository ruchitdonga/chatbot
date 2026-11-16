"""Shared MLflow setup: a local SQLite store under paths.mlflow_tracking_uri."""
import hashlib
import subprocess

import mlflow

from src.data.load import ROOT
from src.data.prepare import SPLITS_DIR


def init_mlflow(cfg, experiment):
    mlruns = ROOT / cfg["paths"]["mlflow_tracking_uri"]
    mlruns.mkdir(parents=True, exist_ok=True)
    mlflow.set_tracking_uri(f"sqlite:///{(mlruns / 'mlflow.db').as_posix()}")
    if mlflow.get_experiment_by_name(experiment) is None:
        mlflow.create_experiment(experiment, artifact_location=(mlruns / "artifacts" / experiment).as_uri())
    mlflow.set_experiment(experiment)


def git_commit():
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True,
                              check=True).stdout.strip()
    except subprocess.CalledProcessError:
        return "uncommitted"


def lineage_params(cfg):
    """Seed, code version and data fingerprint, logged with every run."""
    return {"seed": cfg["project"]["seed"], "git_commit": git_commit(),
            "splits_checksums_sha256": hashlib.sha256((SPLITS_DIR / "checksums.json").read_bytes()).hexdigest()}
