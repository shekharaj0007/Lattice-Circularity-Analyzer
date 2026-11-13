# The Relay — write-up (draft skeleton)

Use the brief’s required headings in order. Fill after measurements. Max ~2 pages.

## 1 What I built and why

Correctness-first multi-step RAG over three pinned arXiv papers. **Shaping decision:** never guess to stay fast; low-consumption degrade ladder engages only after **80%** of RPM/TPM/RPD/TPD usage.

## 2 The real service and my stand-in

(Fill Table 1 from `probe_limits.py`. Describe stand-in calibration and where it differs most.)

## 3 Results

(Fill Tables 2a/2b/3 from `results.csv` via `analyze.py`. Include one surprising measured number.)

## 4 Where the time goes

(Pick one slow request; split waiting / working / retrying; before vs after first token.)

## 5 When a limit is hit

Per-minute vs per-day: who waits, who is dropped, who gets extractive / try-later, and why.

### Retrieval: quality versus cost

(Three settings from `RETRIEVAL_SETTINGS`; choose one; behavior near the limit.)

### How this library will mislead a naive retriever

1. …
2. …
3. …

## 6 Retries

Policy + one case where retrying made things worse.

## 7 What the person sees

3pm daily budget gone — exact reply shape.

## 8 What I'm unsure about, what I left out, what I learned

…

### Your feedback on Vaani

…

### How I worked with the assistant

…
