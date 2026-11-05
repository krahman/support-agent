# Thread & Harbor Support

> Submitted by Khalilur Rahman (khal.rahman@gmail.com)

A fictional apparel support agent. The model proposes actions; Python authorizes and executes simulated refunds, exchanges, and cancellations against persistent SQLite state.

## Setup and one-command usage

Use Python >=3.14.7 (verified locally with Python 3.15). From the extracted repository, create and activate a virtual environment:

```sh
python3 -m venv .venv
source .venv/bin/activate
python --version
```

On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1` instead. Activate the environment in each new terminal before running the commands below. After activation, `python` refers to the virtual environment's interpreter. No third-party dependencies need to be installed.

Configure your key and run the agent:

```sh
cp .env.example .env
# Set OPENROUTER_API_KEY in .env privately. Exported environment values take precedence.
# Blank values (e.g. OPENROUTER_MODEL=) are ignored, so defaults still apply.
python main.py --customer C001 --message "Refund the Cloud Cotton Tee in O100"
python main.py --customer guest@example.test --message "What is the status of O300?"
python main.py --check-model
```

The command prints JSON containing `reply` and `actions`. Each executed action has a receipt, amount in cents, and `simulated: true`. Repeat the same request: its units cannot be paid twice. A missing key or provider failure produces no order mutation and exits nonzero. Normal clarifications and policy denials exit zero.

`OPENROUTER_MODEL` selects a tool-capable OpenRouter model; `.env.example` defaults to `openai/gpt-4o-mini`. Requests use OpenRouter's [chat completions endpoint](https://openrouter.ai/docs/api/api-reference/chat/create-a-chat-completion) with bearer authentication. A live API key and network access are required for ordinary conversations. There is no silent offline fallback. `--check-model` distinguishes HTTP, DNS, TLS, timeout, and malformed-response failures without displaying credentials.

## Fixtures and state

Inspect `data/fixtures.json` for all fictional data. C001 owns O100 (tee + sale hoodie), O130 (day 30), O131 (day 31), O400 (unshipped), O401 (shipped), and O500 (two tees). C002 owns O200. `guest@example.test` owns sale order O300. Explicit defect messages exercise defective-sale handling.

For repeatable demonstrations, set `SUPPORT_TODAY=2026-11-04`. Without it, dates use actual UTC today and fixtures eventually expire. IDs such as `O500-1-1` identify individual purchased units. Read ASSUMPTIONS.md for policy decisions.

State defaults to `state/support.db`; override with `SUPPORT_DB` or `--db`. To reset safely, select a new database filename, or delete only your disposable demonstration database. Evals create isolated temporary databases and never reset interactive state.

## Tool failure injection

```sh
SUPPORT_LOOKUP_FAIL=1 python main.py --customer C001 --message "Refund O100"
```

This blocks both agent lookup and executor revalidation, creates a local escalation receipt, and makes no monetary or stock change. Remove the variable to restore lookup.

## Evaluation

```sh
python -m evals.run
python -m evals.run --live
```

Offline checks use unittest, adversarial tool proposals, scripted model doubles, fixed dates, isolated databases, concurrency, and separate CLI processes. Live checks use real OpenRouter interpretation and consume API credits. Every runner invocation writes a new JSON report under `eval_runs/` before tests start and preserves failures and partial results. A failing suite exits nonzero. Run through the eval runner to retain evidence.

## Execution boundary and submission

`support/executor.py:execute` reloads identity-scoped orders inside a write transaction, checks delivery dates, sale/defect rules, unit ownership, stock and consumed entitlements, computes amounts from paid values, then updates units and appends the simulated financial receipt in the same commit. The model cannot supply a price or directly write state. Final action replies come from executor receipts, without a post-execution model call.

Build the credential-free archive with `python scripts/package_submission.py`. Review `docs/FAILURE_ANALYSIS.md` and `docs/SUBMISSION_EMAIL.md`; rewrite the email in your own words and submit manually. Live verification status is recorded in `docs/VERIFICATION.md`.
