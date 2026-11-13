# The Relay

Correctness-first RAG pipeline over three pinned arXiv papers, with Groq + a calibrated stand-in, load tests, and a fixed degrade ladder.

## Policy

- Protect correctness first. Never guess to stay fast.
- Spend tokens only where they buy correctness.
- **Low-consumption mode only after 80% budget usage** (RPM/TPM/RPD/TPD). Below 80%: full quality (ladder 0).
- Degrade ladder after 80%: skip rewrite → skip LLM verify → shrink retrieval → extractive → honest try-later.

## Models

| Step | Model |
|------|--------|
| Draft | `openai/gpt-oss-120b` |
| Classify / rewrite / optional LLM verify | `openai/gpt-oss-20b` |

## Setup

```bash
pip install -r relay/requirements.txt
cp relay/.env.example .env   # set GROQ_API_KEY for real calls
export PYTHONPATH=.
```

Build the local paper index (fetches pinned PDFs once):

```bash
python -m relay.index.build_index
```

## Stand-in

```bash
python -m relay.models.standin_server
# other terminal:
python -m relay.scripts.calibrate_standin
python -m relay.scripts.run_quality
python -m relay.scripts.run_load
python -m relay.loadtest.analyze
```

## Real Groq (budget carefully)

```bash
export GROQ_API_KEY=...
python -m relay.scripts.probe_limits
python -m relay.scripts.calibrate_standin
python -m relay.scripts.run_load --real-probe
```

## Results

Per-request rows land in `relay/data/results/results.csv` with the brief’s required columns.
