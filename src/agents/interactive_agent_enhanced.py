"""
Enhanced Interactive PE Agent - Returns tool usage information
For Streamlit integration
"""

import os
import sys
import json
from pathlib import Path
from typing import Optional, Dict, List, Tuple
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
from src.agents.advanced_tools import (
    calculate_financial_metrics,
    compare_competitors,
    generate_investment_recommendation,
    analyze_market_trends,
    calculate_risk_score
)
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


class EnhancedInteractivePEAgent:
    """Enhanced interactive agent that tracks and returns tool usage."""
    
    def __init__(self):
        self.client = client
        self.model = "gpt-4o-mini"
        self.conversation_history = []
        self.tool_usage_history = []  # Track all tool calls
        
    async def call_tool(self, tool_name: str, **kwargs) -> Dict:
        """Call a tool with proper Pydantic models."""
        try:
            tool_call_info = {
                "tool_name": tool_name,
                "arguments": kwargs,
                "timestamp": None,
                "result": None,
                "success": False
            }
            
            if tool_name == "get_payload":
                request = PayloadRequest(company_id=kwargs.get('company_id'))
                result = await get_latest_structured_payload(request)
                tool_call_info["result"] = result.model_dump() if hasattr(result, 'model_dump') else result.dict()
                tool_call_info["success"] = True
                
            elif tool_name == "rag_search":
                request = RAGSearchRequest(
                    company_id=kwargs.get('company_id'),
                    query=kwargs.get('query')
                )
                result = await rag_search_company(request)
                tool_call_info["result"] = result.model_dump() if hasattr(result, 'model_dump') else result.dict()
                tool_call_info["success"] = True
                
            elif tool_name == "report_risk":
                signal = LayoffSignal(**kwargs.get('signal_data', {}))
                result = await report_layoff_signal(signal)
                tool_call_info["result"] = result.model_dump() if hasattr(result, 'model_dump') else result.dict()
                tool_call_info["success"] = True
            
            elif tool_name == "generate_dashboard" or tool_name == "run_due_diligence":
                company_id = kwargs.get('company_id')
                auto_approve = kwargs.get('auto_approve', True)  # Default to auto-approve for Streamlit
                
                if not company_id:
                    tool_call_info["result"] = {"error": "company_id is required"}
                    return tool_call_info
                
                workflow_result = await run_workflow(company_id, auto_approve=auto_approve)
                
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
                
                tool_call_info["result"] = result
                tool_call_info["success"] = not workflow_result.get("error")
                
            # Advanced tools
            elif tool_name == "calculate_financial_metrics":
                result = await calculate_financial_metrics(kwargs.get('company_id'))
                tool_call_info["result"] = result
                tool_call_info["success"] = "error" not in result
                
            elif tool_name == "compare_competitors":
                result = await compare_competitors(kwargs.get('company_ids', []))
                tool_call_info["result"] = result
                tool_call_info["success"] = "error" not in result
                
            elif tool_name == "generate_investment_recommendation":
                result = await generate_investment_recommendation(kwargs.get('company_id'))
                tool_call_info["result"] = result
                tool_call_info["success"] = "error" not in result
                
            elif tool_name == "analyze_market_trends":
                result = await analyze_market_trends(kwargs.get('sector', 'AI'))
                tool_call_info["result"] = result
                tool_call_info["success"] = "error" not in result
                
            elif tool_name == "calculate_risk_score":
                result = await calculate_risk_score(kwargs.get('company_id'))
                tool_call_info["result"] = result
                tool_call_info["success"] = "error" not in result
                
            else:
                tool_call_info["result"] = {"error": f"Unknown tool: {tool_name}"}
            
            from datetime import datetime
            tool_call_info["timestamp"] = datetime.now().isoformat()
            self.tool_usage_history.append(tool_call_info)
            
            return tool_call_info["result"]
            
        except Exception as e:
            tool_call_info["result"] = {"error": f"Tool error: {str(e)}"}
            tool_call_info["success"] = False
            from datetime import datetime
            tool_call_info["timestamp"] = datetime.now().isoformat()
            self.tool_usage_history.append(tool_call_info)
            return tool_call_info["result"]
    
    async def process_query(self, user_query: str) -> Tuple[str, List[Dict]]:
        """
        Process user query and return response + tool usage info.
        
        Returns:
            Tuple of (response_text, tool_usage_list)
        """
        # Clear tool usage for this query
        query_tool_calls = []
        
        # Add user message to history
        self.conversation_history.append({
            "role": "user",
            "content": user_query
        })
        
        # System prompt with all tools
        system_prompt = f"""You are a PE (Private Equity) Due Diligence Assistant specializing in the Forbes AI 50 companies.

You have access to the following tools:

**Basic Tools:**
1. **get_payload(company_id)**: Get structured company data (funding, valuation, team, etc.)
2. **rag_search(company_id, query)**: Search company documents for specific information
3. **generate_dashboard(company_id)**: Run full due diligence workflow and generate comprehensive dashboard

**Advanced Tools:**
4. **calculate_financial_metrics(company_id)**: Calculate financial ratios and efficiency metrics
5. **compare_competitors(company_ids)**: Compare multiple companies side-by-side
6. **generate_investment_recommendation(company_id)**: Get BUY/HOLD/PASS recommendation with score
7. **analyze_market_trends(sector)**: Analyze market trends across Forbes AI 50
8. **calculate_risk_score(company_id)**: Comprehensive risk assessment (0-100)

**Available companies:** {', '.join(AVAILABLE_COMPANIES[:10])}... and 36 more.

**Guidelines:**
- Use appropriate tools based on user query
- For financial analysis, use calculate_financial_metrics
- For comparisons, use compare_competitors
- For investment decisions, use generate_investment_recommendation
- For risk assessment, use calculate_risk_score
- Always cite data from tools
- Be concise and data-driven
"""

        messages = [
            {"role": "system", "content": system_prompt},
            *self.conversation_history[-5:]  # Last 5 messages for context
        ]
        
        # Define all tools for OpenAI function calling
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
                            "company_id": {"type": "string", "description": "Company identifier"},
                            "query": {"type": "string", "description": "Search query"}
                        },
                        "required": ["company_id", "query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "generate_dashboard",
                    "description": "Run full due diligence workflow and generate comprehensive dashboard",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "company_id": {"type": "string", "description": "Company identifier"},
                            "auto_approve": {"type": "boolean", "description": "Auto-approve HITL", "default": True}
                        },
                        "required": ["company_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "calculate_financial_metrics",
                    "description": "Calculate financial metrics and ratios for a company",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "company_id": {"type": "string", "description": "Company identifier"}
                        },
                        "required": ["company_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "compare_competitors",
                    "description": "Compare multiple companies side-by-side",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "company_ids": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of company IDs to compare"
                            }
                        },
                        "required": ["company_ids"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "generate_investment_recommendation",
                    "description": "Get BUY/HOLD/PASS investment recommendation with score",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "company_id": {"type": "string", "description": "Company identifier"}
                        },
                        "required": ["company_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "analyze_market_trends",
                    "description": "Analyze market trends across Forbes AI 50",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "sector": {"type": "string", "description": "Industry sector", "default": "AI"}
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "calculate_risk_score",
                    "description": "Calculate comprehensive risk score (0-100) for a company",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "company_id": {"type": "string", "description": "Company identifier"}
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
                
                # Track this tool call
                tool_info = {
                    "tool_name": function_name,
                    "arguments": function_args,
                    "timestamp": None
                }
                
                # Call the tool
                tool_result = await self.call_tool(function_name, **function_args)
                
                # Get the last tool call info (added by call_tool)
                if self.tool_usage_history:
                    last_tool = self.tool_usage_history[-1]
                    tool_info.update({
                        "result": last_tool.get("result"),
                        "success": last_tool.get("success"),
                        "timestamp": last_tool.get("timestamp")
                    })
                
                query_tool_calls.append(tool_info)
                
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
        
        return final_text, query_tool_calls
    
    def get_tool_usage_history(self) -> List[Dict]:
        """Get all tool usage history."""
        return self.tool_usage_history
    
    def clear_history(self):
        """Clear conversation and tool history."""
        self.conversation_history = []
        self.tool_usage_history = []

