"""Train the classifier, and save or load it as a file for the container."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
from sklearn.pipeline import Pipeline

from serve_lab.data import make_answers

MODEL_FILE = "model.joblib"
META_FILE = "meta.json"


@dataclass(frozen=True)
class ModelMeta:
    """What the endpoint reports about the model it serves."""

    name: str
    version: str


def train(
    n_train: int = 1_500, n_val: int = 500, seed: int = 0, c: float = 1.0
) -> tuple[Pipeline, float]:
    """Fit TF-IDF plus logistic regression and score it on fresh answers.

    Returns:
        The fitted pipeline and its validation accuracy.
    """
    texts, labels = make_answers(n_train, seed)
    val_texts, val_labels = make_answers(n_val, seed + 1)
    pipeline = Pipeline(
        [("tfidf", TfidfVectorizer()), ("clf", LogisticRegression(C=c, max_iter=1_000))]
    )
    pipeline.fit(texts, labels)
    return pipeline, float(accuracy_score(val_labels, pipeline.predict(val_texts)))


def save_artifact(model: Pipeline, meta: ModelMeta, folder: Path) -> None:
    """Write the model and its name and version to a folder the image copies in."""
    folder.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, folder / MODEL_FILE)
    (folder / META_FILE).write_text(json.dumps(asdict(meta)), encoding="utf-8")


def load_artifact(folder: Path) -> tuple[Pipeline, ModelMeta]:
    """Load a saved model. joblib runs code from the file: load only files you built."""
    model: Pipeline = joblib.load(folder / MODEL_FILE)
    meta = ModelMeta(**json.loads((folder / META_FILE).read_text(encoding="utf-8")))
    return model, meta
