# Multilingual Customer Support Chatbot

Student prototype: joint intent classification and slot extraction on MASSIVE across ten languages, with Rasa dialogue management, confidence-gated human handoff and per-language fairness evaluation. Not a real support service.

Status: Phases 0–4 done (setup, data and EDA, privacy design, NLU data pipeline, baselines). See `PROJECT_STATUS.md` for progress and `reports/requirements.md` for scope.

## Setup

Requires Python 3.10 (the newest version Rasa 3.6 supports).

```bash
python -m venv .venv
```

Activate it (`.venv\Scripts\activate` on Windows, `source .venv/bin/activate` elsewhere), then:

```bash
pip install -r requirements.txt
```

```bash
pytest
```

## Data

Download, verify and extract MASSIVE 1.1 (40 MB; details in `data/README.md`):

```bash
python -m src.data.download
```

Regenerate the dataset report (`reports/dataset_report.md`, `reports/dataset_stats.json`, `reports/figures/`):

```bash
python -m src.data.eda
```

Build the model-ready examples, label maps and frozen-split checksums (`data/processed/`, `data/splits/`), then check label alignment against both tokenizers (downloads ~18 MB of tokenizer files from Hugging Face on first run):

```bash
python -m src.data.prepare
```

```bash
python -m src.data.check_alignment
```

## Baselines

Train and evaluate the majority-intent and bag-of-embeddings baselines, logged to MLflow in `mlruns/` (downloads the 714 MB mBERT weights on first run; about 20 minutes on CPU):

```bash
python -m src.models.baselines
```

The remaining sections (training, evaluation, demo, Docker) are added as each phase is completed.
