from typing import Dict, Any, Optional, Callable
import threading
import time
import logging
from enum import Enum

from .base_agent import Agent, AgentStatus
from messaging.message import Message, MessageType
from messaging.router import MessageRouter

class LifecycleManager:
    """智能体生命周期管理器"""
    
    def __init__(self, agent: Agent):
        """
        初始化生命周期管理器
        
        Args:
            agent: 要管理的智能体实例
        """
        self.agent = agent
        self.status = AgentStatus.INITIALIZING
        self._worker_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._lifecycle_hooks: Dict[str, List[Callable[[], None]]] = {
            "before_start": [],
            "after_start": [],
            "before_stop": [],
            "after_stop": [],
            "on_error": []
        }
        self.logger = logging.getLogger(f"lifecycle.{agent.agent_id}")
    
    def add_hook(self, hook_type: str, callback: Callable[[], None]) -> None:
        """
        添加生命周期钩子
        
        Args:
            hook_type: 钩子类型 (before_start, after_start, before_stop, after_stop, on_error)
            callback: 回调函数
        """
        if hook_type not in self._lifecycle_hooks:
            raise ValueError(f"Invalid hook type: {hook_type}")
        
        if not callable(callback):
            raise ValueError("Callback must be callable")
        
        self._lifecycle_hooks[hook_type].append(callback)
    
    def _run_hooks(self, hook_type: str) -> None:
        """执行指定类型的钩子"""
        for hook in self._lifecycle_hooks[hook_type]:
            try:
                hook()
            except Exception as e:
                self.logger.error(f"Error in {hook_type} hook: {e}")
                # 执行错误钩子
                for error_hook in self._lifecycle_hooks["on_error"]:
                    try:
                        error_hook()
                    except:
                        pass
    
    def start(self) -> None:
        """启动智能体"""
        with self._lock:
            if self.status in [AgentStatus.ACTIVE, AgentStatus.BUSY]:
                self.logger.warning("Agent is already running")
                return
            
            if self.status == AgentStatus.TERMINATED:
                self.logger.error("Cannot start a terminated agent")
                return
            
            # 执行启动前钩子
            self._run_hooks("before_start")
            
            # 更新状态
            self.status = AgentStatus.ACTIVE
            self.agent.status = AgentStatus.ACTIVE
            
            # 启动工作线程
            self._stop_event.clear()
            self._worker_thread = threading.Thread(
                target=self._lifecycle_worker,
                name=f"agent-{self.agent.agent_id}-worker",
                daemon=True
            )
            self._worker_thread.start()
            
            # 执行启动后钩子
            self._run_hooks("after_start")
            
            self.logger.info(f"Agent {self.agent.agent_id} started successfully")
    
    def _lifecycle_worker(self) -> None:
        """生命周期工作线程"""
        self.logger.debug(f"Lifecycle worker started for agent {self.agent.agent_id}")
        
        while not self._stop_event.is_set():
            try:
                # 检查状态
                if self.status == AgentStatus.SUSPENDED:
                    time.sleep(0.5)  # 降低CPU使用率
                    continue
                
                # 调用智能体的主循环逻辑
                if hasattr(self.agent, "_main_loop"):
                    self.agent._main_loop()
                
                # 短暂休眠，避免占用过多CPU
                time.sleep(0.1)
                
            except Exception as e:
                self.logger.error(f"Error in lifecycle worker: {e}")
                # 执行错误钩子
                self._run_hooks("on_error")
                # 短暂休眠后继续
                time.sleep(1.0)
    
    def stop(self, graceful: bool = True) -> None:
        """
        停止智能体
        
        Args:
            graceful: 是否优雅停止 (等待当前任务完成)
        """
        with self._lock:
            if self.status == AgentStatus.TERMINATED:
                self.logger.warning("Agent is already terminated")
                return
            
            # 执行停止前钩子
            self._run_hooks("before_stop")
            
            # 更新状态
            self.status = AgentStatus.TERMINATING
            self.agent.status = AgentStatus.TERMINATING
            
            # 设置停止事件
            self._stop_event.set()
            
            # 优雅停止：等待工作线程结束
            if graceful and self._worker_thread and self._worker_thread.is_alive():
                self._worker_thread.join(timeout=5.0)
            
            # 确保线程已停止
            if self._worker_thread and self._worker_thread.is_alive():
                self.logger.warning(f"Worker thread for agent {self.agent.agent_id} did not stop gracefully")
            
            # 更新最终状态
            self.status = AgentStatus.TERMINATED
            self.agent.status = AgentStatus.TERMINATED
            
            # 执行停止后钩子
            self._run_hooks("after_stop")
            
            self.logger.info(f"Agent {self.agent.agent_id} terminated")
    
    def suspend(self) -> None:
        """暂停智能体"""
        with self._lock:
            if self.status not in [AgentStatus.ACTIVE, AgentStatus.BUSY]:
                self.logger.warning(f"Cannot suspend agent in {self.status.value} state")
                return
            
            self.status = AgentStatus.SUSPENDED
            self.agent.status = AgentStatus.SUSPENDED
            self.logger.info(f"Agent {self.agent.agent_id} suspended")
    
    def resume(self) -> None:
        """恢复智能体"""
        with self._lock:
            if self.status != AgentStatus.SUSPENDED:
                self.logger.warning(f"Cannot resume agent in {self.status.value} state")
                return
            
            self.status = AgentStatus.ACTIVE
            self.agent.status = AgentStatus.ACTIVE
            self.logger.info(f"Agent {self.agent.agent_id} resumed")
    
    def get_status_info(self) -> Dict[str, Any]:
        """获取详细的生命周期状态信息"""
        return {
            "agent_id": self.agent.agent_id,
            "status": self.status.value,
            "is_running": self.status in [AgentStatus.ACTIVE, AgentStatus.BUSY],
            "thread_alive": self._worker_thread.is_alive() if self._worker_thread else False,
            "last_updated": time.time()
        }