# Millenium LLM Analyst MVP

This repository owns the boundary after risk core: it accepts a versioned JSON
snapshot, asks a provider-neutral analyst for structured verdicts, and produces
an interactive HTML report plus machine-readable artifacts. It does **not**
calculate risk metrics, run the planned validator, or execute governor actions.

## Run the complete demo

No dependencies or credentials are needed for the deterministic mock provider:

```bash
python3 run_mvp.py examples/risk_core_sample.json --provider mock
open output/reports/index.html
```

Outputs:

- `output/reports/analysis.json` - provider-neutral LLM result
- `output/reports/report.json` - risk-core data plus analyst interpretation
- `output/reports/index.html` - self-contained interactive report
- `output/pdf/millenium_pod_risk_review.pdf` - printable snapshot

Run the dependency-free core suite with:

```bash
python3 -m unittest discover -s tests -v
```

Run the complete suite, including ReportLab/Poppler PDF generation, pagination,
and HTML-to-PDF narrative parity checks, with:

```bash
.venv/bin/python -m unittest discover -s tests -v
```

The suite covers snapshot and analyst contracts, canonical metric citations,
environment-file safety, Anthropic and OpenAI adapter payloads, prompt
allowlists, quadrant boundaries, HTML escaping, CLI artifact generation, and
PDF content/pagination regression checks. Provider tests mock network calls and
never consume API credits.

## Live providers

Copy `.env.example` to ignored `.env.local`, or export values through your
runtime. The CLI loads only a small allowlist of provider settings from
`.env.local`/`.env` and never executes those files as shell code.

OpenAI:

```bash
ANALYST_PROVIDER=openai ANALYST_MODEL=<model-id> OPENAI_API_KEY=<secret> \
  python3 run_mvp.py examples/risk_core_sample.json
```

Anthropic:

```bash
python3 run_mvp.py examples/risk_core_sample.json --provider anthropic
```

Anthropic defaults to `claude-sonnet-5`; set `ANALYST_MODEL` to override it.

OpenAI uses Responses API strict JSON Schema output. Anthropic uses a forced,
schema-backed tool call. Both are normalized to the same analysis contract and
checked for run IDs, pod coverage, valid enums, valid metric citations, and
`not_executed` recommendations.

## Contract choices

The proposed upstream contract is `config/risk_core_contract.schema.json`.
Risk core owns all numbers, units, windows, baselines, and provenance. The
analyst may only cite stable metric paths already present in a pod snapshot.

The verdict taxonomy is the complete 2x2 performance/skill matrix—`skilled`,
`lucky`, `unlucky`, and `broken`—plus `inconclusive` for material data-quality
gaps. Gaming risk is separate because suspicious behavior and performance
quality are different judgments.

Each verdict must also explain why it was reached, the strongest alternative
explanation, what evidence would change it, why each recommendation is timely,
the immediate next step, and the signal that would count as improvement.

The report derives chart positions from risk-core values rather than model
prose. This prevents a model-generated explanation from moving or relabeling
the underlying quantitative evidence.
