# jeevan-0508.github.io

Source of my portfolio page: **https://jeevan-0508.github.io**

One page, two files, no dependencies, no build step, no tracking. It exists to make four separate
repositories legible as one body of work:

| | |
|---|---|
| [Freight & Carrier Fraud Risk Taxonomy](https://github.com/Jeevan-0508/freight-fraud-taxonomy) | the data model |
| [Freight Risk Atlas](https://github.com/Jeevan-0508/freight-risk-atlas) | an assessment engine over it |
| [AI Risk Control Room](https://github.com/Jeevan-0508/ai-governance-control-room) | the same discipline applied to AI regulation |
| [FOMO](https://github.com/Jeevan-0508/FOMO) | a standing watch on German logistics risk news |
| [AI Compliance Scanner](https://github.com/Jeevan-0508/eu-ai-act-scanner) | fast self-assessment against the EU AI Act, ISO 42001 and NIST AI RMF |
| [GDPR Compliance Scanner](https://github.com/Jeevan-0508/gdpr-compliance-scanner) | a personal-data linter that screens a file before you share it |

Every figure quoted on the page is counted from the source data of the repository it describes, not
written by hand.

## The three scheduled jobs

Every six hours, driven by real signals only. Nothing writes prose, and nothing
commits unless a fact has changed.

| Job | Cadence | What it may change | What it may never do |
|---|---|---|---|
| `refresh` — figures | every 6h | rewrites a quoted number to match the source data it came from | invent a figure, or touch a sentence |
| `refresh` — activity | every 6h | regenerates the *Latest* section from real pushes and FOMO signals | write a timestamp, so a quiet run makes no commit |
| `inspect` | every 6h, offset 30m | nothing at all — it opens or updates one issue | edit the page, or close a finding on your behalf |

`scripts/refresh.py` recounts every `data-fig` on the page from the source data
of the repository that figure describes, so the page cannot drift from the truth
it claims. It is idempotent: running it twice produces an identical file.

`scripts/inspect_site.py` tests the deployed URL — structure, contact route,
image and page weight, link rot, and whether the repositories the page sends
people to actually describe themselves. Findings are a decision for a human.
