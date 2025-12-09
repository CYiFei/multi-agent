from typing import Dict, Any, Optional, Callable, List, Union
import threading
import time
import logging

from .base_agent import Agent, AgentStatus
from .lifecycle import LifecycleManager
from .state_manager import StateManager
from messaging.message import Message, MessageType
from messaging.router import MessageRouter

class BasicAgent(Agent):
    """基础智能体实现"""
    
    def __init__(
        self, 
        agent_id: str, 
        name: str, 
        router: MessageRouter,
        persistent_state: bool = False,
        state_storage_path: Optional[str] = None
    ):
        """
        初始化基础智能体
        
        Args:
            agent_id: 智能体唯一标识
            name: 智能体名称
            router: 消息路由器
            persistent_state: 是否持久化状态
            state_storage_path: 状态存储路径
        """
        super().__init__(agent_id, name, router)
        
        # 初始化组件
        self.router = router
        self.state_manager = StateManager(agent_id, persistent_state, state_storage_path)
        self.lifecycle = LifecycleManager(self)
        self.logger = logging.getLogger(f"agent.{agent_id}")
        
        # 注册到路由器
        self.router.register_agent(agent_id, f"agent.{agent_id}")
        
        # 设置消息处理器
        self._setup_handlers()
        
        # 初始化完成，更新状态
        self.status = AgentStatus.IDLE
        self.logger.info(f"Agent {agent_id} initialized successfully")
    
    def _setup_handlers(self) -> None:
        """设置默认消息处理器"""
        self.register_handler(MessageType.TASK.value, self._handle_task_message)
        self.register_handler(MessageType.SYSTEM.value, self._handle_system_message)
        self.register_handler(MessageType.NOTIFICATION.value, self._handle_notification_message)
    
    def get_handler(self, msg_type: str) -> Optional[Callable[[Message], Any]]:
        """获取消息处理器"""
        return self._message_handlers.get(msg_type)
    
    def register_handler(self, msg_type: str, handler: Callable[[Message], Any]) -> None:
        """注册消息处理器"""
        self._message_handlers[msg_type] = handler
    
    def handle_message(self, message: Message) -> Any:
        """
        处理接收到的消息
        
        Args:
            message: 要处理的消息
            
        Returns:
            处理结果
        """
        # 更新状态
        previous_status = self.status
        self.status = AgentStatus.BUSY
        
        try:
            # 获取处理器
            handler = self.get_handler(message.msg_type)
            
            if handler:
                # 记录日志
                self.logger.debug(f"Processing message {message.message_id} of type {message.msg_type}")
                
                # 调用处理器
                result = handler(message)
                
                # 记录处理结果
                self.logger.debug(f"Message {message.message_id} processed successfully")
                
                return result
            else:
                self.logger.warning(f"No handler found for message type: {message.msg_type}")
                return {"status": "error", "message": f"No handler for type {message.msg_type}"}
        
        except Exception as e:
            self.logger.error(f"Error processing message {message.message_id}: {e}")
            return {"status": "error", "message": str(e)}
        
        finally:
            # 恢复状态
            self.status = previous_status
    
    def _handle_task_message(self, message: Message) -> Dict[str, Any]:
        """处理任务消息"""
        self.logger.info(f"Received task: {message.content.get('task_id')}")
        
        # 默认任务处理逻辑
        task_id = message.content.get('task_id', 'unknown')
        result = f"Processed task {task_id} successfully"
        
        # 发送响应
        self.send_message(
            receiver_id=message.sender_id,
            msg_type=MessageType.RESPONSE,
            content={
                "task_id": task_id,
                "result": result,
                "status": "completed"
            },
            conversation_id=message.conversation_id
        )
        
        return {"status": "success", "task_id": task_id}
    
    def _handle_system_message(self, message: Message) -> Dict[str, Any]:
        """处理系统消息"""
        command = message.content.get('command')
        
        if command == "status":
            # 返回状态
            return self.get_status()
        elif command == "shutdown":
            # 关闭智能体
            self.stop()
            return {"status": "shutting_down"}
        elif command == "suspend":
            self.lifecycle.suspend()
            return {"status": "suspended"}
        elif command == "resume":
            self.lifecycle.resume()
            return {"status": "resumed"}
        else:
            self.logger.warning(f"Unknown system command: {command}")
            return {"status": "error", "message": f"Unknown command: {command}"}
    
    def _handle_notification_message(self, message: Message) -> Dict[str, Any]:
        """处理通知消息"""
        self.logger.info(f"Received notification: {message.content.get('title')}")
        return {"status": "received", "notification_id": message.message_id}
    
    def send_message(
        self, 
        receiver_id: str, 
        msg_type: Union[MessageType, str], 
        content: Dict[str, Any],
        priority: int = 2,
        conversation_id: Optional[str] = None
    ) -> str:
        """
        发送消息
        
        Args:
            receiver_id: 接收者ID
            msg_type: 消息类型
            content: 消息内容
            priority: 优先级
            conversation_id: 会话ID
            
        Returns:
            消息ID
        """
        try:
            # 创建消息
            message = Message(
                sender_id=self.agent_id,
                receiver_id=receiver_id,
                msg_type=msg_type,
                content=content,
                priority=priority,
                conversation_id=conversation_id
            )
            
            # 路由消息
            if self.router.route_message(message):
                self.logger.debug(f"Message {message.message_id} sent to {receiver_id}")
                return message.message_id
            else:
                self.logger.warning(f"Failed to route message to {receiver_id}")
                return ""
        
        except Exception as e:
            self.logger.error(f"Error sending message: {e}")
            return ""
    
    def get_status(self) -> Dict[str, Any]:
        """获取智能体状态"""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "status": self.status.value,
            "lifecycle": self.lifecycle.get_status_info(),
            "state": self.state_manager.get_metadata(),
            "handlers": list(self._message_handlers.keys()),
            "timestamp": time.time()
        }
    
    def start(self) -> None:
        """启动智能体"""
        self.lifecycle.start()
    
    def stop(self) -> None:
        """停止智能体"""
        self.lifecycle.stop()
    
    @property
    def is_running(self) -> bool:
        """检查智能体是否正在运行"""
        return self.status in [AgentStatus.ACTIVE, AgentStatus.BUSY]
    
    def _main_loop(self) -> None:
        """
        智能体主循环
        被LifecycleManager调用，实现智能体的核心逻辑
        """
        # 这里可以添加智能体的主动行为逻辑
        # 例如：定期检查状态、执行计划任务等
        self.logger.debug(f"Main loop executed for agent {self.agent_id} with status {self.status.value}")
        if self.status == AgentStatus.ACTIVE:
            # 示例：每5秒记录一次心跳
            current_time = time.time()
            last_heartbeat = self.state_manager.get("last_heartbeat", 0)
            
            if current_time - last_heartbeat > 5:
                self.state_manager.set("last_heartbeat", current_time)
                self.logger.debug(f"Heartbeat from agent {self.agent_id}")