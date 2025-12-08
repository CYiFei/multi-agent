from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import threading
import time
from enum import Enum

from .message_system import Message, MessageType, MessageBus, MessageRouter

class AgentStatus(Enum):
    """智能体状态枚举"""
    INITIALIZING = "initializing"
    ACTIVE = "active"
    IDLE = "idle"
    PROCESSING = "processing"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"

class Agent(ABC):
    """智能体基础抽象类"""
    
    def __init__(self, agent_id: str, name: str):
        self.agent_id = agent_id
        self.name = name
        self.status = AgentStatus.INITIALIZING
        self.message_bus = MessageBus()
        self.message_router = MessageRouter(self.message_bus)
        self.message_topic = f"agent.{agent_id}"
        self._state: Dict[str, Any] = {}
        self._message_handlers: Dict[str, Callable[[Message], Any]] = {}
        self._setup_message_handling()
        self._lifecycle_thread = None
        self._stop_flag = threading.Event()
    
    def _setup_message_handling(self):
        """设置消息处理机制"""
        # 注册到消息路由器
        self.message_router.register_agent(self.agent_id, self.message_topic)
        # 订阅自己的主题
        self.message_bus.subscribe(self.message_topic, self._handle_incoming_message)
        # 订阅系统命令
        self.message_bus.subscribe(f"system.command.{self.agent_id}", self._handle_system_command)
        
        # 注册默认处理器
        self.register_message_handler(MessageType.TASK.value, self.handle_task)
        self.register_message_handler(MessageType.SYSTEM.value, self.handle_system_message)
    
    def register_message_handler(self, msg_type: str, handler: Callable[[Message], Any]):
        """注册消息处理器"""
        self._message_handlers[msg_type] = handler
    
    def _handle_incoming_message(self, message: Message):
        """处理入站消息"""
        handler = self._message_handlers.get(message.msg_type, self.handle_unknown_message)
        try:
            self.status = AgentStatus.PROCESSING
            handler(message)
        finally:
            if self.status == AgentStatus.PROCESSING:
                self.status = AgentStatus.IDLE
    
    def _handle_system_command(self, message: Message):
        """处理系统命令"""
        command = message.content.get("command")
        if command == "shutdown":
            self.terminate()
        elif command == "status":
            self._respond_status(message.sender_id)
        elif command == "suspend":
            self.suspend()
        elif command == "resume":
            self.resume()
    
    def _respond_status(self, requester_id: str):
        """响应状态查询"""
        status_message = Message(
            sender_id=self.agent_id,
            receiver_id=requester_id,
            msg_type=MessageType.RESPONSE,
            content={
                "status": self.status.value,
                "agent_id": self.agent_id,
                "name": self.name,
                "timestamp": time.time()
            }
        )
        self.message_router.route_message(status_message)
    
    @abstractmethod
    def handle_task(self, message: Message):
        """处理任务消息（需子类实现）"""
        pass
    
    def handle_system_message(self, message: Message):
        """处理系统消息"""
        print(f"[{self.name}] Received system message: {message.content}")
    
    def handle_unknown_message(self, message: Message):
        """处理未知类型消息"""
        print(f"[{self.name}] Received unknown message type: {message.msg_type}")
    
    def send_message(self, receiver_id: str, msg_type: MessageType, content: Dict[str, Any]):
        """发送消息到其他智能体"""
        return self.message_router.send_message(
            self.agent_id, receiver_id, msg_type, content
        )
    
    def broadcast_message(self, msg_type: MessageType, content: Dict[str, Any]):
        """广播消息"""
        message = Message(
            sender_id=self.agent_id,
            receiver_id="broadcast",
            msg_type=msg_type,
            content=content
        )
        self.message_bus.publish("system.broadcast", message)
    
    # 状态管理
    @property
    def state(self) -> Dict[str, Any]:
        return self._state.copy()
    
    def update_state(self, key: str, value: Any):
        """更新状态"""
        self._state[key] = value
    
    def get_state(self, key: str, default: Any = None) -> Any:
        """获取状态值"""
        return self._state.get(key, default)
    
    # 生命周期管理
    def initialize(self):
        """初始化智能体"""
        self.status = AgentStatus.INITIALIZING
        self._on_initialize()
        self.status = AgentStatus.IDLE
    
    @abstractmethod
    def _on_initialize(self):
        """初始化钩子（需子类实现）"""
        pass
    
    def start(self):
        """启动智能体"""
        if self.status in [AgentStatus.TERMINATED, AgentStatus.INITIALIZING]:
            self.initialize()
        
        if self._lifecycle_thread is None or not self._lifecycle_thread.is_alive():
            self._stop_flag.clear()
            self._lifecycle_thread = threading.Thread(target=self._lifecycle_loop, daemon=True)
            self._lifecycle_thread.start()
            self.status = AgentStatus.ACTIVE
    
    def _lifecycle_loop(self):
        """生命周期主循环"""
        while not self._stop_flag.is_set():
            self._on_idle()
            time.sleep(0.1)  # 避免CPU过度占用
    
    def _on_idle(self):
        """空闲时的处理（可被子类重写）"""
        pass
    
    def suspend(self):
        """暂停智能体"""
        if self.status == AgentStatus.ACTIVE:
            self.status = AgentStatus.SUSPENDED
    
    def resume(self):
        """恢复智能体"""
        if self.status == AgentStatus.SUSPENDED:
            self.status = AgentStatus.ACTIVE
    
    def terminate(self):
        """终止智能体"""
        self._stop_flag.set()
        if self._lifecycle_thread and self._lifecycle_thread.is_alive():
            self._lifecycle_thread.join(timeout=2.0)
        
        # 清理资源
        self.message_bus.unsubscribe(self.message_topic, self._handle_incoming_message)
        self.message_router.unregister_agent(self.agent_id)
        self._on_terminate()
        self.status = AgentStatus.TERMINATED
    
    def _on_terminate(self):
        """终止时的清理（可被子类重写）"""
        pass
    
    def __del__(self):
        """析构函数，确保资源释放"""
        if self.status != AgentStatus.TERMINATED:
            self.terminate()