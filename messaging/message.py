import json
import uuid
from datetime import datetime
from typing import Any, Dict, Optional, Union
from enum import Enum

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

class MessageSchema:
    """消息格式标准定义 (JSON Schema)"""
    SCHEMA = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "AgentMessage",
        "type": "object",
        "required": [
            "message_id", "sender_id", "receiver_id", 
            "msg_type", "content", "timestamp"
        ],
        "properties": {
            "message_id": {
                "type": "string",
                "description": "唯一消息ID (UUID format)"
            },
            "sender_id": {
                "type": "string",
                "description": "发送者智能体ID"
            },
            "receiver_id": {
                "type": "string",
                "description": "接收者智能体ID或'broadcast'"
            },
            "msg_type": {
                "type": "string",
                "enum": [t.value for t in MessageType],
                "description": "消息类型"
            },
            "content": {
                "type": "object",
                "description": "消息内容，结构由具体场景定义"
            },
            "timestamp": {
                "type": "string",
                "format": "date-time",
                "description": "ISO 8601格式时间戳"
            },
            "priority": {
                "type": "integer",
                "minimum": 1,
                "maximum": 4,
                "default": 2,
                "description": "消息优先级 (1-4)"
            },
            "conversation_id": {
                "type": "string",
                "description": "会话ID，用于关联相关消息"
            },
            "metadata": {
                "type": "object",
                "description": "附加元数据"
            }
        }
    }

class Message:
    """标准化消息对象"""
    
    def __init__(
        self,
        sender_id: str,
        receiver_id: str,
        msg_type: Union[MessageType, str],
        content: Dict[str, Any],
        priority: Union[MessagePriority, int] = MessagePriority.NORMAL,
        conversation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        # 基本验证
        if not sender_id or not receiver_id:
            raise ValueError("sender_id and receiver_id cannot be empty")
        
        if not content or not isinstance(content, dict):
            raise ValueError("content must be a non-empty dictionary")
        
        # 设置属性
        self.message_id = str(uuid.uuid4())
        self.sender_id = sender_id
        self.receiver_id = receiver_id
        self.msg_type = msg_type.value if isinstance(msg_type, Enum) else msg_type
        self.content = content
        self.timestamp = datetime.now().isoformat()
        self.priority = priority.value if isinstance(priority, Enum) else priority
        self.conversation_id = conversation_id or str(uuid.uuid4())
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典，符合JSON Schema"""
        return {
            "message_id": self.message_id,
            "sender_id": self.sender_id,
            "receiver_id": self.receiver_id,
            "msg_type": self.msg_type,
            "content": self.content,
            "timestamp": self.timestamp,
            "priority": self.priority,
            "conversation_id": self.conversation_id,
            "metadata": self.metadata
        }
    
    def serialize(self) -> str:
        """序列化为JSON字符串"""
        return json.dumps(self.to_dict())
    
    @classmethod
    def deserialize(cls, json_str: str) -> "Message":
        """从JSON字符串反序列化"""
        data = json.loads(json_str)
        return cls(
            sender_id=data["sender_id"],
            receiver_id=data["receiver_id"],
            msg_type=data["msg_type"],
            content=data["content"],
            priority=data.get("priority", MessagePriority.NORMAL.value),
            conversation_id=data.get("conversation_id"),
            metadata=data.get("metadata", {})
        )
    
    def validate(self) -> bool:
        """验证消息是否符合schema (简化版)"""
        data = self.to_dict()
        
        # 基本验证
        required_fields = ["message_id", "sender_id", "receiver_id", "msg_type", "content", "timestamp"]
        for field in required_fields:
            if field not in data:
                return False
        
        # 类型验证
        if not isinstance(data["content"], dict):
            return False
        
        if not isinstance(data["priority"], int) or not (1 <= data["priority"] <= 4):
            return False
        
        return True
    
    def __repr__(self) -> str:
        return (f"Message(id={self.message_id[:8]}, from={self.sender_id}, "
                f"to={self.receiver_id}, type={self.msg_type})")