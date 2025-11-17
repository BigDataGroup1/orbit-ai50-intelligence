# Lab 18: HITL Integration & Visualization - Step-by-Step Guide

## Prerequisites

1. **Virtual environment activated**
2. **MCP server running** (required for dashboard generation)
3. **Company payloads available** in `data/payloads/`

---

## Step 1: Start MCP Server (Terminal 1)

Open a **new terminal window** and run:

```bash
# Activate virtual environment (if not already activated)
.\venv\Scripts\Activate.ps1  # Windows PowerShell
# OR
source venv/bin/activate     # Linux/Mac

# Start MCP server
python src/server/mcp_server.py
```

**Expected output:**
```
======================================================================
🚀 STARTING MCP SERVER
======================================================================

📦 Loading vector store...
✅ Loaded 26985 chunks
✅ 46 companies

🤖 Initializing RAG generator...

✅ MCP SERVER READY!
======================================================================
INFO:     Started server process [xxxxx]
INFO:     Uvicorn running on http://0.0.0.0:8001
```

**Keep this terminal open!** The server must be running.

---

## Step 2: Run Workflow with HITL (Terminal 2)

Open a **second terminal window** and run:

```bash
# Activate virtual environment
.\venv\Scripts\Activate.ps1  # Windows PowerShell
# OR
source venv/bin/activate     # Linux/Mac

# Run workflow (will pause at HITL checkpoint)
python src/workflows/due_diligence_graph.py --company anthropic
```

**What happens:**
1. Workflow starts and executes nodes sequentially
2. When risks are detected, it will **PAUSE** at the HITL checkpoint
3. You'll see a prompt asking for your decision

---

## Step 3: Human Checkpoint (HITL Pause)

When the workflow detects risks, you'll see:

```
======================================================================
👤 HITL NODE: anthropic
======================================================================
   ⏸️  Workflow paused for human review

   📊 Risk Summary:
      Risk keywords: layoff, layoffs, security incident, leadership change
      Dashboard score: 75.4/100
      Company: anthropic

   ──────────────────────────────────────────────────────────────────
   ⚠️  HUMAN REVIEW REQUIRED
   ──────────────────────────────────────────────────────────────────
   This workflow has detected risks that require human review.
   Please review the information above and decide:

   Options:
     [y] Approve - Continue workflow
     [n] Reject - Stop workflow
     [s] Skip HITL - Continue without approval (not recommended)

   ──────────────────────────────────────────────────────────────────

   Enter your decision (y/n/s): 
```

**At this point:**
- The workflow is **PAUSED** and waiting for your input
- Type `y` and press Enter to approve
- Type `n` and press Enter to reject
- Type `s` and press Enter to skip (not recommended)

**Example interaction:**
```
   Enter your decision (y/n/s): y

   ✅ Human approved - continuing workflow
```

After approval, the workflow continues and completes.

---

## Step 4: View Execution Trace Files

After the workflow completes, check the generated trace files:

```bash
# List all execution traces
ls docs/execution_trace_*.md

# View the latest trace (replace with actual filename)
cat docs/execution_trace_anthropic_20251115_010000.md
```

**Or open in your editor:**
- Navigate to `docs/` folder
- Open `execution_trace_anthropic_YYYYMMDD_HHMMSS.md`

---

## Step 5: View Mermaid Diagram in Browser

### Option A: Using GitHub/GitLab (Recommended)

1. **Push trace file to GitHub/GitLab**
2. **View the `.md` file** on GitHub/GitLab
3. Mermaid diagrams render automatically

### Option B: Using VS Code

1. **Install Mermaid Preview extension** in VS Code
2. **Open the trace file** (`docs/execution_trace_*.md`)
3. **Right-click** → "Open Preview" or press `Ctrl+Shift+V`
4. Mermaid diagram will render in preview

### Option C: Using Online Mermaid Editor

1. **Copy the Mermaid code** from the trace file (between ```mermaid and ```)
2. **Go to:** https://mermaid.live/
3. **Paste the code** into the editor
4. **View the diagram** in the browser

### Option D: Using Markdown Viewer Extension

1. **Install "Markdown Preview Mermaid Support"** extension
2. **Open trace file** in VS Code
3. **Open preview** (`Ctrl+Shift+V`)
4. Diagram renders automatically

---

## Step 6: View Complete Workflow State

The trace file contains:

1. **Execution Path** - List of all nodes executed
2. **Decision Path** - Branch taken and HITL decision
3. **Mermaid Visualization** - Visual diagram
4. **Complete State** - Full JSON state at the end

**Example trace file structure:**
```markdown
# Execution Trace - anthropic

**Run ID:** 473a2a8d-bb93-4c83-b5fe-32192dac9578
**Company:** anthropic
**Branch Taken:** hitl
**Timestamp:** 2025-11-15T01:00:00

## Execution Path

### Nodes Executed
[Detailed node information...]

## Decision Path
[Decision details...]

## Visualization
[Mermaid diagram...]

## Complete State
[JSON state...]
```

---

## Quick Test (Auto-Approve Mode)

To test without waiting for input:

```bash
python src/workflows/due_diligence_graph.py --company anthropic --auto-approve
```

This automatically approves HITL without pausing.

---

## Troubleshooting

### MCP Server Not Running
**Error:** `Could not connect to MCP server at http://localhost:8001`

**Solution:** Make sure MCP server is running in Terminal 1

### No Risks Detected
**Result:** Workflow completes without HITL pause

**Solution:** Try a different company that has risks:
```bash
python src/workflows/due_diligence_graph.py --company anthropic
```

### Can't See Mermaid Diagram
**Solution:** 
- Use VS Code with Mermaid extension
- Or use online editor: https://mermaid.live/
- Or view on GitHub/GitLab

---

## Summary Checklist

✅ **Step 1:** MCP server running (`python src/server/mcp_server.py`)  
✅ **Step 2:** Run workflow (`python src/workflows/due_diligence_graph.py --company anthropic`)  
✅ **Step 3:** See HITL pause and enter decision (`y`/`n`/`s`)  
✅ **Step 4:** Workflow completes  
✅ **Step 5:** Check trace file in `docs/execution_trace_*.md`  
✅ **Step 6:** View Mermaid diagram in browser/editor  

---

## Demo Video Script

For recording a demo video:

1. **Show Terminal 1:** MCP server running
2. **Show Terminal 2:** Run workflow command
3. **Show workflow executing:** Nodes running sequentially
4. **Show HITL pause:** Workflow stops, shows risk summary
5. **Show human input:** Type `y` and press Enter
6. **Show workflow resuming:** Continues after approval
7. **Show completion:** Final summary with trace file path
8. **Show trace file:** Open in editor, show Mermaid diagram
9. **Show browser view:** Open trace file on GitHub or mermaid.live

---

## Files Generated

After running, you'll have:

1. **Execution trace:** `docs/execution_trace_{company}_{timestamp}.md`
2. **ReAct trace (if using supervisor agent):** `logs/react_traces/react_trace_{company}_{timestamp}.json`

Both contain complete execution history and decision paths.

