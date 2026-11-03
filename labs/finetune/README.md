# Fine-tuning lab (Track B, module B26)

Pretrain a small transformer on unlabelled sequences, then fine-tune it on 60 labelled ones in four ways. Compare training from scratch, a new head on a frozen encoder, full fine-tuning and LoRA.

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

Each sequence holds 12 tokens from 1 to 10. It counts round the ring of 10 from a random start, in steps of 1, 2 or 3, and 10% of tokens are replaced at random. The label is the step.

- **Pretraining** sees 20,000 unlabelled sequences. It hides 15% of tokens behind a mask token and learns to fill them in. To fill a gap, the model has to work out the step.
- **Fine-tuning** sees 60 labelled sequences and predicts the step. Validation uses 2,000 fresh sequences.

## What is here

| Path | What it holds |
|---|---|
| `src/finetune_lab/data.py` | Builds the sequences and labels. NumPy only. |
| `src/finetune_lab/layers.py`, `model.py` | The encoder from lab B25, with a masked-token head and a classifier head. Given. |
| `src/finetune_lab/schedule.py` | You write: `warmup_linear`, the learning-rate factor. Pure Python. |
| `src/finetune_lab/strategies.py` | You write: `load_backbone`, `set_trainable`, `count_parameters`. |
| `src/finetune_lab/lora.py` | You write: `LoRALinear` and `add_lora`. |
| `src/finetune_lab/train.py` | Pretrains, then fine-tunes with AdamW, 10% warm-up and linear decay. |
| `tests/test_data_and_schedule.py` | What the data and the schedule must do. Runs without PyTorch. |
| `tests/test_strategies.py` | What loading, freezing and LoRA must do. Skipped when PyTorch is missing. |
| `tests/test_run.py` | The full comparison must show pretraining helping. Skipped when PyTorch is missing. |
| `solution/` | Reference answers. Read them only after your tests pass. |

## Your task

1. Write `warmup_linear` (lesson B26-L2). Run `pytest tests/test_data_and_schedule.py`.
2. Write `load_backbone`, `set_trainable` and `count_parameters` (lesson B26-L1), then `LoRALinear` and `add_lora` (lesson B26-L3). Run `pytest`: every test passes. The full run takes about 30 seconds on a laptop CPU.
3. Run `python -m finetune_lab pretrain`. It saves `checkpoints/encoder.pt`. The reference masked-token loss falls from 1.771 to 0.567 over 8 epochs.
4. Run `python -m finetune_lab compare`. With the reference solution, on 60 labelled sequences:

   | Strategy | Trainable | Accuracy, seeds 0, 1, 2 | Mean |
   |---|---|---|---|
   | Scratch | 25,955 | 0.778, 0.755, 0.744 | 0.759 |
   | Frozen encoder, new head | 99 | 0.628, 0.627, 0.547 | 0.601 |
   | Full fine-tuning | 25,955 | 0.992, 0.994, 0.990 | 0.992 |
   | LoRA, r 4, on queries and values | 1,123 | 0.990, 0.982, 0.929 | 0.967 |

5. Run `python -m finetune_lab compare --n-train 600`. The reference means are 0.963 from scratch, 0.893 for the head, 0.998 for full fine-tuning and 0.995 for LoRA. With ten times the labels, the scratch model nearly catches up.
6. Write your README. Cover the task, the four strategies, both tables, the spread across seeds, and when you would pick each strategy.

## Questions to answer in your README

- Why does the frozen encoder with a new head score below the scratch model? The pretraining task did not need the step to sit in one direction of the averaged vector.
- LoRA trains 4% of the values. What does it cost you in accuracy, and in spread across seeds?
- What would change if you had 6,000 labels?

## Extend it

- Put LoRA on the feed-forward layers too, and compare.
- Try r of 1, 2, 8 and 16 with alpha at twice r.
- Make `FinetuneConfig.lr` return 1e-2 for full fine-tuning. Run it with `warmup_share=0.1` and with `warmup_share=0.0`, and compare the accuracy across seeds.
