import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Callable, Optional
from enum import Enum

class MessageType(Enum):
    """消息类型枚举"""
    TASK = "task"
    RESPONSE = "response"
    SYSTEM = "system"
    NOTIFICATION = "notification"

class Message:
    """标准化消息格式"""
    def __init__(self, 
                 sender_id: str, 
                 receiver_id: str, 
                 msg_type: MessageType, 
                 content: Dict[str, Any],
                 conversation_id: Optional[str] = None):
        self.message_id = str(uuid.uuid4())
        self.sender_id = sender_id
        self.receiver_id = receiver_id
        self.msg_type = msg_type.value if isinstance(msg_type, Enum) else msg_type
        self.content = content
        self.timestamp = datetime.now().isoformat()
        self.conversation_id = conversation_id or str(uuid.uuid4())
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "message_id": self.message_id,
            "sender_id": self.sender_id,
            "receiver_id": self.receiver_id,
            "msg_type": self.msg_type,
            "content": self.content,
            "timestamp": self.timestamp,
            "conversation_id": self.conversation_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """从字典创建消息对象"""
        msg = cls(
            sender_id=data["sender_id"],
            receiver_id=data["receiver_id"],
            msg_type=MessageType(data["msg_type"]),
            content=data["content"],
            conversation_id=data.get("conversation_id")
        )
        msg.message_id = data["message_id"]
        msg.timestamp = data["timestamp"]
        return msg
    
    def serialize(self) -> str:
        """序列化为JSON字符串"""
        return json.dumps(self.to_dict())
    
    @classmethod
    def deserialize(cls, json_str: str) -> "Message":
        """从JSON字符串反序列化"""
        return cls.from_dict(json.loads(json_str))

class MessageBus:
    """发布/订阅消息总线"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MessageBus, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """初始化消息总线"""
        self._subscribers: Dict[str, List[Callable[[Message], None]]] = {}
        self._broadcast_subscribers: List[Callable[[Message], None]] = []
    
    def subscribe(self, topic: str, callback: Callable[[Message], None]):
        """订阅特定主题"""
        if topic not in self._subscribers:
            self._subscribers[topic] = []
        self._subscribers[topic].append(callback)
    
    def unsubscribe(self, topic: str, callback: Callable[[Message], None]):
        """取消订阅"""
        if topic in self._subscribers and callback in self._subscribers[topic]:
            self._subscribers[topic].remove(callback)
    
    def subscribe_broadcast(self, callback: Callable[[Message], None]):
        """订阅广播消息"""
        if callback not in self._broadcast_subscribers:
            self._broadcast_subscribers.append(callback)
    
    def publish(self, topic: str, message: Message):
        """发布消息到指定主题"""
        # 发送给特定主题的订阅者
        if topic in self._subscribers:
            for callback in self._subscribers[topic][:]:  # 使用切片避免修改列表时出错
                try:
                    callback(message)
                except Exception as e:
                    print(f"Error in subscriber callback: {e}")
        
        # 发送给广播订阅者
        for callback in self._broadcast_subscribers[:]:
            try:
                callback(message)
            except Exception as e:
                print(f"Error in broadcast subscriber callback: {e}")

class MessageRouter:
    """消息路由系统"""
    def __init__(self, message_bus: MessageBus):
        self.message_bus = message_bus
        self.agent_addresses: Dict[str, str] = {}  # agent_id -> topic
    
    def register_agent(self, agent_id: str, topic: str):
        """注册智能体地址"""
        self.agent_addresses[agent_id] = topic
    
    def unregister_agent(self, agent_id: str):
        """注销智能体地址"""
        if agent_id in self.agent_addresses:
            del self.agent_addresses[agent_id]
    
    def route_message(self, message: Message):
        """路由消息到目标智能体"""
        if message.receiver_id in self.agent_addresses:
            topic = self.agent_addresses[message.receiver_id]
            self.message_bus.publish(topic, message)
        else:
            # 尝试广播查找
            self.message_bus.publish("system.unresolved", message)
            print(f"Warning: No route found for agent {message.receiver_id}")
    
    def send_message(self, sender_id: str, receiver_id: str, 
                    msg_type: MessageType, content: Dict[str, Any]):
        """发送消息的便捷方法"""
        message = Message(sender_id, receiver_id, msg_type, content)
        self.route_message(message)
        return message.message_id