"""`workplace mcp` — add, list and remove MCP servers from the command line.

Writes to the same ``config.toml`` the app reads (via ``VibeConfig`` /
``save_updates``), so entries are validated and serialised correctly — no
hand-editing and no TOML array-of-tables pitfalls.
"""

from __future__ import annotations

import argparse
import os
import tomllib
from typing import Any

from rich import print as rprint

from vibe.core.config import VibeConfig
from vibe.core.config._settings import MCPHttp, MCPServer, MCPStdio, MCPStreamableHttp
from vibe.core.config.harness_files import (
    get_harness_files_manager,
    init_harness_files_manager,
)
from vibe.core.paths import GLOBAL_ENV_FILE


class McpCliError(Exception):
    """User-facing error for the mcp CLI."""


# --------------------------------------------------------------------------- #
# Core operations (pure-ish; used by the CLI and covered by tests)
# --------------------------------------------------------------------------- #
def configured_servers() -> list[dict[str, Any]]:
    """Return the raw ``mcp_servers`` entries from the active config file."""
    mgr = get_harness_files_manager()
    target = mgr.config_file or mgr.user_config_file
    if target and target.exists():
        try:
            data = tomllib.loads(target.read_text(encoding="utf-8"))
        except (tomllib.TOMLDecodeError, OSError):
            return []
        servers = data.get("mcp_servers", [])
        return list(servers) if isinstance(servers, list) else []
    return []


def add_server(server: MCPServer, *, force: bool = False) -> None:
    """Add (or, with ``force``, replace) a validated MCP server."""
    servers = configured_servers()
    if any(s.get("name") == server.name for s in servers):
        if not force:
            raise McpCliError(
                f"MCP server {server.name!r} already exists. Use --force to replace it."
            )
        servers = [s for s in servers if s.get("name") != server.name]
    servers.append(server.model_dump(mode="json", exclude_defaults=True))
    VibeConfig.save_updates({"mcp_servers": servers})


def remove_server(name: str) -> bool:
    """Remove a server by name. Returns True if one was removed."""
    servers = configured_servers()
    remaining = [s for s in servers if s.get("name") != name]
    if len(remaining) == len(servers):
        return False
    VibeConfig.save_updates({"mcp_servers": remaining})
    return True


def build_server(
    *,
    name: str,
    transport: str,
    url: str | None,
    api_key_env: str,
    api_key_header: str,
    api_key_format: str,
    headers: dict[str, str],
    env: dict[str, str],
    command_argv: list[str],
) -> MCPServer:
    """Validate CLI inputs into a concrete MCPServer model."""
    if transport == "stdio":
        if not command_argv:
            raise McpCliError(
                "stdio transport needs a command after '--', e.g.\n"
                "  workplace mcp add fetch --transport stdio -- uvx mcp-server-fetch"
            )
        return MCPStdio(
            name=name,
            transport="stdio",
            command=command_argv[0],
            args=command_argv[1:],
            env=env,
        )

    if not url:
        raise McpCliError(f"{transport} transport requires --url.")
    fields: dict[str, Any] = {"name": name, "url": url, "headers": headers}
    if api_key_env:
        fields["api_key_env"] = api_key_env
        fields["api_key_header"] = api_key_header
        fields["api_key_format"] = api_key_format
    if transport == "streamable-http":
        return MCPStreamableHttp(transport="streamable-http", **fields)
    return MCPHttp(transport="http", **fields)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _parse_kv(pairs: list[str] | None) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in pairs or []:
        if "=" not in item:
            raise McpCliError(f"Expected KEY=VALUE, got {item!r}.")
        key, value = item.split("=", 1)
        result[key.strip()] = value
    return result


def _env_var_available(name: str) -> bool:
    if os.getenv(name):
        return True
    try:
        for line in GLOBAL_ENV_FILE.path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith(f"{name}=") and stripped.split("=", 1)[1].strip():
                return True
    except OSError:
        pass
    return False


def _describe(server: dict[str, Any]) -> str:
    transport = server.get("transport", "?")
    where = server.get("url") or " ".join(
        [str(server.get("command", ""))] + list(server.get("args") or [])
    )
    state = " [disabled]" if server.get("disabled") else ""
    return f"  {server.get('name'):<20} {transport:<16} {where}{state}"


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def _cmd_add(args: argparse.Namespace, command_argv: list[str]) -> None:
    server = build_server(
        name=args.name,
        transport=args.transport,
        url=args.url,
        api_key_env=args.api_key_env,
        api_key_header=args.api_key_header,
        api_key_format=args.api_key_format,
        headers=_parse_kv(args.header),
        env=_parse_kv(args.env),
        command_argv=command_argv,
    )
    add_server(server, force=args.force)
    target = get_harness_files_manager().config_file
    rprint(f"[green]✓[/] MCP server [bold]{server.name}[/] added ({args.transport}).")
    if target:
        rprint(f"  Written to {target}")
    if args.api_key_env and not _env_var_available(args.api_key_env):
        rprint(
            f"[yellow]  Note:[/] set the token in the environment variable "
            f"[bold]{args.api_key_env}[/] (e.g. add it to {GLOBAL_ENV_FILE.path})."
        )
    rprint("  Restart Workplace CLI (or /reload) to pick it up; verify with /mcp.")


def _cmd_list(_args: argparse.Namespace) -> None:
    servers = configured_servers()
    if not servers:
        rprint("No MCP servers configured.")
        return
    rprint(f"[bold]{len(servers)} MCP server(s):[/]")
    for server in servers:
        rprint(_describe(server))


def _cmd_remove(args: argparse.Namespace) -> None:
    if remove_server(args.name):
        rprint(f"[green]✓[/] Removed MCP server [bold]{args.name}[/].")
        rprint("  Restart Workplace CLI (or /reload) to apply.")
    else:
        raise McpCliError(f"No MCP server named {args.name!r}.")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="workplace mcp", description="Manage MCP (Model Context Protocol) servers."
    )
    sub = parser.add_subparsers(dest="action", required=True)

    p_add = sub.add_parser("add", help="Add an MCP server")
    p_add.add_argument("name", help="Short alias (used to prefix the server's tools)")
    p_add.add_argument(
        "--transport",
        choices=["streamable-http", "http", "stdio"],
        default="streamable-http",
        help="Transport type (default: streamable-http)",
    )
    p_add.add_argument("--url", help="Base URL (for http/streamable-http)")
    p_add.add_argument(
        "--api-key-env",
        default="",
        metavar="VAR",
        help="Name of the env var holding the API token (kept out of config.toml)",
    )
    p_add.add_argument("--api-key-header", default="Authorization")
    p_add.add_argument("--api-key-format", default="Bearer {token}")
    p_add.add_argument(
        "--header",
        action="append",
        metavar="KEY=VALUE",
        help="Extra HTTP header (repeatable)",
    )
    p_add.add_argument(
        "--env",
        action="append",
        metavar="KEY=VALUE",
        help="Env var for a stdio server process (repeatable)",
    )
    p_add.add_argument(
        "--force", action="store_true", help="Replace an existing server of this name"
    )

    sub.add_parser("list", help="List configured MCP servers")

    p_remove = sub.add_parser("remove", help="Remove an MCP server")
    p_remove.add_argument("name", help="Name of the server to remove")
    return parser


def run_mcp_cli(argv: list[str]) -> None:
    """Entry point for ``workplace mcp ...`` (argv without the 'mcp' token)."""
    # Everything after a bare '--' is the stdio command line.
    command_argv: list[str] = []
    if "--" in argv:
        idx = argv.index("--")
        argv, command_argv = argv[:idx], argv[idx + 1 :]

    args = _build_parser().parse_args(argv)
    init_harness_files_manager("user", "project")

    try:
        match args.action:
            case "add":
                _cmd_add(args, command_argv)
            case "list":
                _cmd_list(args)
            case "remove":
                _cmd_remove(args)
    except McpCliError as error:
        rprint(f"[red]Error:[/] {error}")
        raise SystemExit(1) from error
    except Exception as error:  # pydantic ValidationError etc.
        rprint(f"[red]Error:[/] {error}")
        raise SystemExit(1) from error
