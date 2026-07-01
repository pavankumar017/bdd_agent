"""
BDD Agent — Entry Point

Usage:
    python main.py                          # Interactive CLI mode
    python main.py --spec path/to/spec.txt  # Load spec from file
    python main.py --spec-inline "..."      # Pass spec as string

The agent will:
  1. Generate BDD scenarios from your API spec
  2. Pause for your review (approve/reject each scenario)
  3. Generate Behave feature file + step definitions
  4. Run the tests
  5. Display a comprehensive report
"""

import argparse
import sys
import uuid
from pathlib import Path

from dotenv import load_dotenv
from langgraph.types import Command
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

from agent.graph import build_graph
from agent.state import AgentState, Scenario

load_dotenv()
console = Console()

# Example API spec for quick testing
EXAMPLE_SPEC = """
REST API: JSONPlaceholder - Posts API
Base URL: https://jsonplaceholder.typicode.com

Endpoints:
  GET    /posts          - Returns list of all posts (200)
  GET    /posts/{id}     - Returns a single post by ID (200, 404 if not found)
  POST   /posts          - Creates a new post (201)
                           Body: { "title": string, "body": string, "userId": integer }
  PUT    /posts/{id}     - Updates a post (200, 404 if not found)
  DELETE /posts/{id}     - Deletes a post (200)

Response format (Post object):
  { "id": integer, "title": string, "body": string, "userId": integer }

Authentication: None required for this public API.
"""


def get_api_spec(args) -> str:
    """Get API spec from args, file, or interactive prompt."""
    if args.spec:
        spec_path = Path(args.spec)
        if not spec_path.exists():
            console.print(f"[red]❌ Spec file not found: {args.spec}[/red]")
            sys.exit(1)
        return spec_path.read_text(encoding="utf-8")

    if args.spec_inline:
        return args.spec_inline

    # Interactive mode
    console.print(Panel(
        "[bold yellow]BDD Agent[/bold yellow]\n"
        "AI-powered BDD test generation with human-in-loop review",
        expand=False
    ))

    use_example = Confirm.ask(
        "\nUse the built-in example API spec (JSONPlaceholder Posts)?",
        default=True
    )

    if use_example:
        console.print("[dim]Using example spec: JSONPlaceholder Posts API[/dim]")
        return EXAMPLE_SPEC

    console.print("\nPaste your API specification below.")
    console.print("[dim](Enter a blank line followed by 'END' to finish)[/dim]\n")

    lines = []
    while True:
        line = input()
        if line.strip() == "END":
            break
        lines.append(line)

    return "\n".join(lines)


def run_human_review(graph, config: dict, thread_id: str) -> dict:
    """
    Handles the human-in-loop review step.
    Reads the interrupted state, collects decisions, and resumes the graph.
    """
    # Get current state (paused at human_review)
    current_state = graph.get_state(config)
    scenarios: list[Scenario] = current_state.values.get("generated_scenarios", [])

    if not scenarios:
        console.print("[yellow]No scenarios to review.[/yellow]")
        return {}

    console.print(Panel(
        f"[bold yellow]👁  Human Review — {len(scenarios)} Scenarios[/bold yellow]\n"
        "Review each scenario and approve or reject it.",
        expand=False
    ))

    decisions = {}

    for scenario in scenarios:
        console.print(f"\n[bold cyan]━━━ Scenario #{scenario['id']}: {scenario['title']} ━━━[/bold cyan]")
        console.print(f"[white]{scenario['gherkin']}[/white]")
        console.print()

        approved = Confirm.ask(f"  ✅ Approve scenario #{scenario['id']}?", default=True)
        feedback = ""
        if not approved:
            feedback = Prompt.ask("  💬 Feedback (optional)", default="")

        decisions[scenario["id"]] = {"approved": approved, "feedback": feedback}

        status = "[green]APPROVED[/green]" if approved else "[red]REJECTED[/red]"
        console.print(f"  → {status}")

    return decisions


def main():
    parser = argparse.ArgumentParser(description="BDD Agent — AI-powered BDD test generator")
    parser.add_argument("--spec", help="Path to API spec file")
    parser.add_argument("--spec-inline", help="API spec as inline string")
    args = parser.parse_args()

    api_spec = get_api_spec(args)

    # Build the graph
    graph = build_graph()

    # Unique thread ID for this run (enables checkpointing)
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    console.print(f"\n[dim]Session ID: {thread_id}[/dim]\n")

    # --- Phase 1: Generate test scenarios (runs until interrupt at human_review) ---
    console.print(Panel("[bold]Phase 1: Generating BDD Scenarios[/bold]", expand=False))

    initial_state: AgentState = {
        "api_spec": api_spec,
        "generated_scenarios": [],
        "approved_scenarios": [],
        "feature_file_path": "",
        "steps_file_path": "",
        "step_definitions": "",
        "test_results": [],
        "raw_behave_output": "",
        "report": "",
        "error": None,
        "current_node": ""
    }

    # Run until interrupt
    for event in graph.stream(initial_state, config, stream_mode="values"):
        # Events stream as state snapshots; we just let them flow
        if event.get("error"):
            console.print(f"[red]❌ Error: {event['error']}[/red]")
            sys.exit(1)

    # --- Phase 2: Human review ---
    console.print(Panel("[bold]Phase 2: Human Review[/bold]", expand=False))
    decisions = run_human_review(graph, config, thread_id)

    approved_count = sum(1 for d in decisions.values() if d["approved"])
    if approved_count == 0:
        console.print("[yellow]⚠️  No scenarios approved. Exiting.[/yellow]")
        sys.exit(0)

    console.print(f"\n[green]✅ {approved_count} scenarios approved. Continuing...[/green]\n")

    # --- Phase 3: Resume graph (generate steps → run tests → report) ---
    console.print(Panel("[bold]Phase 3: Generating Steps, Running Tests & Reporting[/bold]", expand=False))

    for event in graph.stream(
        Command(resume=decisions),
        config,
        stream_mode="values"
    ):
        if event.get("error"):
            console.print(f"[red]❌ Error: {event['error']}[/red]")
            # Don't exit — report node may still run

    console.print(Panel(
        "[bold green]🎉 BDD Agent run complete![/bold green]\n"
        "Check [dim]reports/summary.txt[/dim] for the full report.",
        expand=False
    ))


if __name__ == "__main__":
    main()
