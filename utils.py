import json
import os
import logging
from typing import Dict, Any, Optional

def setup_logging(log_file: Optional[str] = None, level: int = logging.INFO):
    """设置日志系统"""
    handlers = [logging.StreamHandler()]
    if log_file:
        os.makedirs(os.path.dirname(os.path.abspath(log_file)), exist_ok=True)
        handlers.append(logging.FileHandler(log_file))
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )

def load_config(config_path: str) -> Dict[str, Any]:
    """加载配置文件"""
    if not os.path.exists(config_path):
        return {}
    
    with open(config_path, 'r') as f:
        return json.load(f)

def save_config(config: Dict[str, Any], config_path: str):
    """保存配置文件"""
    os.makedirs(os.path.dirname(os.path.abspath(config_path)), exist_ok=True)
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)

def generate_agent_id(prefix: str = "agent") -> str:
    """生成唯一智能体ID"""
    import uuid
    import time
    timestamp = int(time.time())
    random_part = str(uuid.uuid4())[:8]
    return f"{prefix}_{timestamp}_{random_part}"

class Singleton(type):
    """单例元类"""
    _instances = {}
    
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]