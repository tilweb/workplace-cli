from __future__ import annotations

from rich import print as rprint

from vibe.core.types import AgentStats


def format_session_usage(stats: AgentStats) -> str:
    return (
        "Total tokens used this session: "
        f"input={stats.session_prompt_tokens:,} "
        f"output={stats.session_completion_tokens:,} "
        f"(total={stats.session_total_llm_tokens:,})"
    )


def print_session_resume_message(session_id: str | None, stats: AgentStats) -> None:
    if not session_id:
        return

    print()
    print(format_session_usage(stats))
    print()
    # === ADACOR PATCH: binary name workplace statt vibe ===
    rprint("To continue this session, run: [bold dark_orange]workplace --continue[/]")
    rprint(f"Or: [bold dark_orange]workplace --resume {session_id}[/]")
    # === ADACOR PATCH END ===
