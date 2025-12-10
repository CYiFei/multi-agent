from typing import Dict, Any, List, Optional, Callable
import uuid
import time
import logging
from .base_agent import AgentStatus
from .task import Task, TaskStatus
from messaging.message import Message, MessageType

# 为了解决循环导入问题，在这里添加对 BasicAgent 的前向引用
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .agent_impl import BasicAgent

class TaskEngine:
    """任务处理引擎"""
    
    def __init__(self, agent: 'BasicAgent'):
        self.agent = agent
        self.logger = logging.getLogger(f"task_engine.{agent.agent_id}")
        self.tasks: Dict[str, Task] = {}  # 本地任务缓存
        self.task_processors: Dict[str, Callable[[Task], Dict[str, Any]]] = {}
        
        # 注册默认的任务处理器
        self._register_default_processors()
        
        # 注册任务相关消息处理器
        self.agent.register_handler("task_assignment", self._handle_task_assignment)
        self.agent.register_handler("task_completion", self._handle_task_completion)
        self.agent.register_handler("task_failure", self._handle_task_failure)
    
    def _register_default_processors(self) -> None:
        """注册默认任务处理器"""
        self.register_task_processor("default", self._process_default_task)
    
    def register_task_processor(self, task_type: str, processor: Callable[[Task], Dict[str, Any]]) -> None:
        """注册任务处理器"""
        if not callable(processor):
            raise ValueError("Processor must be callable")
        self.task_processors[task_type] = processor
    
    def submit_task(self, task: Task) -> str:
        """提交任务到系统"""
        self.tasks[task.task_id] = task
        self.logger.info(f"Task {task.task_id} submitted")
        
        # 如果任务分配给了当前智能体，则开始处理
        if task.assigned_agent == self.agent.agent_id:
            self._process_assigned_task(task)
        
        return task.task_id
    
    def create_and_submit_task(
        self,
        description: str,
        payload: Dict[str, Any],
        priority: int = 2,
        assigned_agent: Optional[str] = None
    ) -> str:
        """创建并提交任务"""
        task = Task(
            task_id=None,
            description=description,
            payload=payload,
            priority=priority,
            creator_id=self.agent.agent_id,
            assigned_agent=assigned_agent
        )
        return self.submit_task(task)
    
    def _process_assigned_task(self, task: Task) -> None:
        """处理分配给当前智能体的任务"""
        try:
            # 更新状态
            task.start_execution()
            self.logger.info(f"Starting execution of task {task.task_id}")
            
            # 查找合适的处理器
            task_type = task.payload.get("task_type", "default")
            processor = self.task_processors.get(task_type)
            
            if not processor:
                # 尝试使用默认处理器
                processor = self.task_processors.get("default")
            
            if processor:
                # 执行任务
                result = processor(task)
                task.complete(result)
                
                # 发送完成通知
                self._notify_task_completion(task)
            else:
                error_msg = f"No processor found for task type: {task_type}"
                self.logger.error(error_msg)
                task.fail(error_msg)
                self._notify_task_failure(task)
                
        except Exception as e:
            self.logger.error(f"Error processing task {task.task_id}: {e}")
            task.fail(str(e))
            self._notify_task_failure(task)
    
    def _process_default_task(self, task: Task) -> Dict[str, Any]:
        """默认任务处理器"""
        self.logger.info(f"Processing default task: {task.description}")
        
        # 模拟任务处理
        time.sleep(0.1)  # 模拟处理时间
        
        return {
            "status": "success",
            "result": f"Processed task: {task.description}",
            "processed_by": self.agent.agent_id
        }
    
    def _notify_task_completion(self, task: Task) -> None:
        """通知任务完成"""
        if task.creator_id:
            message = Message(
                sender_id=self.agent.agent_id,
                receiver_id=task.creator_id,
                msg_type="task_completion",
                content={
                    "task_id": task.task_id,
                    "result": task.result
                }
            )
            self.agent.router.route_message(message)
    
    def _notify_task_failure(self, task: Task) -> None:
        """通知任务失败"""
        if task.creator_id:
            message = Message(
                sender_id=self.agent.agent_id,
                receiver_id=task.creator_id,
                msg_type="task_failure",
                content={
                    "task_id": task.task_id,
                    "error": task.result.get("error") if task.result else "Unknown error"
                }
            )
            self.agent.router.route_message(message)
    
    def _handle_task_assignment(self, message: Message) -> Dict[str, Any]:
        """处理任务分配消息"""
        task_data = message.content.get("task", {})
        task = Task(
            task_id=task_data["task_id"],
            description=task_data["description"],
            payload=task_data["payload"],
            priority=task_data["priority"],
            creator_id=task_data["creator_id"],
            assigned_agent=task_data["assigned_agent"]
        )
        
        # 更新依赖
        for dep_id in task_data.get("dependencies", []):
            task.add_dependency(dep_id)
        
        return {"status": "accepted", "task_id": task.task_id}
    
    def _handle_task_completion(self, message: Message) -> Dict[str, Any]:
        """处理任务完成消息"""
        task_id = message.content.get("task_id")
        result = message.content.get("result")
        
        if task_id in self.tasks:
            task = self.tasks[task_id]
            task.complete(result)
            self.logger.info(f"Task {task_id} completed with result: {result}")
        
        return {"status": "acknowledged"}
    
    def _handle_task_failure(self, message: Message) -> Dict[str, Any]:
        """处理任务失败消息"""
        task_id = message.content.get("task_id")
        error = message.content.get("error")
        
        if task_id in self.tasks:
            task = self.tasks[task_id]
            task.fail(error)
            self.logger.warning(f"Task {task_id} failed with error: {error}")
        
        return {"status": "acknowledged"}
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        task = self.tasks.get(task_id)
        return task.to_dict() if task else None
    
    def get_all_tasks(self) -> List[Dict[str, Any]]:
        """获取所有任务状态"""
        return [task.to_dict() for task in self.tasks.values()]