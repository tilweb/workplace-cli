## remember — persistent memory

Use `remember` to store a fact that should outlive the current conversation.
Stored memories are automatically shown to you (via the memory index) at the
start of every future session.

**Save** when:
- The user explicitly asks you to remember something.
- You learn a durable user preference (language, tooling, coding style).
- You discover a stable project or environment fact that is NOT already
  recorded in the repo (build quirks, deploy steps, non-obvious conventions).

**Do NOT save**:
- Transient task state, or anything only relevant to this conversation.
- Facts already captured in the code, README, or AGENTS.md.
- Secrets, tokens, or credentials.

Guidelines:
- One fact per memory. Pick a stable kebab-case `name`; reusing a name updates
  that memory. Write `content` in full sentences and give a one-line
  `description` for the index.
- Convert relative dates to absolute ones ("next Friday" → the actual date).
- Delete a memory (`action: "delete"`) when it becomes wrong or obsolete.
