# Verification Status

> Submitted by Khalilur Rahman (khal.rahman@gmail.com)

- Current provider: OpenRouter, restored at the user's request. The application reads OPENROUTER_API_KEY at runtime, with OPENROUTER_MODEL defaulting to openai/gpt-4o-mini. No key is bundled. Older Anthropic reports are historical evidence, not verification of the current adapter.
- Runtime: Python 3.15.2 in this workspace; the project declares >=3.14.7. No third-party dependencies are required.
- Original OpenRouter build: the offline suite contained 49 checks, including the additional defect-target and history-write regressions. The earlier 46-check passing run is eval_runs/20261104T033705854576Z-748d5a4d.json; consult the latest passing report for the final source fingerprint. Exact criteria, fictional inputs/proposals, observed results, and source fingerprints are retained by the runner. The original first-run report predates richer step logging and is kept unchanged.
- Failure repair: Original 3200-cent unauthorized sale refund preserved in eval_runs/20261104T033542515843Z-477af12b.json; first fixed run preserved in eval_runs/20261104T033621885945Z-b8382e0e.json.
- Live API checks: VERIFIED on 2026-11-04 (see "Live OpenRouter verification" below). Earlier attempts in a restricted session could not reach OpenRouter; those reports are retained as history.
- To reproduce: `python3 main.py --check-model`, then `python3 -m evals.run --live`, with a valid key and network access. The current OpenRouter live suite includes product questions, refunds/retries, sale-policy override, defective-sale refund, clarification follow-up, and guest exchange. It preserves a distinct run report even when the API is unavailable.
- One-hour constraint: Implementation is intentionally a small local simulation. No recorded session duration or submission deadline has been independently verified. Screen sharing, thinking aloud, the candidate's own email wording, and manual submission remain the candidate's responsibility.

Original-build clean-extraction validation: 49/49 offline checks passed in `eval_runs/20261104T034137035840Z-07a9f7bd.json`; refund and retry CLI smoke checks also passed. The archive retains this historical report.

## Historical Anthropic migration

The native Anthropic adapter passed 53/53 offline checks in `eval_runs/20261104T034921615071Z-e5762c34.json`. Transport checks cover authentication/version headers, top-level system instructions, conversation history, input_schema conversion, tool_use parsing, missing credentials, truncated completions, malformed responses, unexpected/multiple tools, and sanitized errors. The refund/exchange/cancellation regression suite also passes. Historical eval reports and archived OpenSpec artifacts were not rewritten.

Live Anthropic behavior was not verified. This was an intermediate provider migration; the current implementation uses OpenRouter as described below.

## Current OpenRouter restoration

Restored OpenRouter chat completions and environment settings at the user's request. `eval_runs/20261104T035857147535Z-ceb13c8a.json` passes 55/55 offline checks. The adapter retains strict single-tool validation and rejects truncated responses, unexpected tools, invalid JSON arguments, and nonfinite JSON values. Connection diagnostics now distinguish DNS, TLS, timeout, HTTP, and generic network failures without disclosing keys or raw provider bodies.

Set `OPENROUTER_API_KEY` in ignored `.env` and optionally `OPENROUTER_MODEL` (default `openai/gpt-4o-mini`). After activating the venv, run `python main.py --check-model` and then `python -m evals.run --live` in a network-enabled terminal. This code switch does not lift this session's network restriction. Live OpenRouter verification is still pending. All historical eval evidence is preserved in the rebuilt ZIP.

## Live OpenRouter verification

- `eval_runs/20261104T040130197541Z-c8f44ee5.json`: 0/6 live checks. `OPENROUTER_API_KEY` was blank, so every case failed before any network call. Blank `.env` values such as `OPENROUTER_MODEL=` were also being exported as empty strings, which would have masked the default model; `support/config.py:load_env` now skips blank values.
- `eval_runs/20261104T040247116975Z-c506155e.json`: 5/6 with a real key. `test_defective_sale` was denied because the model intermittently copied the system prompt's example sentence as `defect_quote` (about 1 call in 8). The executor correctly rejected it. See `docs/FAILURE_ANALYSIS.md`.
- `eval_runs/20261104T040546360465Z-d7a82803.json`: 6/6 live checks pass after the prompt fix, model `openai/gpt-4o-mini`. The offline suite passes 55/55 in `eval_runs/20261104T040545920200Z-eb2156eb.json`.
- Limit: live model output is nondeterministic even at temperature 0. 15 repeated calls of the defect message all executed after the fix, which lowers but does not eliminate the chance of an occasional miss.
