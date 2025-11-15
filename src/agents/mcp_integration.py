"""
Lab 15: MCP Integration for Supervisor Agent
Handles MCP server communication and tool invocation
"""
import json
import requests
from typing import Dict, Optional
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))


class MCPIntegration:
    """
    MCP Integration helper for Supervisor Agent.
    Handles configuration loading, tool invocation, and security filtering.
    """
    
    def __init__(self):
        """Initialize MCP integration with config."""
        self.config = self._load_config()
        self.enabled = self.config.get("mcp_server", {}).get("enabled", False)
        self.base_url = self.config.get("mcp_server", {}).get("base_url", "http://localhost:8001")
        self.allowed_tools = self.config.get("security", {}).get("allowed_tools", [])
        self.timeout = self.config.get("mcp_server", {}).get("timeout", 30)
        
        if self.enabled:
            print(f"   MCP: enabled ({self.base_url})")
        else:
            print(f"   MCP: disabled")
    
    def _load_config(self) -> Dict:
        """Load MCP configuration from mcp_config.json."""
        config_path = project_root / "mcp_config.json"
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️  Failed to load MCP config: {e}")
        return {}
    
    def is_enabled(self) -> bool:
        """Check if MCP is enabled."""
        return self.enabled
    
    def call_tool(self, tool_name: str, payload: Dict) -> Dict:
        """
        Call MCP tool with security filtering.
        
        Args:
            tool_name: Name of the tool (e.g., "generate_structured_dashboard")
            payload: Request payload
            
        Returns:
            Response from MCP server
        """
        if not self.enabled:
            return {"success": False, "error": "MCP is disabled"}
        
        # Security check - tool filtering
        if self.allowed_tools and tool_name not in self.allowed_tools:
            return {"success": False, "error": f"Tool '{tool_name}' is not allowed by security config"}
        
        # Get endpoint from config
        tool_config = self.config.get("tools", {}).get(tool_name, {})
        endpoint = tool_config.get("endpoint", f"/tool/{tool_name}")
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = requests.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.ConnectionError:
            return {"success": False, "error": f"Could not connect to MCP server at {self.base_url}. Is it running?"}
        except requests.exceptions.Timeout:
            return {"success": False, "error": f"Request to MCP server timed out after {self.timeout}s"}
        except requests.exceptions.HTTPError as e:
            return {"success": False, "error": f"MCP server error: {e.response.status_code} - {e.response.text}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_companies(self) -> Dict:
        """
        Get list of companies from MCP resource.
        
        Returns:
            Response with companies list
        """
        if not self.enabled:
            return {"success": False, "error": "MCP is disabled"}
        
        endpoint = self.config.get("resources", {}).get("ai50_companies", {}).get("endpoint", "/resource/ai50/companies")
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_prompt(self, prompt_type: str = "rag") -> Dict:
        """
        Get prompt template from MCP.
        
        Args:
            prompt_type: "rag" or "structured"
            
        Returns:
            Response with prompt content
        """
        if not self.enabled:
            return {"success": False, "error": "MCP is disabled"}
        
        endpoint = self.config.get("prompts", {}).get("pe_dashboard", {}).get("endpoint", "/prompt/pe-dashboard")
        url = f"{self.base_url}{endpoint}?prompt_type={prompt_type}"
        
        try:
            response = requests.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def health_check(self) -> Dict:
        """Check MCP server health."""
        if not self.enabled:
            return {"status": "disabled"}
        
        url = f"{self.base_url}/health"
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}


# Singleton instance
_mcp_integration = None


def get_mcp_integration() -> MCPIntegration:
    """Get or create MCP integration singleton."""
    global _mcp_integration
    if _mcp_integration is None:
        _mcp_integration = MCPIntegration()
    return _mcp_integration

