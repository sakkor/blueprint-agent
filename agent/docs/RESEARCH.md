# Reference research and design decisions

The professor's URLs were resolved to the public repositories below. This is targeted educational research, not an audit or a claim of matching proprietary Claude Code internals. Blueprint Agent's application code is independently written; reference source has not been copied into it.

## Claw Code: source inspected and binary exercised
Repository: https://github.com/ultraworkers/claw-code
Pinned revision: `8aab1d4e5410f9ab5e5e7f03c8a87de479e814ec` (also reported by the v0.1.8 Windows release).

- [`GlobalToolRegistry::execute` and `execute_tool_with_enforcer`](https://github.com/ultraworkers/claw-code/blob/8aab1d4e5410f9ab5e5e7f03c8a87de479e814ec/rust/crates/tools/src/lib.rs#L406): built-in dispatch routes through enforcement; read/write handlers parse typed input and classify path permissions before file operations. Our `Agent.dispatch` and `Workspace.path` keep a much smaller explicit tool catalog and project-only file boundary.
- [`path_scope_enforcement.rs`](https://github.com/ultraworkers/claw-code/blob/8aab1d4e5410f9ab5e5e7f03c8a87de479e814ec/rust/crates/tools/tests/path_scope_enforcement.rs): tests distinguish workspace reads from outside paths and include a Unix symlink case. Our tests cover traversal, absolute/reserved Windows paths and bounded reads; our file guard also rejects links/junctions. We do not reproduce its shell permission analyzer.
- [`parallel_tool_result_pairing.rs`](https://github.com/ultraworkers/claw-code/blob/8aab1d4e5410f9ab5e5e7f03c8a87de479e814ec/rust/crates/rusty-claude-cli/tests/parallel_tool_result_pairing.rs): a CLI/mock-service test verifies the Anthropic protocol's tool-result grouping. Our DeepSeek/OpenAI-style loop instead appends one `role: tool` response per call ID, as required by that API. `test_tool_result_pairing_and_success` checks the association; duplicate call IDs fail before execution.

The official v0.1.8 Windows binary was downloaded and its SHA-256 compared with the publisher's checksum. `--help`, `version` and `doctor` ran locally. The interactive command reported missing credentials; no real AI prompt was completed. This exercises startup, not the reference's full test suite. The README describes Claw as an agent-managed exhibit; it is not a production-readiness endorsement.

## How Claude Code Works: documentation studied and served locally
Repository: https://github.com/Windy3f3f3f3f/how-claude-code-works

[Chapter 2](https://github.com/Windy3f3f3f3f/how-claude-code-works/blob/main/en/docs/02-agent-loop.md) describes a separation between session state and the repeated model/tool/result query cycle, with budgets and recovery. Blueprint Agent separates the desktop UI from `Agent.run`, preserves tool results and stops on bounded turns, usage or context size. It does not implement streaming or conversation compaction.

[Chapter 4](https://github.com/Windy3f3f3f3f/how-claude-code-works/blob/main/en/docs/04-tool-system.md) discusses schema-defined tools, assembly and execution, including permission checks and concurrency semantics. Our five tools have fixed JSON schemas, argument checks and sequential execution. This keeps the teaching implementation inspectable; it omits shell tools, MCP, background workers and arbitrary plugins.

This repository is an independent educational analysis, not official Anthropic documentation. It is a Docsify website, not a second runnable AI agent. Its original website was downloaded, served on loopback and rendered in a browser in English.

## Official interfaces consulted
- [DeepSeek Chat Completion](https://api-docs.deepseek.com/api/create-chat-completion/): fixed `deepseek-v4-pro` model, messages, tool calls, usage and completion response. Blueprint uses HTTPS with `thinking: {type: disabled}`, nonstreaming responses and an 8,192 output-token request limit.
- [DeepSeek tool calls](https://api-docs.deepseek.com/guides/tool_calls/): local execution and tool-result reinjection.
- [Anthropic public Claude Code repository](https://github.com/anthropics/claude-code): public product/documentation reference, not assumed to publish every proprietary runtime component. It was not installed or run as part of this two-repository demonstration.

## Our architecture and intentional limits
`app.py` handles the GUI and worker queue; `blueprint.py` preprocesses documents; `agent.py` implements API calls, five tools, repair and evidence reporting; `validation.py` owns file boundaries and deterministic checks. This supports a focused Windows assignment without requiring Rust, an SDK or a local model.

The distinctive contribution is requirement-oriented feedback: source findings before generation and a file/test evidence map afterward. Quality claims and runtime behavior remain separate from static coverage. Tests use a deterministic fake client to verify the harness without pretending that a paid generation occurred.

## Version 2.1: email constraints
The later email adds native desktop game delivery and a US$1 token-cost target. The game output now has a Tkinter manifest/entry-point contract; the cost_control module reserves conservative request cost before every attempt, persists evaluation totals and stops on uncertain usage. This is application admission control rather than a provider-enforced account billing cap. See COST-POLICY.md and COMPLIANCE.md for assumptions and pending live evidence.
