"""
Node: human_review
Pauses the graph and presents generated scenarios to the user for approval.
Uses LangGraph's interrupt() for true human-in-the-loop behavior.
"""

from langgraph.types import interrupt
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich import box

from agent.state import AgentState, Scenario

console = Console()


def human_review_node(state: AgentState) -> AgentState:
    """
    LangGraph node: presents scenarios to the human for approval/rejection.
    Uses LangGraph interrupt() to pause execution and wait for human input.
    Updates state with `approved_scenarios`.
    """
    scenarios = state.get("generated_scenarios", [])

    if not scenarios:
        console.print("[yellow]⚠️  No scenarios to review.[/yellow]")
        return {**state, "approved_scenarios": [], "current_node": "human_review"}

    # Display all scenarios in a rich table
    _display_scenarios(scenarios)

    # Use LangGraph interrupt to pause and collect human decisions
    # The interrupt payload is sent to the caller; resume value contains decisions
    review_payload = {
        "message": "Review the generated BDD scenarios above.",
        "scenarios": [
            {"id": s["id"], "title": s["title"], "gherkin": s["gherkin"]}
            for s in scenarios
        ],
        "instructions": (
            "For each scenario, provide your decision. "
            "Return a dict: {scenario_id: {'approved': bool, 'feedback': str}}"
        )
    }

    # This pauses the graph — the runner must call graph.invoke() with a Command(resume=...)
    human_decisions: dict = interrupt(review_payload)

    # Process decisions
    approved: list[Scenario] = []
    for scenario in scenarios:
        sid = scenario["id"]
        decision = human_decisions.get(sid, human_decisions.get(str(sid), {}))
        is_approved = decision.get("approved", False)
        feedback = decision.get("feedback", "")

        updated = Scenario(
            id=scenario["id"],
            title=scenario["title"],
            gherkin=scenario["gherkin"],
            approved=is_approved,
            feedback=feedback
        )
        if is_approved:
            approved.append(updated)

    console.print(f"\n[green]✅ {len(approved)} / {len(scenarios)} scenarios approved.[/green]")

    if not approved:
        console.print("[yellow]⚠️  No scenarios approved. Ending workflow.[/yellow]")

    return {
        **state,
        "approved_scenarios": approved,
        "current_node": "human_review"
    }


def _display_scenarios(scenarios: list[Scenario]) -> None:
    """Render scenarios in a rich formatted table."""
    console.print(Panel(
        f"[bold yellow]👁  Human Review — {len(scenarios)} Scenarios Generated[/bold yellow]",
        expand=False
    ))

    for scenario in scenarios:
        table = Table(
            title=f"[bold]#{scenario['id']}: {scenario['title']}[/bold]",
            box=box.ROUNDED,
            show_header=False,
            expand=True
        )
        table.add_column("Gherkin", style="cyan", no_wrap=False)
        table.add_row(scenario["gherkin"])
        console.print(table)
        console.print()


# ---------------------------------------------------------------------------
# CLI fallback: used when running outside LangGraph (e.g., direct testing)
# ---------------------------------------------------------------------------

def cli_human_review(scenarios: list[Scenario]) -> list[Scenario]:
    """
    Interactive CLI review — used when running the agent in CLI mode
    without LangGraph's interrupt mechanism.
    """
    _display_scenarios(scenarios)
    approved = []

    console.print("[bold]Review each scenario:[/bold]\n")
    for scenario in scenarios:
        console.print(f"[bold cyan]#{scenario['id']}: {scenario['title']}[/bold cyan]")
        console.print(scenario["gherkin"])
        console.print()

        decision = Confirm.ask(f"  Approve scenario #{scenario['id']}?", default=True)
        feedback = ""
        if not decision:
            feedback = Prompt.ask("  Feedback (optional)", default="")

        updated = Scenario(
            id=scenario["id"],
            title=scenario["title"],
            gherkin=scenario["gherkin"],
            approved=decision,
            feedback=feedback
        )
        if decision:
            approved.append(updated)

        console.print()

    return approved
