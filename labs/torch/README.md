# PyTorch lab (Track B, modules B23 and B16)

Train a small neural network on survey data, and show whether it beats a logistic regression baseline.

## Set up

From this folder:

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install torch --index-url https://download.pytorch.org/whl/cpu   # optional: the smaller CPU build
pip install -e .
pip install pytest
pytest
```

Most tests fail with `NotImplementedError`. That is the starting point. The lab was checked with PyTorch 2.15.0 on a CPU.

## What is here

| Path | What it holds |
|---|---|
| `src/survey_torch/data.py` | A seeded generator of 6,000 synthetic respondents with a 0/1 "would recommend" outcome. Interactions in the data give a network something a linear model misses. |
| `src/survey_torch/prep.py` | You write: `split_indices`, `Standardiser`, `EarlyStopping`. NumPy only. |
| `src/survey_torch/nn_steps.py` | You write: `SurveyRows`, `make_model`, `train_one_epoch`, `evaluate`. |
| `src/survey_torch/train.py` | Puts the steps together: seeds, split, scaling, loaders, AdamW, early stopping, and the baseline. |
| `tests/test_prep.py` | What the NumPy steps must do. Runs without PyTorch. |
| `tests/test_nn_steps.py` | What the PyTorch steps and the full run must do. Skipped when PyTorch is missing. |
| `solution/` | Reference answers. Read them only after your tests pass. |

## Your task

1. Fill in `prep.py`, then `nn_steps.py`, until `pytest` passes.
2. Run `python -m survey_torch train`. The reference solution prints a validation loss of 0.2719 and accuracy of 0.8800 for the network, against 0.3008 and 0.8725 for the baseline, after 45 epochs. Your numbers match only if your steps use the random generators in the same order.
3. Try `--hidden 8`, `--hidden 128`, `--lr 0.03` and `--patience 3`. Write down what each did to the validation loss and the epochs run.
4. Save a loss curve with `--curve curve.csv` and plot it. Where does validation loss stop falling?
5. Write your README: the data, the model, the comparison with the baseline, the curve, and one thing that did not work.

## Extend it

- Add dropout and weight decay and compare the curves.
- Report the area under the ROC curve as well as accuracy (lesson B12-L1).
- Log each run with MLflow (lesson B14-L1).
