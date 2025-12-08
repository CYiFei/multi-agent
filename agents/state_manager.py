from typing import Any, Dict, Optional, List, Union
import threading
import json
import os
from datetime import datetime

class StateError(Exception):
    """状态管理错误"""
    pass

class StateManager:
    """智能体状态管理器"""
    
    def __init__(self, agent_id: str, persistent: bool = False, storage_path: Optional[str] = None):
        """
        初始化状态管理器
        
        Args:
            agent_id: 智能体ID
            persistent: 是否持久化状态
            storage_path: 持久化存储路径
        """
        self.agent_id = agent_id
        self._state: Dict[str, Any] = {}
        self._lock = threading.Lock()
        self._persistent = persistent
        self._storage_path = storage_path or f".agent_state/{agent_id}.json"
        self._last_modified = datetime.now()
        
        # 加载持久化状态（如果存在）
        if self._persistent:
            self._load_persistent_state()
    
    def _load_persistent_state(self) -> None:
        """加载持久化状态"""
        try:
            if os.path.exists(self._storage_path):
                with open(self._storage_path, 'r') as f:
                    self._state = json.load(f)
                self._last_modified = datetime.fromtimestamp(os.path.getmtime(self._storage_path))
        except Exception as e:
            print(f"Error loading persistent state: {e}")
            self._state = {}
    
    def _save_persistent_state(self) -> None:
        """保存持久化状态"""
        if not self._persistent:
            return
        
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(os.path.abspath(self._storage_path)), exist_ok=True)
            
            # 保存状态
            with open(self._storage_path, 'w') as f:
                json.dump(self._state, f, indent=2)
            
            self._last_modified = datetime.now()
        except Exception as e:
            print(f"Error saving persistent state: {e}")
    
    def set(self, key: str, value: Any) -> None:
        """
        设置状态值
        
        Args:
            key: 状态键
            value: 状态值
        """
        with self._lock:
            self._state[key] = value
            if self._persistent:
                self._save_persistent_state()
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取状态值
        
        Args:
            key: 状态键
            default: 默认值
            
        Returns:
            状态值或默认值
        """
        with self._lock:
            return self._state.get(key, default)
    
    def delete(self, key: str) -> bool:
        """
        删除状态键
        
        Args:
            key: 要删除的键
            
        Returns:
            是否成功删除
        """
        with self._lock:
            if key in self._state:
                del self._state[key]
                if self._persistent:
                    self._save_persistent_state()
                return True
            return False
    
    def update(self, updates: Dict[str, Any]) -> None:
        """
        批量更新状态
        
        Args:
            updates: 更新字典
        """
        with self._lock:
            self._state.update(updates)
            if self._persistent:
                self._save_persistent_state()
    
    def get_all(self) -> Dict[str, Any]:
        """获取所有状态"""
        with self._lock:
            return self._state.copy()
    
    def clear(self) -> None:
        """清除所有状态"""
        with self._lock:
            self._state.clear()
            if self._persistent:
                self._save_persistent_state()
    
    def get_metadata(self) -> Dict[str, Any]:
        """获取状态元数据"""
        with self._lock:
            return {
                "agent_id": self.agent_id,
                "key_count": len(self._state),
                "last_modified": self._last_modified.isoformat(),
                "persistent": self._persistent,
                "storage_path": self._storage_path if self._persistent else None
            }
    
    def __getitem__(self, key: str) -> Any:
        """支持字典式访问"""
        return self.get(key)
    
    def __setitem__(self, key: str, value: Any) -> None:
        """支持字典式设置"""
        self.set(key, value)
    
    def __delitem__(self, key: str) -> None:
        """支持字典式删除"""
        self.delete(key)
    
    def __contains__(self, key: str) -> bool:
        """支持in操作符"""
        with self._lock:
            return key in self._state
    
    def __len__(self) -> int:
        """支持len()函数"""
        with self._lock:
            return len(self._state)