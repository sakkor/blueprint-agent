# Blueprint Agent 2.3.2

A Windows desktop code agent for the professor's Task 1. It reads the supplied architecture Markdown and UML views, uses the official DeepSeek V4 Pro API and writes a project for a **native desktop Space Fractions game**.

The professor's October 22 email supplements the ZIP: show the agent and the generated desktop game in a YouTube video, share the source (for example through GitHub), and keep evaluation token charges within US$1.

## Fixes in 2.3
- Check API (no generation) uses official GET /models and GET /user/balance. It sends no architecture documents or text-generation request. Generation repeats this check automatically with a new client.
- A failed completion request is never automatically resent. Unknown charges retain a conservative reservation.
- DNS, certificate, timeout and Windows permission failures have distinct messages without printing secrets.
- Each received choice and the last API response are saved, with the exact key redacted, to aid review of partial work.
- Read-only metadata checks cannot guarantee a subsequent generation succeeds or stays within the target.

## Quick start
1. Install Python 3.12 with Tkinter, install requirements.txt, and run `python app.py` from this directory. To build an executable, use build.ps1.
2. The two original example files are preselected. Choose **Inspect inputs** to see 21 checklist entries, 13 UML blocks, 10 required output artifacts and the source conflicts.
3. Choose one output folder for your evaluation. Keep using it for retries so its cost ledger is shared.
4. Enter your official DeepSeek API key privately in the masked field. Keep Show key unchecked during recording.
5. First click **Check API (no generation)**. Proceed only after it passes. Then choose **Generate desktop game**. This sends both documents to the official API and incurs usage charges. The default is 40 turns with a $0.90 conservative cost guard.
6. Open the evidence report. Review errors, warnings and partial/deferred features before accepting an output.
7. Open the generated project in an editor. Follow its README to install dependencies and run tests. Launch its native desktop.py entry point, then use its build_game.ps1 to build Space-Fractions.exe. These generated files require inspection and actual execution before the demo.

Full local paths are hidden by default; use Show full paths for troubleshooting.

## What is included
- build.ps1: builds the Windows executable; binaries are not included in this source repository.
- app.py: Tkinter interface, background worker and progress display.
- agent.py: official API client, five function tools, generation/repair loop and HTML evidence report.
- blueprint.py: source extraction, hashes, UML catalog and requirement catalog.
- validation.py: file boundaries, syntax/artifact checks, desktop output structure and evidence references.
- cost_control.py: pre-request cost reservations, usage settlement and persistent evaluation ledger.
- tests/: offline unit and localhost HTTP integration tests.
- examples/: the two unmodified professor-provided inputs.
- docs/: reference research, cost policy and third-party notices. See the root README for submission status.

## Desktop output contract
The game uses Python 3.12 + tkinter/ttk with desktop.py, desktop-manifest.json and build_game.ps1. Checks require a native Tk window/event loop and a PyInstaller desktop packaging recipe with tests; a browser launcher or web-only project is rejected. Generated tests must reference the desktop requirement. Static structure cannot establish that a window is useful or that every feature works.

The original architecture describes a web/microservices system; the later email requires desktop delivery. The agent is explicitly instructed to reconcile this in ASSUMPTIONS.md, preserve Game/Question/User/Admin responsibilities, provide PostgreSQL persistence and retain the original API/SQL/deployment design. Any SQLite offline demo adapter must be disclosed, and quality/infrastructure gaps must be marked honestly.

## Cost controls
The app reserves a conservative cost estimate **before every network attempt**, with no automatic retry. It uses request UTF-8 byte length plus a framing allowance for input, the maximum requested output (8192 tokens), and published peak uncached rates checked October 29, 2026. Known usage is settled at those conservative rates; unknown attempts keep the full reservation. Missing/inconsistent usage stops further calls.

The default $0.90 guard leaves $0.10 below the professor's $1 target. The ledger is stored as evaluation-budget.json in the chosen output folder and survives restarts. It is shared across generation attempts in that folder; concurrent runs are locked out. This is **an estimate guard, not a provider-enforced account-wide billing cap**. Verify prices and the final bill in the official account, and include attempts from other folders/tools in the evaluation total. See docs/COST-POLICY.md.

The API key is held in memory, not saved as configuration. Exact-key matches are rejected in generated file content and redacted from reports. Do not put secrets in source documents. Generated code is never executed automatically by the agent.

## Results and honest status
Each new run has inputs/, project/, events.jsonl, run-report.json, report.html and SUMMARY.md. ready_for_runtime_test means structural checks passed, not that the game passed tests. needs_review means there are warnings or partial claims. budget_limit, cost_review, failed, cancelled and incomplete preserve partial work and explain why the run stopped.

A live DeepSeek run produced the game in this repository, but stopped at the budget guard. The game was repaired locally after generation. See ../game/LOCAL-REVIEW.md and ../evidence/STATUS.md. This does not establish full requirement compliance or clean-machine compatibility.

## Develop, test and build
Use Python 3.12 with Tkinter on Windows:
```
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python app.py
```
Run build.ps1 to install the build requirements, test, package and smoke-test the executable. The --self-test REPORT.json mode is offline and makes no API call.

Implementation is independently written for this assignment. Reference research is credited in docs/RESEARCH.md. It is a simplified teaching agent, not a clone of all Claude Code capabilities.
