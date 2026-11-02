# RAG lab (Track B, modules B21 and B22)

Build a retrieval-augmented generation pipeline that answers questions about a survey tracker's methodology, with citations you can check.

## Set up

From this folder:

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e .
pip install pytest
pytest
```

Most tests fail with `NotImplementedError`. That is the starting point.

## What is here

| Path | What it holds |
|---|---|
| `notes/` | Five methodology notes. The file name is the document ID, each `##` heading is a section. |
| `eval/questions.jsonl` | 12 gold questions, each with the section IDs that answer it. |
| `src/survey_rag/steps.py` | The seven functions you write. Each docstring names its lesson. |
| `src/survey_rag/corpus.py` | Splits notes into sections and chunks. Chunk IDs look like `weighting#w14-change#0`. |
| `src/survey_rag/index.py` | Two keyword rankings (word and character TF-IDF), fused with your `rrf`. |
| `src/survey_rag/prompt.py` | The system prompt and the tagged user turn. |
| `src/survey_rag/llm.py` | The optional Claude caller. |
| `src/survey_rag/pipeline.py` | Retrieve, prompt, call, check citations. |
| `src/survey_rag/evaluate.py` | Recall at k and MRR on the gold questions. |
| `tests/` | What each function and the pipeline must do. |
| `solution/steps.py` | Reference answers. Read them only after your tests pass. |

## Your task

1. Fill in the functions in `src/survey_rag/steps.py` until `pytest` passes.
2. Score retrieval: `python -m survey_rag eval --k 3`. Compare chunk sizes with `python -m survey_rag --size 40 eval --k 3` and `--size 120`.
3. Read a prompt without calling a model: `python -m survey_rag ask "What changed in the W14 weighting?" --dry-run`.
4. Optional, with a model: `pip install -e ".[llm]"`, set `ANTHROPIC_API_KEY`, and run the same command without `--dry-run`. The command prints the answer, the sources it sent and any citation problems. It exits with code 1 when a citation check fails.

## About the model call

`llm.py` uses the Anthropic Python SDK, anthropic 2.4.0, with the model `claude-opus-5-5`. It calls `client.beta.messages.create` with the beta `server-side-fallback-2026-07-01` and `fallbacks="default"`: if the model declines a request, the API retries it on a fallback model inside the same call. Remove both arguments to turn this off. Each call costs money. The eval command never calls a model.

## Extend it

- Swap the character ranking for sentence embeddings (lesson B15-L1). Keep the same chunk IDs and compare MRR.
- Add a threshold: when the best word-ranking score is low, return the refusal without calling the model. Set the threshold from the gold questions.
- Add questions the notes cannot answer, and check the pipeline refuses them.
- Add an answer evaluation with the checks from lesson B22-L2.
