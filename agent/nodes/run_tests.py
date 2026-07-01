"""
Node: run_tests
Executes Behave against the generated .feature file and captures results.
"""

import json
import subprocess
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from agent.state import AgentState, TestResult

console = Console()

FEATURES_DIR = Path(__file__).parent.parent.parent / "features"
REPORTS_DIR = Path(__file__).parent.parent.parent / "reports"


def run_tests_node(state: AgentState) -> AgentState:
    """
    LangGraph node: runs Behave and captures structured test results.
    """
    console.print(Panel("[bold cyan]🚀 Running BDD tests with Behave...[/bold cyan]"))

    feature_path = state.get("feature_file_path", str(FEATURES_DIR / "generated.feature"))

    if not Path(feature_path).exists():
        error_msg = f"Feature file not found: {feature_path}"
        console.print(f"[red]❌ {error_msg}[/red]")
        return {**state, "error": error_msg, "current_node": "run_tests"}

    # Ensure reports directory exists
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    json_report_path = REPORTS_DIR / "behave_results.json"

    # Build Behave command
    cmd = [
        sys.executable, "-m", "behave",
        str(feature_path),
        "--no-capture",                        # Show print output
        "--format", "json",
        "--outfile", str(json_report_path),    # JSON report
        "--format", "pretty",                  # Human-readable to stdout
        "--no-skipped",
    ]

    console.print(f"[dim]Running: {' '.join(cmd)}[/dim]\n")

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            progress.add_task("Executing scenarios...", total=None)

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=str(Path(__file__).parent.parent.parent)  # Run from project root
            )

        raw_output = result.stdout + result.stderr
        console.print(raw_output)

        # Parse JSON report
        test_results = _parse_json_report(json_report_path)

        return {
            **state,
            "test_results": test_results,
            "raw_behave_output": raw_output,
            "error": None,
            "current_node": "run_tests"
        }

    except FileNotFoundError:
        error_msg = "Behave is not installed. Run: pip install behave"
        console.print(f"[red]❌ {error_msg}[/red]")
        return {**state, "error": error_msg, "current_node": "run_tests"}

    except Exception as e:
        error_msg = f"Test execution failed: {e}"
        console.print(f"[red]❌ {error_msg}[/red]")
        return {**state, "error": error_msg, "current_node": "run_tests"}


def _parse_json_report(report_path: Path) -> list[TestResult]:
    """Parse Behave's JSON output into a list of TestResult objects."""
    if not report_path.exists():
        return []

    try:
        data = json.loads(report_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []

    results: list[TestResult] = []

    for feature in data:
        for element in feature.get("elements", []):
            if element.get("type") != "scenario":
                continue

            scenario_name = element.get("name", "Unknown")
            steps = element.get("steps", [])

            # Determine overall scenario status
            statuses = [step.get("result", {}).get("status", "skipped") for step in steps]
            if "failed" in statuses:
                status = "failed"
            elif "undefined" in statuses:
                status = "undefined"
            elif all(s == "passed" for s in statuses):
                status = "passed"
            else:
                status = "skipped"

            # Total duration
            duration = sum(
                step.get("result", {}).get("duration", 0.0)
                for step in steps
            )

            # Collect error messages from failed steps
            errors = [
                step.get("result", {}).get("error_message", "")
                for step in steps
                if step.get("result", {}).get("status") == "failed"
            ]
            error_text = "\n".join(filter(None, errors)) or None

            results.append(TestResult(
                scenario=scenario_name,
                status=status,
                duration=round(duration, 4),
                error=error_text
            ))

    return results
