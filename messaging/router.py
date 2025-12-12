from typing import Dict, Optional, List, Callable
from .message import Message
from .pubsub import PubSubBus
import threading
import logging
class RouterError(Exception):
    """路由系统错误"""
    pass

class MessageRouter:
    """消息路由系统"""
    
    def __init__(self, pubsub_bus: PubSubBus):
        if not isinstance(pubsub_bus, PubSubBus):
            raise ValueError("pubsub_bus must be an instance of PubSubBus")
        
        self.pubsub_bus = pubsub_bus
        self.agent_routes: Dict[str, str] = {}  # agent_id -> topic
        self.agent_instances: Dict[str, 'Agent'] = {}  # agent_id -> agent_instance
        self.group_routes: Dict[str, List[str]] = {}  # group_id -> [agent_ids]
        self.fallback_handlers: List[Callable[[Message], bool]] = []
        self._route_lock = threading.Lock()
        self.logger = logging.getLogger("MessageRouter")
    
    def register_agent(self, agent_id: str, topic: str, agent_instance: Optional['Agent'] = None) -> None:
        """注册智能体路由"""
        if not agent_id or not topic:
            raise ValueError("agent_id and topic cannot be empty")
        
        with self._route_lock:
            self.agent_routes[agent_id] = topic
            if agent_instance:
                self.agent_instances[agent_id] = agent_instance
            # 订阅该主题
            self.pubsub_bus.subscribe(topic, lambda msg: self._handle_routed_message(msg, agent_id))
    
    def unregister_agent(self, agent_id: str) -> None:
        """注销智能体路由"""
        with self._route_lock:
            if agent_id in self.agent_routes:
                topic = self.agent_routes[agent_id]
                del self.agent_routes[agent_id]
                # 注意：不取消订阅，因为可能有其他处理逻辑
    
    def register_agent_group(self, group_id: str, agent_ids: List[str]) -> None:
        """注册智能体组"""
        if not group_id or not agent_ids:
            raise ValueError("group_id and agent_ids cannot be empty")
        
        with self._route_lock:
            self.group_routes[group_id] = agent_ids[:]
    
    def unregister_agent_group(self, group_id: str) -> None:
        """注销智能体组"""
        with self._route_lock:
            if group_id in self.group_routes:
                del self.group_routes[group_id]
    
    def add_fallback_handler(self, handler: Callable[[Message], bool]) -> None:
        """添加回退处理器，当没有找到路由时调用"""
        if not callable(handler):
            raise ValueError("Handler must be callable")
        
        self.fallback_handlers.append(handler)
    
    def _handle_routed_message(self, message: Message, agent_id: str) -> None:
        """处理路由到特定智能体的消息"""
        # 这里可以添加路由级别的中间件逻辑
        # 例如：消息验证、日志记录、指标收集等
        with self._route_lock:
            if agent_id in self.agent_instances:
                agent = self.agent_instances[agent_id]
                try:
                    agent.handle_message(message)
                except Exception as e:
                    print(f"Error handling message in agent {agent_id}: {e}")
            else:
                print(f"No agent instance found for agent_id: {agent_id}")
    
    def route_message(self, message: Message) -> bool:
        """路由消息到目标"""
        self.logger.debug(f"Routing message {message.message_id} from {message.sender_id} to {message.receiver_id}")
        
        # 1. 检查是否为广播消息
        if message.receiver_id == "broadcast":
            self.pubsub_bus.publish("broadcast", message)
            self.logger.debug(f"Published broadcast message {message.message_id}")
            return True
        
        # 2. 检查是否为组消息
        if message.receiver_id.startswith("group:"):
            group_id = message.receiver_id[6:]  # 去掉"group:"前缀
            with self._route_lock:
                if group_id in self.group_routes:
                    for agent_id in self.group_routes[group_id]:
                        if agent_id in self.agent_routes:
                            topic = self.agent_routes[agent_id]
                            # 创建消息副本，避免修改原始消息
                            msg_copy = Message(
                                sender_id=message.sender_id,
                                receiver_id=agent_id,
                                msg_type=message.msg_type,
                                content=message.content,
                                priority=message.priority,
                                conversation_id=message.conversation_id,
                                metadata=message.metadata.copy()
                            )
                            self.pubsub_bus.publish(topic, msg_copy)
                            self.logger.debug(f"Published message {message.message_id} to group member {agent_id}")
                    return True
        
        # 3. 检查是否为单个智能体消息
        with self._route_lock:
            if message.receiver_id in self.agent_routes:
                topic = self.agent_routes[message.receiver_id]
                self.pubsub_bus.publish(topic, message)
                self.logger.debug(f"Published message {message.message_id} to agent {message.receiver_id} on topic {topic}")
                return True
        
        # 4. 尝试回退处理器
        for handler in self.fallback_handlers:
            if handler(message):
                self.logger.debug(f"Handled message {message.message_id} with fallback handler")
                return True
        
        # 5. 无路由找到
        self.logger.warning(f"No route found for message to {message.receiver_id}")
        return False
    def get_routes(self) -> Dict[str, str]:
        """获取所有注册的路由"""
        with self._route_lock:
            return self.agent_routes.copy()
    
    def get_groups(self) -> Dict[str, List[str]]:
        """获取所有注册的组"""
        with self._route_lock:
            return {gid: agents[:] for gid, agents in self.group_routes.items()}