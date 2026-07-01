# 🤖 BDD AI Agent

> An AI-powered agent that **generates**, **reviews**, and **executes** BDD test cases from an API specification — built with LangGraph, LangChain, and Behave.

---

## 🎯 What It Does

You give it an API spec. It does the rest:

1. **Generates** Gherkin BDD scenarios using an LLM (GPT-4o / Claude)
2. **Pauses for your review** — approve or reject each scenario (human-in-the-loop)
3. **Writes** a `.feature` file and Python Behave step definitions
4. **Runs** the tests against the real API
5. **Reports** comprehensive results with pass/fail/duration per scenario

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        BDD AI Agent                         │
│                    (LangGraph Pipeline)                     │
└─────────────────────────────────────────────────────────────┘

  API Spec Input
       │
       ▼
┌─────────────┐     LLM call (GPT-4o)
│  Generate   │ ──────────────────────► Gherkin scenarios
│   Tests     │                         (delimiter-based prompt)
└──────┬──────┘
       │
       ▼
┌─────────────┐     ◄── GRAPH PAUSES HERE
│   Human     │     You approve / reject each scenario
│   Review    │     LangGraph interrupt() + resume
└──────┬──────┘
       │ (only approved scenarios continue)
       ▼
┌─────────────┐     LLM call (GPT-4o)
│  Generate   │ ──────────────────────► .feature file
│   Steps     │                         step_definitions.py
└──────┬──────┘                         environment.py
       │
       ▼
┌─────────────┐     subprocess → behave
│  Run Tests  │ ──────────────────────► JSON report
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Report    │ ──► Rich CLI table + reports/summary.txt
└─────────────┘
```

---

## 🧠 Key Concepts & Tech Stack

| Concept | Technology | Why |
|---|---|---|
| Agent orchestration | **LangGraph** | Stateful graph with human-in-loop support via `interrupt()` |
| LLM integration | **LangChain** | Provider-agnostic LLM calls (OpenAI / Anthropic) |
| BDD framework | **Behave** | Python-native BDD, runs `.feature` files |
| State management | **TypedDict** | Single source of truth passed between all nodes |
| Human-in-loop | **LangGraph interrupt()** | Pauses graph, resumes after human decision |
| Checkpointing | **MemorySaver** | Serializes state across interrupt/resume cycles |
| API testing | **requests** | HTTP calls inside generated step definitions |
| CLI output | **Rich** | Formatted tables, panels, syntax highlighting |

---

## 📁 Project Structure

```
bdd_agent/
├── agent/
│   ├── graph.py              # LangGraph state graph — nodes + edges
│   ├── llm.py                # LLM factory (OpenAI / Anthropic)
│   ├── state.py              # AgentState TypedDict — shared across all nodes
│   └── nodes/
│       ├── generate_tests.py # Node 1: LLM → Gherkin scenarios
│       ├── human_review.py   # Node 2: interrupt() → human approval
│       ├── generate_steps.py # Node 3: LLM → .feature + step defs
│       ├── run_tests.py      # Node 4: subprocess → behave
│       └── report.py         # Node 5: parse results + format report
├── features/
│   ├── generated.feature     # ← auto-generated at runtime
│   ├── environment.py        # ← auto-generated at runtime
│   └── steps/
│       └── generated_steps.py  # ← auto-generated at runtime
├── prompts/
│   ├── gherkin_prompt.txt    # Prompt for Gherkin generation
│   └── steps_prompt.txt      # Prompt for step definition generation
├── reports/
│   ├── behave_results.json   # Raw Behave JSON output
│   └── summary.txt           # Human-readable final report
├── main.py                   # Entry point — CLI runner
├── requirements.txt
└── .env.example
```

---

## 🚀 Quick Start

### 1. Clone and install

```bash
git clone https://github.com/pavankumar017/bdd_agent.git
cd bdd_agent
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
# Open .env and add your OPENAI_API_KEY
```

### 3. Run

```bash
# Interactive mode — uses built-in JSONPlaceholder example spec
python main.py

# Load your own API spec from a file
python main.py --spec path/to/your/api_spec.txt

# Pass spec as inline string
python main.py --spec-inline "REST API: My API, Base URL: https://api.example.com ..."
```

---

## ⚙️ Configuration

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | — | Required for OpenAI |
| `ANTHROPIC_API_KEY` | — | Required for Anthropic |
| `LLM_PROVIDER` | `openai` | `openai` or `anthropic` |
| `LLM_MODEL` | `gpt-4o` | Any supported model name |

---

## 🔄 How Human-in-the-Loop Works

This is the core of the agent. LangGraph's `interrupt()` mechanism:

```python
# Inside human_review_node — graph freezes here
human_decisions = interrupt(review_payload)
# ↑ execution stops, state is checkpointed

# In main.py — after collecting user input:
graph.stream(Command(resume=decisions), config)
# ↑ graph unfreezes and continues from where it stopped
```

This means the LLM does the heavy lifting, but **a human controls what actually gets tested**. No approved scenario = no test run.

---

## 📊 Sample Output

```
╭──────────────────────────────────────────────────────────╮
│               BDD Test Results Summary                   │
│  Pass Rate: 80.0%  ✅ 4 passed  ❌ 1 failed  ⏱ 2.341s  │
╰──────────────────────────────────────────────────────────╯

 Scenario Results
┌────┬──────────────────────────────────────┬───────────┬──────────┐
│ #  │ Scenario                             │ Status    │ Duration │
├────┼──────────────────────────────────────┼───────────┼──────────┤
│  1 │ Retrieve all posts                   │ ✅ PASSED │  0.412s  │
│  2 │ Retrieve a post by valid ID          │ ✅ PASSED │  0.389s  │
│  3 │ Retrieve a non-existent post         │ ✅ PASSED │  0.401s  │
│  4 │ Create a new post                    │ ✅ PASSED │  0.445s  │
│  5 │ Delete a post                        │ ❌ FAILED │  0.694s  │
└────┴──────────────────────────────────────┴───────────┴──────────┘
```

---

## 💡 Design Decisions & Learnings

**Why delimiter-based prompts instead of JSON?**
Gherkin contains newlines and double quotes. Embedding that inside JSON strings causes LLM escaping inconsistencies. Using `###SCENARIO### ... ###END###` delimiters completely sidesteps the problem — no escaping needed.

**Why LangGraph over a simple loop?**
LangGraph gives you: checkpointed state, interrupt/resume for human-in-loop, conditional branching, and a visual graph you can reason about. A `while True` loop gives you none of that.

**Why Behave over pytest-bdd?**
Behave has cleaner separation between `.feature` files and step definitions, making it easier for an LLM to generate both independently without tight coupling.

---

## 🗺️ Roadmap

- [ ] Streamlit UI for visual scenario review instead of CLI
- [ ] Regenerate rejected scenarios with human feedback fed back to LLM
- [ ] Support OpenAPI / Swagger JSON as direct input
- [ ] Allure report integration for richer HTML reports
- [ ] Multi-agent mode: separate agents for generation and validation

---

## 📄 License

MIT
