"""
Shared state schema for the BDD Agent LangGraph graph.
All nodes read from and write to this TypedDict.
"""

from typing import TypedDict, List, Optional, Annotated
import operator


class Scenario(TypedDict):
    """A single BDD scenario with its approval status."""
    id: int
    title: str
    gherkin: str          # Full Gherkin text for this scenario
    approved: bool        # Set during human review
    feedback: str         # Optional human feedback/notes


class TestResult(TypedDict):
    """Result of a single Behave scenario execution."""
    scenario: str
    status: str           # passed / failed / skipped / undefined
    duration: float
    error: Optional[str]


class AgentState(TypedDict):
    """
    Central state object passed between all LangGraph nodes.
    """
    # --- Input ---
    api_spec: str                           # Raw API description or OpenAPI JSON/YAML

    # --- Generation ---
    generated_scenarios: List[Scenario]     # LLM-generated Gherkin scenarios

    # --- Human Review ---
    approved_scenarios: List[Scenario]      # Subset approved by human

    # --- Step Definitions ---
    feature_file_path: str                  # Path to written .feature file
    steps_file_path: str                    # Path to written step defs file
    step_definitions: str                   # Raw Python step def code

    # --- Test Execution ---
    test_results: List[TestResult]          # Per-scenario results from Behave
    raw_behave_output: str                  # Full stdout/stderr from Behave run

    # --- Reporting ---
    report: str                             # Final formatted report string

    # --- Control ---
    error: Optional[str]                    # Any error message to surface
    current_node: str                       # Tracks which node is active
