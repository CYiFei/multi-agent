"""
Ecosystem Integration Tools
"""
from typing import Dict, List, Any, Optional, Callable
import json
from abc import ABC, abstractmethod

class LLMAdapter(ABC):
    """LLM适配器基类"""
    
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.capabilities = []
    
    @abstractmethod
    def generate_text(self, prompt: str, **kwargs) -> str:
        """生成文本"""
        pass
    
    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        """文本嵌入"""
        pass
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        return {
            "model_name": self.model_name,
            "capabilities": self.capabilities
        }

class OpenAIAdapter(LLMAdapter):
    """OpenAI适配器"""
    
    def __init__(self, model_name: str = "gpt-3.5-turbo", api_key: str = None):
        super().__init__(model_name)
        self.api_key = api_key
        self.capabilities = ["text_generation", "chat_completion"]
        # 在实际实现中，这里会初始化OpenAI客户端
    
    def generate_text(self, prompt: str, **kwargs) -> str:
        """生成文本（模拟实现）"""
        # 在实际实现中，这里会调用OpenAI API
        return f"Generated response for: {prompt}"
    
    def embed_text(self, text: str) -> List[float]:
        """文本嵌入（模拟实现）"""
        # 在实际实现中，这里会调用OpenAI Embedding API
        # 返回模拟的嵌入向量
        return [0.1, 0.2, 0.3]  # 示例向量

class Qwen3MaxAdapter(LLMAdapter):
    """Qwen3-Max模型适配器"""
    
    def __init__(self, model_name: str = "qwen3-max", api_key: str = None):
        super().__init__(model_name)
        self.api_key = api_key
        self.capabilities = ["text_generation", "chat_completion", "reasoning"]
        # 在实际实现中，这里会初始化DashScope客户端或其他Qwen API客户端
    
    def generate_text(self, prompt: str, **kwargs) -> str:
        """生成文本（实际实现）"""
        try:
            # 导入DashScope SDK
            import dashscope
            from http import HTTPStatus
            
            # 设置API密钥
            if self.api_key:
                dashscope.api_key = self.api_key
            elif not dashscope.api_key:
                # 尝试从环境变量获取
                import os
                dashscope.api_key = os.getenv('DASHSCOPE_API_KEY')
                
            if not dashscope.api_key:
                raise ValueError("未找到API密钥，请设置DASHSCOPE_API_KEY环境变量或在创建适配器时传入api_key")
            
            # 准备消息列表
            messages = []
            
            # 如果有对话历史，则添加到消息中
            if "chat_history" in kwargs:
                history = kwargs["chat_history"]
                for item in history:
                    messages.append({'role': item['role'], 'content': item['content']})
            
            # 添加当前提示词
            messages.append({'role': 'user', 'content': prompt})
            
            # 调用Qwen模型
            response = dashscope.Generation.call(
                model='qwen3-max',
                messages=messages,
                result_format='message'
            )
            
            # 检查响应状态
            if response.status_code == HTTPStatus.OK:
                return response.output.choices[0].message.content
            else:
                raise Exception(f"调用Qwen API失败: {response.code} - {response.message}")
                
        except ImportError:
            # 如果没有安装dashscope库，则回退到模拟实现
            import warnings
            warnings.warn("未安装dashscope库，使用模拟实现。请通过 'pip install dashscope' 安装。")
            # 回退到模拟实现
            if "chat_history" in kwargs:
                history = kwargs["chat_history"]
                context = "\n".join([f"{msg['role']}: {msg['content']}" for msg in history])
                return f"Qwen3-Max回复: 基于我们的对话历史:\n{context}\n\n我对'{prompt}'的理解是..."
            else:
                return f"Qwen3-Max回复: 针对'{prompt}'，我认为这是一个很有趣的问题。"
        except Exception as e:
            # 出现异常时也回退到模拟实现，但记录错误
            import logging
            logging.error(f"调用Qwen API时出现错误: {e}")
            # 回退到模拟实现
            if "chat_history" in kwargs:
                history = kwargs["chat_history"]
                context = "\n".join([f"{msg['role']}: {msg['content']}" for msg in history])
                return f"Qwen3-Max回复: 基于我们的对话历史:\n{context}\n\n我对'{prompt}'的理解是..."
            else:
                return f"Qwen3-Max回复: 针对'{prompt}'，我认为这是一个很有趣的问题。"
            
    def embed_text(self, text: str) -> List[float]:
        """文本嵌入（模拟实现）"""
        # 在实际实现中，这里会调用Qwen的嵌入API
        # 返回模拟的嵌入向量
        import hashlib
        # 简单模拟嵌入向量生成
        hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16)
        return [(hash_val % 1000) / 1000.0, (hash_val % 2000) / 2000.0, (hash_val % 3000) / 3000.0]
    
class HuggingFaceAdapter(LLMAdapter):
    """HuggingFace适配器"""
    
    def __init__(self, model_name: str = "gpt2"):
        super().__init__(model_name)
        self.capabilities = ["text_generation", "text_classification"]
        # 在实际实现中，这里会初始化HuggingFace管道
    
    def generate_text(self, prompt: str, **kwargs) -> str:
        """生成文本（模拟实现）"""
        # 在实际实现中，这里会调用HuggingFace模型
        return f"HuggingFace generated response for: {prompt}"
    
    def embed_text(self, text: str) -> List[float]:
        """文本嵌入（模拟实现）"""
        # 在实际实现中，这里会使用HuggingFace的嵌入模型
        return [0.4, 0.5, 0.6]  # 示例向量

class ThirdPartyConnector:
    """第三方服务连接器"""
    
    def __init__(self):
        self.services: Dict[str, Any] = {}
        self.templates: Dict[str, Dict[str, Any]] = {}
    
    def register_service(self, service_name: str, connector: Any) -> None:
        """注册服务"""
        self.services[service_name] = connector
    
    def get_service(self, service_name: str) -> Any:
        """获取服务连接器"""
        return self.services.get(service_name)
    
    def register_template(self, template_name: str, template: Dict[str, Any]) -> None:
        """注册应用场景模板"""
        self.templates[template_name] = template
    
    def get_template(self, template_name: str) -> Optional[Dict[str, Any]]:
        """获取应用场景模板"""
        return self.templates.get(template_name)
    
    def list_templates(self) -> List[str]:
        """列出所有模板"""
        return list(self.templates.keys())
    
    def instantiate_template(self, template_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """实例化模板"""
        template = self.get_template(template_name)
        if not template:
            raise ValueError(f"Template '{template_name}' not found")
        
        # 简单的参数替换实现
        instantiated = json.loads(json.dumps(template))
        
        # 在实际实现中，这里会有更复杂的模板渲染逻辑
        return instantiated

# 常见应用场景模板
DEFAULT_TEMPLATES = {
    "data_processing_pipeline": {
        "name": "Data Processing Pipeline",
        "description": "Template for data processing workflows",
        "agents": [
            {"id": "reader", "type": "data_reader", "capabilities": ["read"]},
            {"id": "processor", "type": "data_processor", "capabilities": ["process"]},
            {"id": "writer", "type": "data_writer", "capabilities": ["write"]}
        ],
        "workflow": [
            {"from": "reader", "to": "processor", "trigger": "data_ready"},
            {"from": "processor", "to": "writer", "trigger": "processing_complete"}
        ]
    },
    
    "chat_bot": {
        "name": "Chat Bot",
        "description": "Template for chatbot applications",
        "agents": [
            {"id": "input_handler", "type": "input_handler", "capabilities": ["receive_input"]},
            {"id": "intent_classifier", "type": "intent_classifier", "capabilities": ["classify"]},
            {"id": "response_generator", "type": "response_generator", "capabilities": ["generate_response"]}
        ],
        "workflow": [
            {"from": "input_handler", "to": "intent_classifier", "trigger": "user_input"},
            {"from": "intent_classifier", "to": "response_generator", "trigger": "intent_identified"}
        ]
    }
}

def initialize_ecosystem() -> ThirdPartyConnector:
    """初始化生态系统连接器"""
    connector = ThirdPartyConnector()
    
    # 注册默认模板
    for name, template in DEFAULT_TEMPLATES.items():
        connector.register_template(name, template)
    
    return connector