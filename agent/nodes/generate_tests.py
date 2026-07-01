"""
Node: generate_tests
Calls the LLM with the API spec and returns a list of Gherkin scenarios.

Uses a delimiter-based prompt format (###SCENARIO### ... ###END###) instead of
JSON to avoid LLM escaping issues with multi-line Gherkin content.
"""

from pathlib import Path

from langchain_core.messages import HumanMessage
from rich.console import Console
from rich.panel import Panel

from agent.state import AgentState, Scenario
from agent.llm import get_llm

console = Console()

PROMPT_PATH = Path(__file__).parent.parent.parent / "prompts" / "gherkin_prompt.txt"


def _parse_scenarios(raw: str) -> list[dict]:
    """
    Parse the delimiter-based LLM response into a list of scenario dicts.

    Expected format per block:
        ###SCENARIO###
        TITLE: Some title here
        GHERKIN:
        Scenario: Some title here
          Given ...
          When ...
          Then ...
        ###END###
    """
    scenarios = []
    blocks = raw.split("###SCENARIO###")

    for i, block in enumerate(blocks):
        block = block.strip()
        if not block or "###END###" not in block:
            continue

        # Trim everything after ###END###
        block = block.split("###END###")[0].strip()

        title = ""
        gherkin = ""

        if "TITLE:" in block and "GHERKIN:" in block:
            # Extract title — everything after "TITLE:" up to the next newline
            title_part = block.split("TITLE:", 1)[1]
            title = title_part.splitlines()[0].strip()

            # Extract gherkin — everything after "GHERKIN:\n"
            gherkin_part = block.split("GHERKIN:", 1)[1].strip()
            gherkin = gherkin_part.strip()

        elif "Scenario" in block:
            # Fallback: no TITLE/GHERKIN markers but has Scenario keyword
            lines = block.splitlines()
            for line in lines:
                if line.strip().startswith("Scenario"):
                    title = line.strip().replace("Scenario Outline:", "").replace("Scenario:", "").strip()
                    break
            gherkin = block.strip()

        if gherkin:
            scenarios.append({
                "id":     i,
                "title":  title or f"Scenario {i}",
                "gherkin": gherkin,
            })
        else:
            console.print(f"[yellow]⚠️  Skipping block {i} — could not extract gherkin.[/yellow]")

    return scenarios


def generate_tests_node(state: AgentState) -> AgentState:
    """
    LangGraph node: generates BDD Gherkin scenarios from the API spec.
    Updates state with `generated_scenarios`.
    """
    console.print(Panel("[bold cyan]🤖 Generating BDD test scenarios...[/bold cyan]"))

    api_spec = state["api_spec"]
    if not api_spec:
        return {**state, "error": "No API spec provided.", "current_node": "generate_tests"}

    prompt_template = PROMPT_PATH.read_text()
    prompt = prompt_template.format(api_spec=api_spec)

    llm = get_llm()

    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        raw_content = response.content.strip()

        console.print(f"[dim]Raw LLM response length: {len(raw_content)} chars[/dim]")

        scenarios_data = _parse_scenarios(raw_content)

        if not scenarios_data:
            # Last resort: dump raw so the user can see what came back
            console.print(f"[red]❌ Could not parse any scenarios.[/red]")
            console.print(f"[dim]--- Raw LLM output ---\n{raw_content[:1000]}\n---[/dim]")
            return {
                **state,
                "error": "Could not parse scenarios from LLM response.",
                "current_node": "generate_tests"
            }

        scenarios: list[Scenario] = [
            Scenario(
                id=item["id"],
                title=item["title"],
                gherkin=item["gherkin"],
                approved=False,
                feedback=""
            )
            for item in scenarios_data
        ]

        console.print(f"[green]✅ Generated {len(scenarios)} scenarios.[/green]")
        for s in scenarios:
            console.print(f"  [dim]{s['id']}. {s['title']}[/dim]")

        return {
            **state,
            "generated_scenarios": scenarios,
            "error": None,
            "current_node": "generate_tests"
        }

    except Exception as e:
        import traceback
        error_msg = f"LLM call failed: {e}"
        console.print(f"[red]❌ {error_msg}[/red]")
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        return {**state, "error": error_msg, "current_node": "generate_tests"}
