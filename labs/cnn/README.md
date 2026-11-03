# CNN lab (Track B, module B24)

Train a small convolutional network on handwritten digits and compare it with a dense network on the same split.

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

Most tests fail with `NotImplementedError`. That is the starting point. The data is scikit-learn's bundled digits dataset, 1,797 images of 8 by 8 pixels, so nothing downloads. The lab was checked with PyTorch 2.15.0 on a CPU.

## What is here

| Path | What it holds |
|---|---|
| `src/digits_cnn/data.py` | Loads the digits as (N, 8, 8) images in [0, 1] with labels 0 to 9. |
| `src/digits_cnn/vision.py` | You write: `add_channel`, `random_shift`, `confusion`, `recall_by_class`. NumPy only. |
| `src/digits_cnn/models.py` | You write: `make_cnn`. |
| `src/digits_cnn/train.py` | Trains a dense network and your CNN on the same stratified split and batches, with early stopping, and scores both. |
| `tests/test_vision.py` | What the NumPy steps must do. Runs without PyTorch. |
| `tests/test_models.py` | What the CNN and the full run must do. Skipped when PyTorch is missing. |
| `solution/` | Reference answers. Read them only after your tests pass. |

## Your task

1. Fill in `vision.py`, then `models.py`, until `pytest` passes.
2. Run `python -m digits_cnn train`. With the reference solution it prints, on 360 validation images:

   | Model | Parameters | Validation loss | Accuracy |
   |---|---|---|---|
   | Dense | 4,810 | 0.0985 | 0.9778 |
   | CNN | 6,090 | 0.0374 | 0.9917 |

   Your numbers match only if your steps use the random generators in the same order.
3. Run `python -m digits_cnn train --augment`, which shifts training images by up to one pixel. In the reference run the CNN's validation loss rose to 0.0495 and the dense network's accuracy fell to 0.9389. The digits are centred, and one pixel is an eighth of the image. Explain in your README why augmentation did not help here, and when it would.
4. Read the recall for each digit. Which digits does each model confuse?
5. Write your README: the data, both models, the parameter counts, the comparison, the confusion, and the augmentation result.

## Extend it

- End the CNN with `nn.AdaptiveAvgPool2d(1)` (lesson B24-L3) and compare.
- Try a smaller shift with `max_shift=0` plus horizontal flips, and explain why flips are wrong for digits (lesson B24-L4).
- Run three seeds and report the spread of accuracy, not one number.
