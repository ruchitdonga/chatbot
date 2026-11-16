# Data

## Source

| Item | Value |
|---|---|
| Dataset | MASSIVE (Multilingual Amazon SLURP for Slot-filling, Intent classification, and Virtual assistant Evaluation) |
| Version | 1.1 (released 2022-11-16; adds `ca-ES` only, all other locales unchanged from 1.0) |
| URL | https://amazon-massive-nlu-dataset.s3.amazonaws.com/amazon-massive-dataset-1.1.tar.gz |
| Archive SHA-256 | `4cba5faa11c71437928e17cb1b9b3d8b8e727e7ea363a3a9a8045e19c0491577` |
| Accessed | 2026-11-16 |
| Licence | CC BY 4.0, Copyright Amazon.com Inc. or its affiliates (`LICENSE` in the archive). MASSIVE is localised from SLURP, also CC BY 4.0. |

The raw data is not committed. `data/raw/` is git-ignored.

## Download

From the repo root:

```bash
python -m src.data.download
```

This downloads the archive into `data/raw/`, refuses it if the SHA-256 differs from `configs/project.yaml`, and extracts it to `data/raw/1.1/` using Python's safe `data` extraction filter.

## Layout and schema

One JSON-lines file per locale: `data/raw/1.1/data/<locale>.jsonl`. Fields used by this project:

| Field | Meaning |
|---|---|
| `id` | Utterance ID, shared by the parallel translations in every locale |
| `locale` | e.g. `en-US` |
| `partition` | `train`, `dev` or `test` (official split, identical across locales) |
| `scenario`, `intent` | Intent label, formatted `scenario_intent`, e.g. `alarm_set` |
| `utt` | Raw utterance |
| `annot_utt` | Utterance with inline slots, `[label : value]` |
| `judgments` | Annotator quality judgments (absent for `en-US`) |

Judgment scores, from the MASSIVE README: `intent_score` and `slots_score` 0 = No, 1 = Yes, 2 = reasonable interpretation / no slots; `language_identification` lists `target`, `english` and/or `other`.

## Citation

```bibtex
@misc{fitzgerald2022massive,
  title={MASSIVE: A 1M-Example Multilingual Natural Language Understanding Dataset with 51 Typologically-Diverse Languages},
  author={Jack FitzGerald and Christopher Hench and Charith Peris and Scott Mackie and Kay Rottmann and Ana Sanchez and Aaron Nash and Liam Urbach and Vishesh Kakarala and Richa Singh and Swetha Ranganath and Laurie Crist and Misha Britan and Wouter Leeuwis and Gokhan Tur and Prem Natarajan},
  year={2022},
  eprint={2204.08582},
  archivePrefix={arXiv},
  primaryClass={cs.CL}
}

@inproceedings{slurp,
  author={Emanuele Bastianelli and Andrea Vanzo and Pawel Swietojanski and Verena Rieser},
  title={{SLURP: A Spoken Language Understanding Resource Package}},
  booktitle={{Proceedings of the 2020 Conference on Empirical Methods in Natural Language Processing (EMNLP)}},
  year={2020}
}
```
