# Due Diligence Workflow Graph

Lab 17: Supervisory Workflow Pattern (Graph-based)

## Overview

The Due Diligence Workflow is a graph-based orchestration system that processes companies through a series of specialized nodes, with conditional branching based on risk detection.

## Workflow Diagram

```
                    ┌─────────────┐
                    │   START     │
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │   PLANNER   │
                    │             │
                    │ Constructs │
                    │ plan of    │
                    │ actions    │
                    └──────┬──────┘
                           │
                           ▼
                ┌───────────────────────┐
                │   DATA GENERATOR       │
                │                        │
                │ 1. Retrieve payload   │
                │ 2. Invoke MCP         │
                │    dashboard tools    │
                └──────┬────────────────┘
                       │
                       ▼
                ┌───────────────────────┐
                │     EVALUATOR          │
                │                        │
                │ Scores dashboards     │
                │ per rubric:           │
                │ - Length (20 pts)     │
                │ - Structure (30 pts)  │
                │ - Quality (30 pts)    │
                │ - Formatting (20 pts) │
                └──────┬────────────────┘
                       │
                       ▼
                ┌───────────────────────┐
                │   RISK DETECTOR        │
                │                        │
                │ Scans for risk        │
                │ keywords:             │
                │ - layoff, bankruptcy  │
                │ - lawsuit, breach      │
                │ - funding issues      │
                └──────┬────────────────┘
                       │
                       │
        ┌──────────────┴──────────────┐
        │                             │
        │ Conditional Branch          │
        │                             │
        ▼                             ▼
┌───────────────┐           ┌───────────────┐
│  HITL BRANCH  │           │ NORMAL BRANCH │
│               │           │               │
│ Risks found   │           │ No risks      │
│ → Pause for   │           │ → Continue    │
│   human       │           │   to end      │
│   review      │           │               │
└───────┬───────┘           └───────┬───────┘
        │                           │
        └───────────┬───────────────┘
                    │
                    ▼
              ┌───────────┐
              │    END    │
              └───────────┘
```

## Node Descriptions

### 1. Planner Node
**Responsibility:** Constructs plan of actions

**Input:** `company_id`

**Output:** `plan` (list of action steps)

**Logic:**
- Creates a structured plan for the due diligence workflow
- Defines 4 main steps:
  1. Retrieve company structured payload
  2. Generate dashboard via MCP
  3. Evaluate dashboard quality
  4. Detect risks and determine if HITL needed

**Example Output:**
```json
{
  "plan": [
    "1. Retrieve company structured payload",
    "2. Generate dashboard via MCP",
    "3. Evaluate dashboard quality",
    "4. Detect risks and determine if HITL needed"
  ]
}
```

---

### 2. Data Generator Node
**Responsibility:** Invokes MCP dashboard tools

**Input:** `company_id`, `plan`

**Output:** `payload`, `dashboard_markdown`

**Logic:**
1. Retrieves structured payload using `get_latest_structured_payload` tool
2. Calls MCP server to generate structured dashboard
3. Stores dashboard markdown in state

**Dependencies:**
- MCP server must be running and enabled
- Company payload must exist in `data/payloads/`

**Example Output:**
```json
{
  "payload": {...},
  "dashboard_markdown": "# Company Dashboard\n\n...",
  "metadata": {
    "tokens_used": 1234
  }
}
```

---

### 3. Evaluator Node
**Responsibility:** Scores dashboards per rubric

**Input:** `dashboard_markdown`

**Output:** `dashboard_score` (0-100)

**Scoring Rubric:**

| Criteria | Points | Description |
|----------|--------|-------------|
| **Length** | 20 | Dashboard length > 1000 chars = 20 pts, > 500 = 15 pts, > 200 = 10 pts |
| **Structure** | 30 | Presence of key sections (company, funding, valuation, team, product, revenue, customers, competitors) |
| **Quality** | 30 | Data quality indicators (founded, headquarters, CEO, employees, funding, valuation, revenue) |
| **Formatting** | 20 | Markdown formatting (headers, lists, structured data) |

**Total:** 100 points

**Example Output:**
```json
{
  "dashboard_score": 75.5,
  "metadata": {
    "evaluation_timestamp": "2025-11-14T23:45:00"
  }
}
```

---

### 4. Risk Detector Node
**Responsibility:** Branches to HITL if keywords found

**Input:** `dashboard_markdown`, `payload`

**Output:** `risk_keywords`, `requires_hitl`, `branch_taken`

**Risk Keywords:**
- **Layoffs:** layoff, layoffs, firing, termination, downsizing
- **Financial:** bankruptcy, insolvency, default, foreclosure
- **Legal:** lawsuit, litigation, legal action, breach
- **Security:** security incident, data breach, hack, cyber attack
- **Funding:** funding round failed, investor pullout, valuation drop
- **Leadership:** ceo resignation, executive departure, leadership change

**Branching Logic:**
```python
if len(risk_keywords) > 0:
    branch_taken = "hitl"
    requires_hitl = True
else:
    branch_taken = "normal"
    requires_hitl = False
```

**Example Output (Risks Found):**
```json
{
  "risk_keywords": ["layoff", "downsizing"],
  "requires_hitl": true,
  "branch_taken": "hitl"
}
```

**Example Output (No Risks):**
```json
{
  "risk_keywords": [],
  "requires_hitl": false,
  "branch_taken": "normal"
}
```

---

### 5. HITL Node (Conditional)
**Responsibility:** Human-in-the-Loop review point

**Input:** `risk_keywords`, `dashboard_score`

**Output:** `metadata.hitl_approved`

**Logic:**
- Pauses workflow for human review
- Displays risk information
- Waits for human approval (simulated in current implementation)
- Continues workflow after approval

**Note:** In production, this would integrate with a task queue or notification system to pause and wait for actual human input.

---

## State Schema

```typescript
interface WorkflowState {
  company_id: string;
  plan: string[] | null;
  payload: object | null;
  dashboard_markdown: string | null;
  dashboard_score: number | null;
  risk_keywords: string[];
  requires_hitl: boolean;
  branch_taken: "normal" | "hitl" | null;
  error: string | null;
  metadata: {
    planner_timestamp?: string;
    tokens_used?: number;
    evaluation_timestamp?: string;
    risk_detection_timestamp?: string;
    risk_count?: number;
    hitl_timestamp?: string;
    hitl_approved?: boolean;
  };
}
```

## Execution Flow

### Normal Flow (No Risks)
```
START → Planner → Data Generator → Evaluator → Risk Detector → END
                                                      │
                                                      └─→ branch_taken: "normal"
```

### HITL Flow (Risks Detected)
```
START → Planner → Data Generator → Evaluator → Risk Detector → HITL → END
                                                      │            │
                                                      └─→ branch_taken: "hitl"
```

## Usage

### Run Workflow
```bash
# Run for a specific company
python src/workflows/due_diligence_graph.py --company anthropic

# Default (anthropic)
python src/workflows/due_diligence_graph.py
```

### Expected Output
```
======================================================================
🚀 DUE DILIGENCE WORKFLOW
======================================================================
Company: anthropic
Timestamp: 2025-11-14T23:45:00
======================================================================

[Node execution logs...]

======================================================================
✅ WORKFLOW COMPLETE
======================================================================
Company: anthropic
Branch taken: normal  (or "hitl" if risks found)
Dashboard score: 75.5/100
Risks detected: 0
Requires HITL: False
======================================================================

======================================================================
✅ CHECKPOINT: Branch taken = normal
======================================================================
```

## Testing

Unit tests cover both branches:
- `test_normal_flow()` - Tests workflow when no risks are detected
- `test_hitl_flow()` - Tests workflow when risks are detected

See `src/tests/test_workflow_graph.py` for details.

## Implementation Details

- **Graph Library:** LangGraph (with fallback to sequential execution)
- **State Management:** TypedDict for type safety
- **Error Handling:** Errors stored in state, workflow continues when possible
- **Async Support:** All nodes support async execution
- **MCP Integration:** Uses existing MCP integration for dashboard generation

## Checkpoint Validation

✅ **Workflow diagram provided** - `docs/WORKFLOW_GRAPH.md`

✅ **Unit test covering both branches** - `src/tests/test_workflow_graph.py`

✅ **`python src/workflows/due_diligence_graph.py` prints branch taken** - Implemented in `__main__` block

