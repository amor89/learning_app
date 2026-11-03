# Transformer lab (Track B, module B25)

Build attention, multi-head self-attention, sinusoidal positions and a pre-norm transformer block from scratch. Then train a small classifier that needs to know token order.

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

Most tests fail with `NotImplementedError`. That is the starting point. The data is synthetic and built in code, so nothing downloads. The lab was checked with PyTorch 2.15.0 on a CPU.

## The task

Each sequence holds 4 to 12 tokens drawn from 1 to 8, right-padded with 0 to length 12. The label is 1 when the first and last real tokens match. Half the sequences match. The same tokens in another order give another label, so a model that cannot see order stays near chance.

## What is here

| Path | What it holds |
|---|---|
| `src/tiny_transformer/data.py` | Builds the sequences and labels. NumPy only. |
| `src/tiny_transformer/layers.py` | You write: `attention`, `sinusoidal_positions`, `MultiHeadSelfAttention`, `Block`. |
| `src/tiny_transformer/model.py` | You write: `Classifier`. |
| `src/tiny_transformer/train.py` | Trains with AdamW and cross-entropy, then scores 1,000 fresh validation sequences. |
| `tests/test_data.py` | What the data must look like. Runs without PyTorch. |
| `tests/test_layers.py` | What each layer must do. Checks `attention` against `torch.nn.functional.scaled_dot_product_attention`. Skipped when PyTorch is missing. |
| `tests/test_model.py` | Padding must not change a prediction, positions must, and the full run must learn. Skipped when PyTorch is missing. |
| `solution/` | Reference answers. Read them only after your tests pass. |

## Your task

1. Write `attention` (lessons B25-L3 and B25-L4). Run `pytest tests/test_layers.py -k attention`.
2. Write `sinusoidal_positions` and `MultiHeadSelfAttention` (lesson B25-L5), then `Block` (lesson B25-L6). Run `pytest tests/test_layers.py`.
3. Write `Classifier` in `model.py`. Run `pytest`: every test passes. The full run takes about 20 seconds on a laptop CPU.
4. Run `python -m tiny_transformer train`, then `python -m tiny_transformer train --no-positions`. With the reference solution and seed 0:

   | Run | Parameters | Final training loss | Validation accuracy |
   |---|---|---|---|
   | With positions | 25,826 | 0.000 | 0.9990 |
   | Without positions | 25,826 | 0.641 | 0.5390 |

   Positions are a fixed buffer, so both runs train the same number of parameters. Without them, attention sees a bag of tokens and the loss barely moves from 0.69, the loss of a coin toss. Explain the gap in your README.
5. Write your README: each part, the test that proves it, the two runs, and a diagram of one block. Push the folder to a new GitHub repository.

## Extend it

- Swap your `Block` for `nn.TransformerEncoderLayer(d, heads, 4 * d, dropout=0.0, batch_first=True, norm_first=True)` and compare (lesson B25-L6).
- Replace sinusoidal positions with a learned `nn.Embedding(max_len, d)` and compare accuracy on sequences longer than any seen in training.
- Run three seeds and report the spread of accuracy, not one number.
