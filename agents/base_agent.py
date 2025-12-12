from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable, List, Union
import threading
import time

from messaging.message import Message
from messaging.router import MessageRouter
from common.types import AgentStatus, MessageType


class Agent(ABC):
    """智能体基类 - 定义接口规范"""
    
    @abstractmethod
    def __init__(
        self, 
        agent_id: str, 
        name: str, 
        router: MessageRouter
    ):
        """
        初始化智能体
        
        Args:
            agent_id: 智能体唯一标识
            name: 智能体名称
            router: 消息路由器实例
        """
        self.agent_id = agent_id
        self.name = name
        self.router = router
        self.status = AgentStatus.INITIALIZING
        self._lock = threading.Lock()
        self._message_handlers: Dict[str, Callable[[Message], Any]] = {}
        self._setup_handlers()
    
    @abstractmethod
    def _setup_handlers(self) -> None:
        """设置默认消息处理器"""
        super()._setup_handlers()
        # 添加LLM特有的处理器
        self.register_handler("chat_message", self._handle_chat_message)
    
    @abstractmethod
    def handle_message(self, message: Message) -> Any:
        """
        处理接收到的消息
        
        Args:
            message: 接收到的消息对象
            
        Returns:
            处理结果，可以是任何类型
        """
        pass
    
    @abstractmethod
    def get_handler(self, msg_type: str) -> Optional[Callable[[Message], Any]]:
        """
        获取指定类型的消息处理器
        
        Args:
            msg_type: 消息类型
            
        Returns:
            对应的处理器函数或None
        """
        pass
    
    @abstractmethod
    def register_handler(self, msg_type: str, handler: Callable[[Message], Any]) -> None:
        """
        注册消息处理器
        
        Args:
            msg_type: 消息类型
            handler: 处理函数
        """
        pass
    
    @abstractmethod
    def send_message(
        self, 
        receiver_id: str, 
        msg_type: Union[str, MessageType], 
        content: Dict[str, Any],
        priority: int = 2,
        conversation_id: Optional[str] = None
    ) -> str:
        """
        发送消息给其他智能体
        
        Args:
            receiver_id: 接收者ID
            msg_type: 消息类型
            content: 消息内容
            priority: 优先级 (1-4)
            conversation_id: 会话ID
            
        Returns:
            消息ID
        """
        pass
    
    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """
        获取智能体当前状态
        
        Returns:
            状态信息字典
        """
        pass
    
    @abstractmethod
    def start(self) -> None:
        """启动智能体"""
        pass
    
    @abstractmethod
    def stop(self) -> None:
        """停止智能体"""
        pass
    
    @property
    @abstractmethod
    def is_running(self) -> bool:
        """检查智能体是否正在运行"""
        pass