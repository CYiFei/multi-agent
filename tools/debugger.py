"""
Visualization Debugging Interface for Multi-Agent System
"""
from typing import Dict, List, Any, Optional
import json
import time
from datetime import datetime
from agents.base_agent import AgentStatus
from agents.task import TaskStatus
from runtime.types import RuntimeManagerInterface

class VisualDebugger:
    """可视化调试器"""
    
    def __init__(self, runtime_manager: RuntimeManagerInterface):
        self.runtime_manager = runtime_manager
        self.debug_session_active = False
        self.debug_data = {
            "sessions": [],
            "current_session": None
        }
    
    def start_debug_session(self, session_name: str = None) -> str:
        """开始调试会话"""
        if not session_name:
            session_name = f"session_{int(time.time())}"
            
        session = {
            "id": session_name,
            "start_time": time.time(),
            "events": [],
            "snapshots": []
        }
        
        self.debug_data["current_session"] = session
        self.debug_data["sessions"].append(session)
        self.debug_session_active = True
        
        return session_name
    
    def capture_system_snapshot(self, snapshot_name: str = None) -> Dict[str, Any]:
        """捕获系统快照"""
        if not snapshot_name:
            snapshot_name = f"snapshot_{int(time.time())}"
            
        # 获取系统状态
        system_status = self.runtime_manager.get_system_status()
        
        # 获取所有智能体状态
        agents = self.runtime_manager.get_all_agents()
        agent_states = {}
        for agent_id, agent in agents.items():
            agent_states[agent_id] = {
                "status": agent.status.value,
                "name": agent.name,
                "tasks": []
            }
            
            # 如果智能体有任务引擎，获取任务信息
            if hasattr(agent, 'task_engine'):
                agent_states[agent_id]["tasks"] = agent.task_engine.get_all_tasks()
        
        snapshot = {
            "name": snapshot_name,
            "timestamp": time.time(),
            "system_status": system_status,
            "agent_states": agent_states
        }
        
        # 添加到当前会话
        if self.debug_data["current_session"]:
            self.debug_data["current_session"]["snapshots"].append(snapshot)
            
        return snapshot
    
    def log_event(self, event_type: str, source: str, details: Dict[str, Any]) -> None:
        """记录调试事件"""
        event = {
            "timestamp": time.time(),
            "type": event_type,
            "source": source,
            "details": details
        }
        
        # 添加到当前会话
        if self.debug_data["current_session"]:
            self.debug_data["current_session"]["events"].append(event)
    
    def get_debug_data(self) -> Dict[str, Any]:
        """获取调试数据"""
        return self.debug_data
    
    def export_debug_session(self, session_id: str = None) -> str:
        """导出调试会话数据为JSON"""
        if not session_id and self.debug_data["current_session"]:
            session = self.debug_data["current_session"]
        else:
            session = next((s for s in self.debug_data["sessions"] if s["id"] == session_id), None)
            
        if not session:
            return "{}"
            
        return json.dumps(session, indent=2, default=str)
    
    def get_agent_interaction_graph(self) -> Dict[str, Any]:
        """生成智能体交互图数据"""
        agents = self.runtime_manager.get_all_agents()
        
        nodes = []
        edges = []
        
        # 创建节点
        for agent_id, agent in agents.items():
            nodes.append({
                "id": agent_id,
                "label": agent.name,
                "status": agent.status.value
            })
        
        # 创建边（基于消息传递，这里简化处理）
        # 在实际实现中，可以通过拦截消息路由器来跟踪真实的交互
        agent_ids = list(agents.keys())
        for i in range(len(agent_ids)):
            for j in range(i+1, len(agent_ids)):
                # 添加示例边
                edges.append({
                    "from": agent_ids[i],
                    "to": agent_ids[j],
                    "label": "interaction"
                })
        
        return {
            "nodes": nodes,
            "edges": edges
        }