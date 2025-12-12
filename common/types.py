"""
Common type definitions for the multi-agent system
"""
from enum import Enum
from typing import Dict, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from agents.base_agent import Agent
    from agents.task import Task

class AgentStatus(Enum):
    """智能体状态"""
    INITIALIZING = "initializing"
    IDLE = "idle"
    ACTIVE = "active"
    BUSY = "busy"
    SUSPENDED = "suspended"
    TERMINATING = "terminating"
    TERMINATED = "terminated"

class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"          # 待处理
    ASSIGNED = "assigned"        # 已分配
    IN_PROGRESS = "in_progress"  # 进行中
    COMPLETED = "completed"      # 已完成
    FAILED = "failed"            # 失败
    CANCELLED = "cancelled"      # 已取消

class MessageType(Enum):
    """消息类型枚举"""
    TASK = "task"
    RESPONSE = "response"
    SYSTEM = "system"
    NOTIFICATION = "notification"
    BROADCAST = "broadcast"
    CHAT = "chat_message"

class MessagePriority(Enum):
    """消息优先级"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4

class RuntimeManagerInterface:
    """运行时管理器接口定义"""
    
    def get_system_status(self) -> Dict[str, Any]:
        raise NotImplementedError()
    
    def get_agent(self, agent_id: str) -> Optional['Agent']:
        raise NotImplementedError()
    
    def get_all_agents(self) -> Dict[str, 'Agent']:
        raise NotImplementedError()