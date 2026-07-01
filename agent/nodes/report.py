"""
Node: report
Generates a comprehensive, human-readable test report from Behave results.
"""

from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

from agent.state import AgentState, TestResult

console = Console()

REPORTS_DIR = Path(__file__).parent.parent.parent / "reports"


def report_node(state: AgentState) -> AgentState:
    """
    LangGraph node: builds and displays a comprehensive test report.
    Writes the report to reports/summary.txt as well.
    """
    console.print(Panel("[bold cyan]📊 Generating Test Report...[/bold cyan]"))

    results: list[TestResult] = state.get("test_results", [])
    approved = state.get("approved_scenarios", [])
    raw_output = state.get("raw_behave_output", "")

    report_text = _build_report(results, approved, raw_output)

    # Print to console
    _print_rich_report(results, approved)

    # Save to file
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / "summary.txt"
    report_path.write_text(report_text, encoding="utf-8")
    console.print(f"\n[dim]📄 Full report saved to: {report_path}[/dim]")

    return {
        **state,
        "report": report_text,
        "current_node": "report"
    }


def _print_rich_report(results: list[TestResult], approved: list) -> None:
    """Render a rich formatted report to the console."""

    # Summary counts
    total = len(results)
    passed = sum(1 for r in results if r["status"] == "passed")
    failed = sum(1 for r in results if r["status"] == "failed")
    undefined = sum(1 for r in results if r["status"] == "undefined")
    skipped = sum(1 for r in results if r["status"] == "skipped")
    total_duration = sum(r["duration"] for r in results)

    # Header panel
    pass_rate = (passed / total * 100) if total > 0 else 0
    color = "green" if pass_rate == 100 else "yellow" if pass_rate >= 50 else "red"

    console.print(Panel(
        f"[bold {color}]Pass Rate: {pass_rate:.1f}%[/bold {color}]  |  "
        f"[green]✅ {passed} passed[/green]  "
        f"[red]❌ {failed} failed[/red]  "
        f"[yellow]⚠️  {undefined} undefined[/yellow]  "
        f"[dim]⏭  {skipped} skipped[/dim]  "
        f"[dim]⏱  {total_duration:.3f}s total[/dim]",
        title="[bold]BDD Test Results Summary[/bold]",
        expand=True
    ))

    if not results:
        console.print("[yellow]No test results found.[/yellow]")
        return

    # Detailed results table
    table = Table(
        title="Scenario Results",
        box=box.ROUNDED,
        show_lines=True,
        expand=True
    )
    table.add_column("#", style="dim", width=4)
    table.add_column("Scenario", style="white")
    table.add_column("Status", justify="center", width=12)
    table.add_column("Duration", justify="right", width=10)
    table.add_column("Error", style="red", no_wrap=False)

    status_styles = {
        "passed": "[bold green]✅ PASSED[/bold green]",
        "failed": "[bold red]❌ FAILED[/bold red]",
        "undefined": "[bold yellow]⚠️  UNDEF[/bold yellow]",
        "skipped": "[dim]⏭  SKIP[/dim]",
    }

    for i, result in enumerate(results, 1):
        status_display = status_styles.get(result["status"], result["status"])
        error_display = (result["error"] or "")[:200]  # Truncate long errors
        table.add_row(
            str(i),
            result["scenario"],
            status_display,
            f"{result['duration']:.3f}s",
            error_display
        )

    console.print(table)

    # Failed scenario details
    failed_results = [r for r in results if r["status"] == "failed"]
    if failed_results:
        console.print("\n[bold red]❌ Failed Scenario Details:[/bold red]")
        for r in failed_results:
            console.print(Panel(
                f"[red]{r['error'] or 'No error details available'}[/red]",
                title=f"[bold red]{r['scenario']}[/bold red]",
                border_style="red"
            ))


def _build_report(
    results: list[TestResult],
    approved: list,
    raw_output: str
) -> str:
    """Build a plain-text report string."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total = len(results)
    passed = sum(1 for r in results if r["status"] == "passed")
    failed = sum(1 for r in results if r["status"] == "failed")
    undefined = sum(1 for r in results if r["status"] == "undefined")
    skipped = sum(1 for r in results if r["status"] == "skipped")
    total_duration = sum(r["duration"] for r in results)
    pass_rate = (passed / total * 100) if total > 0 else 0

    lines = [
        "=" * 70,
        "  BDD AGENT — TEST EXECUTION REPORT",
        f"  Generated: {now}",
        "=" * 70,
        "",
        "SUMMARY",
        "-" * 40,
        f"  Total Scenarios : {total}",
        f"  Passed          : {passed}",
        f"  Failed          : {failed}",
        f"  Undefined       : {undefined}",
        f"  Skipped         : {skipped}",
        f"  Pass Rate       : {pass_rate:.1f}%",
        f"  Total Duration  : {total_duration:.3f}s",
        "",
        "SCENARIO RESULTS",
        "-" * 40,
    ]

    for i, result in enumerate(results, 1):
        status_icon = {"passed": "✅", "failed": "❌", "undefined": "⚠️", "skipped": "⏭"}.get(
            result["status"], "?"
        )
        lines.append(f"  {i:2}. {status_icon} [{result['status'].upper():9}] {result['scenario']}")
        lines.append(f"       Duration: {result['duration']:.3f}s")
        if result["error"]:
            lines.append(f"       Error: {result['error'][:300]}")
        lines.append("")

    lines += [
        "APPROVED SCENARIOS",
        "-" * 40,
    ]
    for s in approved:
        lines.append(f"  • {s['title']}")
    lines.append("")

    lines += [
        "RAW BEHAVE OUTPUT",
        "-" * 40,
        raw_output,
        "",
        "=" * 70,
        "  END OF REPORT",
        "=" * 70,
    ]

    return "\n".join(lines)
