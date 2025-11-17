"""
Interactive PE Agent - Chat Interface
Ask questions in natural language about Forbes AI 50 companies
FIXED: Properly uses Pydantic models for tool calls
"""

import os
import sys
import json
from pathlib import Path
from typing import Optional
import asyncio

# Add project root to path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from openai import AsyncOpenAI
from src.agents.tools import (
    get_latest_structured_payload,
    rag_search_company,
    report_layoff_signal,
    PayloadRequest,
    RAGSearchRequest,
    LayoffSignal
)
from src.agents.react_logger import ReActLogger
from src.workflows.due_diligence_graph import run_workflow

# Initialize OpenAI
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Available companies
AVAILABLE_COMPANIES = [
    'abridge', 'anthropic', 'anysphere', 'baseten', 'captions',
    'character_ai', 'cohere', 'coreweave', 'databricks', 'deepl',
    'eightfold_ai', 'elevenLabs', 'Factory', 'figure_ai', 'glean',
    'groq', 'harvey', 'heygen', 'hugging_face', 'inflection_ai',
    'jasper', 'mistral_ai', 'moonhub', 'moveworks', 'notion',
    'openai', 'perplexity', 'poolside', 'ramp', 'Runway',
    'safe_superintelligence', 'scale_ai', 'sierra', 'typeface',
    'unifyAI', 'v7', 'vercel', 'xai', 'aisera', 'anduril',
    'cresta', 'crusoe', 'descript', 'helsing', 'suno', 'synthesia'
]

class InteractivePEAgent:
    """Interactive agent that responds to natural language queries."""
    
    def __init__(self):
        self.client = client
        self.model = "gpt-4o-mini"
        self.conversation_history = []
        self.logger = None
        
    async def call_tool(self, tool_name: str, **kwargs):
        """Call a tool with proper Pydantic models."""
        try:
            if tool_name == "get_payload":
                request = PayloadRequest(company_id=kwargs.get('company_id'))
                result = await get_latest_structured_payload(request)
                # Convert Pydantic to dict
                return result.model_dump() if hasattr(result, 'model_dump') else result.dict()
                
            elif tool_name == "rag_search":
                request = RAGSearchRequest(
                    company_id=kwargs.get('company_id'),
                    query=kwargs.get('query')
                )
                result = await rag_search_company(request)
                return result.model_dump() if hasattr(result, 'model_dump') else result.dict()
                
            elif tool_name == "report_risk":
                signal = LayoffSignal(**kwargs.get('signal_data', {}))
                result = await report_layoff_signal(signal)
                return result.model_dump() if hasattr(result, 'model_dump') else result.dict()
            
            elif tool_name == "generate_dashboard" or tool_name == "run_due_diligence":
                # Run the due diligence workflow
                company_id = kwargs.get('company_id')
                auto_approve = kwargs.get('auto_approve', False)  # HITL enabled by default
                
                if not company_id:
                    return {"error": "company_id is required"}
                
                print(f"\n🔄 Running due diligence workflow for {company_id}...")
                print("   (This may take 10-30 seconds)")
                if not auto_approve:
                    print("   ⚠️  HITL enabled - workflow will pause for human approval if risks detected\n")
                else:
                    print("   (Auto-approve mode enabled)\n")
                
                # Run workflow (HITL enabled by default)
                workflow_result = await run_workflow(company_id, auto_approve=auto_approve)
                
                # Extract key information
                result = {
                    "success": workflow_result.get("error") is None,
                    "company_id": company_id,
                    "dashboard_generated": workflow_result.get("dashboard_markdown") is not None,
                    "dashboard_score": workflow_result.get("dashboard_score"),
                    "risks_detected": len(workflow_result.get("risk_keywords", [])),
                    "branch_taken": workflow_result.get("branch_taken"),
                    "requires_hitl": workflow_result.get("requires_hitl", False),
                    "dashboard_file": workflow_result.get("metadata", {}).get("dashboard_file"),
                    "trace_file": workflow_result.get("metadata", {}).get("trace_file"),
                    "dashboard_preview": workflow_result.get("dashboard_markdown", "")[:500] + "..." if workflow_result.get("dashboard_markdown") else None
                }
                
                if workflow_result.get("error"):
                    result["error"] = workflow_result["error"]
                
                return result
            else:
                return {"error": f"Unknown tool: {tool_name}"}
        except Exception as e:
            return {"error": f"Tool error: {str(e)}"}
    
    async def process_query(self, user_query: str) -> str:
        """Process user query using agent reasoning."""
        
        # Add user message to history
        self.conversation_history.append({
            "role": "user",
            "content": user_query
        })
        
        # System prompt with tool descriptions
        system_prompt = f"""You are a PE (Private Equity) Due Diligence Assistant specializing in the Forbes AI 50 companies.

You have access to the following tools:

1. **get_payload(company_id)**: Get structured company data (funding, valuation, team, etc.)
   - Returns: company name, valuation, funding, CEO, HQ, employees, etc.
   - Use when user asks about company basics or overview

2. **rag_search(company_id, query)**: Search company documents for specific information
   - Use when user asks specific questions that need detailed context
   - Example: "What did they say about their AI model?"

3. **generate_dashboard(company_id)**: Run full due diligence workflow and generate comprehensive dashboard
   - Use when user asks for: "dashboard", "due diligence", "full analysis", "generate report", "comprehensive analysis"
   - This runs the complete workflow: retrieves data, generates dashboard, evaluates quality, detects risks
   - If risks are detected, workflow will pause for human approval (HITL)
   - Returns: dashboard file path, score, risks detected, execution trace
   - Takes 10-30 seconds to complete (may take longer if HITL pause occurs)

**Available companies:** {', '.join(AVAILABLE_COMPANIES[:10])}... and 36 more.

**Guidelines:**
- Start with get_payload to get basic info
- Use rag_search for detailed questions
- Use generate_dashboard when user explicitly asks for dashboard, due diligence, or full analysis
- If company not in Forbes AI 50, say so politely
- Always cite data from tools
- Be concise and data-driven
- When dashboard is generated, mention the file path and key metrics (score, risks)

**Example flows:**
User: "What is Anthropic's valuation?"
→ Call get_payload(company_id="anthropic")
→ Extract valuation from payload
→ Respond: "Anthropic is valued at $X billion according to the latest data."

User: "Generate a dashboard for Anthropic" or "I need a dashboard on Anthropic"
→ Call generate_dashboard(company_id="anthropic")
→ Wait for completion
→ Respond with dashboard summary, score, risks, and file location
"""

        messages = [
            {"role": "system", "content": system_prompt},
            *self.conversation_history[-5:]  # Last 5 messages for context
        ]
        
        # Define tools for OpenAI function calling
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_payload",
                    "description": "Get structured company data including funding, valuation, team, products",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "company_id": {
                                "type": "string",
                                "description": "Company identifier (lowercase, underscores for spaces)"
                            }
                        },
                        "required": ["company_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "rag_search",
                    "description": "Search company documents for specific information",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "company_id": {
                                "type": "string",
                                "description": "Company identifier"
                            },
                            "query": {
                                "type": "string",
                                "description": "Search query"
                            }
                        },
                        "required": ["company_id", "query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "generate_dashboard",
                    "description": "Run full due diligence workflow and generate comprehensive dashboard for a company. Use when user asks for dashboard, due diligence, full analysis, or comprehensive report. This executes the complete workflow including data retrieval, dashboard generation, quality evaluation, and risk detection.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "company_id": {
                                "type": "string",
                                "description": "Company identifier (lowercase, underscores for spaces)"
                            },
                            "auto_approve": {
                                "type": "boolean",
                                "description": "Auto-approve HITL checkpoints (default: false - HITL enabled)",
                                "default": False
                            }
                        },
                        "required": ["company_id"]
                    }
                }
            }
        ]
        
        # Call OpenAI with tools
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )
        
        assistant_message = response.choices[0].message
        
        # Check if agent wants to use tools
        if assistant_message.tool_calls:
            # Add assistant's tool calls to messages
            messages.append({
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in assistant_message.tool_calls
                ]
            })
            
            # Process each tool call
            for tool_call in assistant_message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                print(f"🔧 Agent using tool: {function_name}({function_args})")
                
                # Call the tool
                tool_result = await self.call_tool(function_name, **function_args)
                
                # Add tool result to messages
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(tool_result)
                })
            
            # Get final response after tool use
            final_response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages
            )
            
            final_text = final_response.choices[0].message.content
        else:
            final_text = assistant_message.content
        
        # Add to history
        self.conversation_history.append({
            "role": "assistant",
            "content": final_text
        })
        
        return final_text


async def interactive_chat():
    """Run interactive chat session."""
    agent = InteractivePEAgent()
    
    print("=" * 70)
    print("🤖 INTERACTIVE PE AGENT - Forbes AI 50 Due Diligence")
    print("=" * 70)
    print("\n💡 Ask me anything about the Forbes AI 50 companies!")
    print("\nExamples:")
    print("  • What is Anthropic's valuation?")
    print("  • Tell me about OpenAI's funding history")
    print("  • What are the risks for Cohere?")
    print("  • Generate a dashboard for Anthropic")
    print("  • I need a due diligence report on Cohere")
    print("  • Run full analysis on Mistral AI")
    print("\nType 'exit' to quit, 'companies' to see all companies\n")
    
    while True:
        try:
            # Get user input
            user_input = input("You: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() == 'exit':
                print("\n👋 Goodbye!")
                break
            
            if user_input.lower() == 'companies':
                print("\n📋 Available Companies:")
                for i, company in enumerate(AVAILABLE_COMPANIES, 1):
                    print(f"  {i:2d}. {company}")
                print()
                continue
            
            # Process query
            print("\n🤔 Agent thinking...\n")
            response = await agent.process_query(user_input)
            
            print(f"\n🤖 Agent: {response}\n")
            print("-" * 70 + "\n")
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {str(e)}\n")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    # Load environment
    from dotenv import load_dotenv
    import json
    load_dotenv()
    
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Error: OPENAI_API_KEY not found in environment")
        print("Set it in your .env file")
        sys.exit(1)
    
    # Run interactive chat
    asyncio.run(interactive_chat())