"""
LLM-based Conversational Agent Implementation
"""
from typing import Dict, Any, List, Optional
import logging
import time

from .agent_impl import BasicAgent
from messaging.message import Message, MessageType
from tools.ecosystem import Qwen3MaxAdapter

class LLMAgent(BasicAgent):
    """基于大语言模型的对话智能体"""
    
    def __init__(
        self, 
        agent_id: str, 
        name: str, 
        router: 'MessageRouter',
        llm_adapter: Qwen3MaxAdapter,
        persistent_state: bool = False,
        state_storage_path: Optional[str] = None
    ):
        """
        初始化LLM智能体
        
        Args:
            agent_id: 智能体唯一标识
            name: 智能体名称
            router: 消息路由器
            llm_adapter: LLM适配器实例
            persistent_state: 是否持久化状态
            state_storage_path: 状态存储路径
        """
        super().__init__(agent_id, name, router, persistent_state, state_storage_path)
        
        # LLM相关组件
        self.llm_adapter = llm_adapter
        self.conversation_history: List[Dict[str, str]] = []
        self.max_history_length = 10  # 最大对话历史长度
        
        # 注册对话相关的消息处理器
        self.register_handler("chat_message", self._handle_chat_message)
        self.register_handler(MessageType.TASK.value, self._handle_task_with_llm)
        
        self.logger.info(f"LLM Agent {agent_id} initialized with model {getattr(llm_adapter, 'model_name', 'unknown')}")
    
    def _setup_handlers(self) -> None:
        """设置默认消息处理器"""
        super()._setup_handlers()
        # 添加LLM特有的处理器
        self.register_handler("chat_message", self._handle_chat_message)
    
    
    def _handle_chat_message(self, message: Message) -> Dict[str, Any]:
        """处理聊天消息"""
        self.logger.info(f"Received chat message from {message.sender_id}")
        
        # 检查是否为自己发送的回复消息，避免循环处理
        if (message.sender_id == self.agent_id and 
            message.content.get("agent_id") == self.agent_id):
            self.logger.debug("Ignoring self-sent reply message to prevent loop")
            return {"status": "ignored", "message": "Self-sent reply message ignored"}
        
        # 获取用户消息内容
        user_message = message.content.get("text", "")
        self.logger.debug(f"User message content: {user_message}")
        if not user_message:
            self.logger.warning("Received empty message")
            return {"status": "error", "message": "Empty message received"}
        
        # 添加到对话历史
        self._add_to_history("user", user_message)
        self.logger.debug(f"Added user message to history: {user_message}")
        
        # 使用LLM生成回复
        try:
            response_text = self._generate_llm_response(user_message)
            self.logger.debug(f"Generated LLM response: {response_text}")
            
            # 添加到对话历史
            self._add_to_history("assistant", response_text)
            
            self.logger.info(f"Sending reply to {message.sender_id}")
            # 发送回复
            reply_msg_id = self.send_message(
                receiver_id=message.sender_id,
                msg_type="chat_message",
                content={
                    "text": response_text,
                    "agent_id": self.agent_id,
                    "timestamp": time.time()
                },
                conversation_id=message.conversation_id
            )
            
            self.logger.info(f"Sent reply message with ID: {reply_msg_id}")
            
            return {"status": "success", "response": response_text}
            
        except Exception as e:
            self.logger.error(f"Error generating LLM response: {e}", exc_info=True)
            error_response = "抱歉，我在生成回复时遇到了问题。请稍后再试。"
            
            # 添加错误信息到对话历史，方便调试
            self._add_to_history("assistant", error_response)
            
            # 发送错误回复
            try:
                error_msg_id = self.send_message(
                    receiver_id=message.sender_id,
                    msg_type="chat_message",
                    content={
                        "text": error_response,
                        "agent_id": self.agent_id,
                        "timestamp": time.time(),
                        "error": str(e)
                    },
                    conversation_id=message.conversation_id
                )
                
                self.logger.info(f"Sent error message with ID: {error_msg_id}")
            except Exception as send_error:
                self.logger.error(f"Failed to send error message: {send_error}", exc_info=True)
            
            return {"status": "error", "message": str(e)}
    
    def _handle_task_with_llm(self, message: Message) -> Dict[str, Any]:
        """使用LLM处理任务消息"""
        self.logger.info(f"Processing task with LLM: {message.content.get('task_id')}")
        
        # 获取任务描述
        task_description = message.content.get('description', '')
        
        # 构造提示词
        prompt = f"请帮我完成以下任务：\n{task_description}\n\n请提供详细的解决方案："
        
        try:
            # 使用LLM生成解决方案
            solution = self.llm_adapter.generate_text(prompt)
            
            # 发送响应
            self.send_message(
                receiver_id=message.sender_id,
                msg_type=MessageType.RESPONSE,
                content={
                    "task_id": message.content.get('task_id', 'unknown'),
                    "result": solution,
                    "status": "completed",
                    "processed_by": self.agent_id
                },
                conversation_id=message.conversation_id
            )
            
            return {"status": "success", "solution": solution}
            
        except Exception as e:
            self.logger.error(f"Error processing task with LLM: {e}")
            return {"status": "error", "message": str(e)}
    
    def _generate_llm_response(self, user_message: str) -> str:
        """使用LLM生成回复"""
        # 构造提示词
        prompt = f"用户说: {user_message}\n请给出合适的回复："
        
        # 确保对话历史不为空且格式正确
        valid_history = []
        for item in self.conversation_history[-self.max_history_length:]:
            if isinstance(item, dict) and 'role' in item and 'content' in item:
                valid_history.append(item)
        
        # 调用LLM适配器生成文本
        response = self.llm_adapter.generate_text(
            prompt, 
            chat_history=valid_history
        )
        
        return response
    
    def _add_to_history(self, role: str, content: str) -> None:
        """添加消息到对话历史"""
        # 确保内容不为空
        if not content:
            return
            
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": time.time()
        })
        
        # 保持历史记录在最大长度内
        while len(self.conversation_history) > self.max_history_length:
            self.conversation_history.pop(0)
    
    def get_conversation_history(self) -> List[Dict[str, str]]:
        """获取对话历史"""
        return self.conversation_history.copy()
    
    def clear_conversation_history(self) -> None:
        """清空对话历史"""
        self.conversation_history.clear()
    
    def send_chat_message(self, receiver_id: str, text: str) -> str:
        """发送聊天消息"""
        message_id = self.send_message(
            receiver_id=receiver_id,
            msg_type="chat_message",
            content={
                "text": text,
                "agent_id": self.agent_id
            }
        )
        return message_id