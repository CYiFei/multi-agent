from typing import Dict, Any, List, Optional
from enum import Enum
import uuid
import time

class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"          # 待处理
    ASSIGNED = "assigned"        # 已分配
    IN_PROGRESS = "in_progress"  # 进行中
    COMPLETED = "completed"      # 已完成
    FAILED = "failed"            # 失败
    CANCELLED = "cancelled"      # 已取消

class Task:
    """任务对象"""
    
    def __init__(
        self,
        task_id: str,
        description: str,
        payload: Dict[str, Any],
        priority: int = 2,
        creator_id: Optional[str] = None,
        assigned_agent: Optional[str] = None
    ):
        self.task_id = task_id or str(uuid.uuid4())
        self.description = description
        self.payload = payload
        self.priority = priority
        self.creator_id = creator_id
        self.assigned_agent = assigned_agent
        self.status = TaskStatus.PENDING
        self.created_at = time.time()
        self.assigned_at: Optional[float] = None
        self.completed_at: Optional[float] = None
        self.result: Optional[Dict[str, Any]] = None
        self.dependencies: List[str] = []  # 依赖的任务ID列表
    
    def assign_to(self, agent_id: str) -> None:
        """分配任务给智能体"""
        self.assigned_agent = agent_id
        self.status = TaskStatus.ASSIGNED
        self.assigned_at = time.time()
    
    def start_execution(self) -> None:
        """开始执行任务"""
        if self.status == TaskStatus.ASSIGNED:
            self.status = TaskStatus.IN_PROGRESS
    
    def complete(self, result: Dict[str, Any]) -> None:
        """完成任务"""
        self.status = TaskStatus.COMPLETED
        self.result = result
        self.completed_at = time.time()
    
    def fail(self, error: str) -> None:
        """标记任务失败"""
        self.status = TaskStatus.FAILED
        self.result = {"error": error}
        self.completed_at = time.time()
    
    def cancel(self) -> None:
        """取消任务"""
        self.status = TaskStatus.CANCELLED
        self.completed_at = time.time()
    
    def add_dependency(self, task_id: str) -> None:
        """添加依赖任务"""
        if task_id not in self.dependencies:
            self.dependencies.append(task_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "description": self.description,
            "payload": self.payload,
            "priority": self.priority,
            "creator_id": self.creator_id,
            "assigned_agent": self.assigned_agent,
            "status": self.status.value,
            "created_at": self.created_at,
            "assigned_at": self.assigned_at,
            "completed_at": self.completed_at,
            "result": self.result,
            "dependencies": self.dependencies
        }