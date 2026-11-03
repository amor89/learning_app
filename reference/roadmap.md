# 18-month learning roadmap (draft for confirmation)

Goal: Senior Data Scientist roles, first in applied or analytics data science, then applied or product data science at tech companies.

Status: the topic sequence below is confirmed. The month ranges are a proposed split. Replace them with the months from the original plan if they differ.

| Months | Theme | Topics | Evidence to produce |
|---|---|---|---|
| 1-3 | PyTorch foundations | Tensors, autograd, training loops, reproducibility, device handling | One documented PyTorch project on GitHub by month 3 |
| 4-6 | CNNs | Convolutions, pooling, CNN on a real dataset, transfer learning, evaluation | CNN project with documented results |
| 7-9 | NLP with deep learning | Embeddings, sequence models, attention, transformer architecture from scratch | Transformer built from scratch with explanation |
| 10-12 | Transformers applied | Fine-tuning a pre-trained model (text classification or NER), evaluation | Fine-tuned model on a work-relevant task |
| 13-15 | LLMs | Prompting, RAG pipeline, LLM evaluation | RAG pipeline on GitHub |
| 16-18 | MLOps and deployment | MLflow tracking and registry, FastAPI endpoint, Azure deployment, monitoring | One deployed model with README |

Running throughout:
- Senior interview preparation: theory depth and practical coding (from-scratch implementations, trade-offs).
- Monthly learning documentation: quick reference plus deep dive per month.

Tagging rule for the learning app:
- Track A and Track C modules support months 16-18 (production and MLOps) and current work.
- Track B modules B1 to B14 are prerequisites for all months. B15 maps to months 7-9. B23 (PyTorch foundations, with the PyTorch lab) and B16 map to months 1-3. B24 (convolutional networks, with the CNN lab) maps to months 4-6. B25 (attention and transformers from scratch, with the transformer lab) maps to months 7-9. B26 (fine-tuning pretrained models, with the fine-tuning lab) maps to months 10-12. B27 (serving and monitoring models, with the serving lab) and B14 map to months 16-18. B20 to B22 (prompting, RAG and LLM evaluation, with the RAG lab) map to months 13-15.
- Track D applies to every month.
