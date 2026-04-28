# Codex Agents

This folder stores portable copies of local Codex sub-agent configs used while developing the project.

## code_searcher_mini

`code_searcher_mini` is a read-only repository investigator for targeted code questions, call graphs, symbols, flows, and evidence-backed findings.

To install it on another machine:

1. Copy `codex_agents/code_searcher_mini.toml` to:

```text
C:\Users\<you>\.codex\agents\code_searcher_mini.toml
```

2. Add this block to:

```text
C:\Users\<you>\.codex\config.toml
```

```toml
[agents.code_searcher_mini]
description = "Read-only repository investigator for targeted code questions, call graphs, symbols, flows, and evidence-backed findings."
config_file = "agents/code_searcher_mini.toml"
```

3. Restart Codex if the agent does not appear immediately.

This is not required for the Telegram bot to run. It is only a local Codex workflow helper.
