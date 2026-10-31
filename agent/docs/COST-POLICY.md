# US$1 evaluation target and cost guard

The professor's email says token cost should be within one dollar. Treat all attempts used for the evaluation as contributing to that total unless the professor clarifies a different scope. An account recharge is not the same as a consumed API charge.

## Implemented admission policy
- The app's shared evaluation ceiling is $0.90 (900,000 micro-US dollars), leaving a nominal $0.10 margin.
- DeepSeek V4 Pro prices last checked 2026-10-29: $1.32 per million uncached input tokens and $3.96 per million output tokens at peak. Cached and off-peak discounts are deliberately ignored when settling usage. Source: https://api-docs.deepseek.com/quick_start/pricing/
- Before EVERY attempt, including retries, reserve input cost from serialized UTF-8 request bytes + 4096 framing allowance + 128 per message/tool, plus the maximum 8192 output tokens. This deliberately overestimates ordinary text tokenization but is not an official tokenizer/count endpoint.
- Refuse the request before network access if its reservation would exceed the remaining guard.
- After a valid response, replace that reservation with the conservative peak cost calculated from reported prompt/output tokens.
- If an attempt fails or the response cannot be used, retain the full reservation. This avoids pretending an interrupted request was free.
- Missing/inconsistent usage or usage beyond the reservation assumptions marks the ledger blocked and stops further calls. Check the official bill before proceeding.

## Persistence and concurrency
The output folder contains evaluation-budget.json. All runs in that folder share it, even after restarting the app. It contains only cost counters and error state, not the API key. An exclusive .lock file prevents two app runs from overspending the same ledger concurrently. Reservations are saved before sending, so a crash does not erase them.

If a crash leaves a stale lock, first make sure no generation is running and inspect the existing ledger and official usage. Keep the ledger: removing a stale lock after checking the process is different from erasing usage. Do not count a new output folder as a new allowance for the same evaluation; sum all attempts.

## Practical limits
This is an estimate-based application guard, not an account-wide provider billing cap. Its validity depends on the published rates and conservative token estimate. Other programs, price changes, account billing adjustments and unreported usage are outside its control. It deliberately stops early rather than claiming a finished project at any cost. Successful completion within $1 is not yet proven.

The report includes rates, accounting method, unknown attempt count, shared evaluation amount and per-run amount. billing_verified remains false: only the provider's account can confirm the final bill. Before recording, compare the official usage/billing entry with the run's timestamps and token counts. Include all retries, and leave a margin rather than spending exactly $1.

## Version 2.3 connection protection
Official model-list and balance GET checks precede generation. They do not request text generation. Failed metadata checks do not reserve token cost. The completion client makes one HTTP attempt per requested model turn; it never automatically resends a failed request. An unknown outcome keeps its full reservation. This does not remove normal model/tool turns or validation/repair turns from a successful generation.
Prior reservations are preserved, and the UI labels the total as an estimate including reservations. Do not reset the ledger without verified billing evidence. This application does not include an automatic refund/reconciliation button.
