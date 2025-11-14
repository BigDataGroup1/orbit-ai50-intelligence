"""
ReAct Logger - Structured Logging for Agent Reasoning
Logs: Thought → Action → Observation triplets
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import uuid

logger = logging.getLogger(__name__)


class ReActLogger:
    """Structured logger for ReAct (Reasoning + Acting) pattern."""
    
    def __init__(self, run_id: str = None, company_id: str = None):
        """
        Initialize ReAct logger.
        
        Args:
            run_id: Unique identifier for this agent run
            company_id: Company being analyzed
        """
        self.run_id = run_id or str(uuid.uuid4())
        self.company_id = company_id
        self.start_time = datetime.now()
        
        # Log storage
        self.thoughts: List[Dict] = []
        self.actions: List[Dict] = []
        self.observations: List[Dict] = []
        self.steps: List[Dict] = []
        
        # Create logs directory
        project_root = Path(__file__).resolve().parents[2]
        self.log_dir = project_root / "logs" / "react_traces"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"🚀 ReAct Logger initialized: run_id={self.run_id}, company={company_id}")
    
    def log_thought(self, thought: str, step_num: int = None) -> Dict:
        """
        Log an agent's reasoning/thought.
        
        Args:
            thought: The agent's internal reasoning
            step_num: Optional step number
            
        Returns:
            Thought log entry
        """
        entry = {
            "type": "thought",
            "run_id": self.run_id,
            "company_id": self.company_id,
            "step": step_num or len(self.thoughts) + 1,
            "timestamp": datetime.now().isoformat(),
            "content": thought
        }
        
        self.thoughts.append(entry)
        logger.info(f"💭 Thought {entry['step']}: {thought[:100]}...")
        
        return entry
    
    def log_action(self, tool_name: str, tool_input: Dict, step_num: int = None) -> Dict:
        """
        Log a tool/action execution.
        
        Args:
            tool_name: Name of the tool being called
            tool_input: Input parameters to the tool
            step_num: Optional step number
            
        Returns:
            Action log entry
        """
        entry = {
            "type": "action",
            "run_id": self.run_id,
            "company_id": self.company_id,
            "step": step_num or len(self.actions) + 1,
            "timestamp": datetime.now().isoformat(),
            "tool_name": tool_name,
            "tool_input": tool_input
        }
        
        self.actions.append(entry)
        logger.info(f"⚡ Action {entry['step']}: {tool_name}({tool_input})")
        
        return entry
    
    def log_observation(self, observation: str, success: bool = True, step_num: int = None) -> Dict:
        """
        Log the result/observation from an action.
        
        Args:
            observation: What the agent observed after the action
            success: Whether the action succeeded
            step_num: Optional step number
            
        Returns:
            Observation log entry
        """
        entry = {
            "type": "observation",
            "run_id": self.run_id,
            "company_id": self.company_id,
            "step": step_num or len(self.observations) + 1,
            "timestamp": datetime.now().isoformat(),
            "success": success,
            "content": observation
        }
        
        self.observations.append(entry)
        status = "✅" if success else "❌"
        logger.info(f"{status} Observation {entry['step']}: {observation[:100]}...")
        
        return entry
    
    def log_step(self, thought: str, action_name: str, action_input: Dict, 
                  observation: str, success: bool = True) -> Dict:
        """
        Log a complete ReAct step (Thought → Action → Observation).
        
        Args:
            thought: Agent's reasoning
            action_name: Tool to execute
            action_input: Tool parameters
            observation: Result of the action
            success: Whether action succeeded
            
        Returns:
            Complete step log entry
        """
        step_num = len(self.steps) + 1
        
        step = {
            "step_number": step_num,
            "run_id": self.run_id,
            "company_id": self.company_id,
            "timestamp": datetime.now().isoformat(),
            "thought": thought,
            "action": {
                "name": action_name,
                "input": action_input
            },
            "observation": {
                "success": success,
                "content": observation
            }
        }
        
        self.steps.append(step)
        
        logger.info(f"\n{'='*70}")
        logger.info(f"STEP {step_num}")
        logger.info(f"{'='*70}")
        logger.info(f"💭 Thought: {thought}")
        logger.info(f"⚡ Action: {action_name}({action_input})")
        logger.info(f"{'✅' if success else '❌'} Observation: {observation[:200]}...")
        
        return step
    
    def save_trace(self, final_output: Optional[str] = None) -> Path:
        """
        Save the complete ReAct trace to a JSON file.
        
        Args:
            final_output: Optional final result/conclusion
            
        Returns:
            Path to the saved trace file
        """
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()
        
        trace = {
            "run_id": self.run_id,
            "company_id": self.company_id,
            "start_time": self.start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": duration,
            "total_steps": len(self.steps),
            "steps": self.steps,
            "final_output": final_output,
            "metadata": {
                "total_thoughts": len(self.thoughts),
                "total_actions": len(self.actions),
                "total_observations": len(self.observations),
                "successful_observations": sum(1 for o in self.observations if o.get("success", True))
            }
        }
        
        # Save to file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"react_trace_{self.company_id}_{timestamp}.json"
        filepath = self.log_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(trace, f, indent=2)
        
        logger.info(f"\n{'='*70}")
        logger.info(f"✅ ReAct trace saved: {filepath}")
        logger.info(f"   Run ID: {self.run_id}")
        logger.info(f"   Steps: {len(self.steps)}")
        logger.info(f"   Duration: {duration:.2f}s")
        logger.info(f"{'='*70}\n")
        
        return filepath
    
    def get_summary(self) -> Dict:
        """Get a summary of the ReAct trace."""
        return {
            "run_id": self.run_id,
            "company_id": self.company_id,
            "total_steps": len(self.steps),
            "total_thoughts": len(self.thoughts),
            "total_actions": len(self.actions),
            "total_observations": len(self.observations),
            "duration_seconds": (datetime.now() - self.start_time).total_seconds()
        }