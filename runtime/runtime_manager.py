from typing import Dict, List, Optional, Any
import threading
import time
import logging

from messaging.pubsub import PubSubBus
from messaging.router import MessageRouter
from agents.agent_impl import BasicAgent
from agents.base_agent import AgentStatus
from .monitor import ExecutionMonitor
from .types import RuntimeManagerInterface

class RuntimeManager(RuntimeManagerInterface):
    """运行时管理器"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RuntimeManager, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """初始化运行时管理器"""
        self.logger = logging.getLogger("runtime")
        
        # 初始化核心组件
        self.message_bus = PubSubBus()
        self.router = MessageRouter(self.message_bus)
        
        # 启动消息总线
        self.message_bus.start()
        
        # 智能体注册表
        self.agents: Dict[str, BasicAgent] = {}
        self._agent_lock = threading.Lock()
        
        # 系统状态
        self._running = True
        self._monitor_thread = None
        self._stop_event = threading.Event()
        
        # 新增执行监控器
        self.execution_monitor = ExecutionMonitor(self)
        self.execution_monitor.start_monitoring()

        # 启动监控线程
        self._start_monitor()
        
        self.logger.info("Runtime manager initialized successfully")
    
    def _start_monitor(self) -> None:
        """启动监控线程"""
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            name="runtime-monitor",
            daemon=True
        )
        self._monitor_thread.start()
    
    def _monitor_loop(self) -> None:
        """监控循环"""
        self.logger.info("Runtime monitor started")
        
        while not self._stop_event.is_set():
            try:
                # 监控系统健康状态
                self._check_system_health()
                
                # 监控智能体状态
                self._check_agent_health()
                
                # 等待下一次检查
                time.sleep(5.0)
                
            except Exception as e:
                self.logger.error(f"Error in monitor loop: {e}")
                time.sleep(1.0)
    
    def _check_system_health(self) -> None:
        """检查系统健康状态"""
        # 检查消息总线状态
        queue_size = self.message_bus._message_queue.qsize()
        if queue_size > 100:  # 阈值可以根据需要调整
            self.logger.warning(f"Message queue size is high: {queue_size}")
    
    def _check_agent_health(self) -> None:
        """检查智能体健康状态"""
        with self._agent_lock:
            terminated_agents = []
            
            for agent_id, agent in self.agents.items():
                # 检查智能体状态
                if agent.status == AgentStatus.TERMINATED:
                    terminated_agents.append(agent_id)
                
                # 检查心跳
                last_heartbeat = agent.state_manager.get("last_heartbeat", 0)
                if time.time() - last_heartbeat > 30:  # 15秒无心跳
                    self.logger.warning(f"Agent {agent_id} has no heartbeat for 15 seconds")
            
            # 清理已终止的智能体
            for agent_id in terminated_agents:
                del self.agents[agent_id]
                self.logger.info(f"Removed terminated agent: {agent_id}")
    
    def register_agent(self, agent: BasicAgent) -> None:
        """
        注册智能体
        
        Args:
            agent: 要注册的智能体
        """
        with self._agent_lock:
            if agent.agent_id in self.agents:
                raise ValueError(f"Agent with ID {agent.agent_id} already registered")
            
            self.agents[agent.agent_id] = agent
            self.logger.info(f"Registered agent: {agent.agent_id} ({agent.name})")
        
        print("打印所有已经注册置的智能体ID")
        for item in self.agents:
            print(item)
    
    def unregister_agent(self, agent_id: str) -> None:
        """
        注销智能体
        
        Args:
            agent_id: 要注销的智能体ID
        """
        with self._agent_lock:
            if agent_id in self.agents:
                # 优雅停止智能体
                self.agents[agent_id].stop()
                del self.agents[agent_id]
                self.logger.info(f"Unregistered agent: {agent_id}")
    
    def get_agent(self, agent_id: str) -> Optional[BasicAgent]:
        """
        获取智能体
        
        Args:
            agent_id: 智能体ID
            
        Returns:
            智能体实例或None
        """
        with self._agent_lock:
            return self.agents.get(agent_id)
    
    def get_all_agents(self) -> Dict[str, BasicAgent]:
        """获取所有注册的智能体"""
        with self._agent_lock:
            return self.agents.copy()
    
    def shutdown(self) -> None:
        """关闭运行时"""
        self.logger.info("Shutting down runtime manager...")
        
        # 停止执行监控
        self.execution_monitor.stop_monitoring()

        # 设置停止标志
        self._stop_event.set()
        
        # 停止所有智能体
        with self._agent_lock:
            for agent in self.agents.values():
                agent.stop()
            self.agents.clear()
        
        # 停止监控线程
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=3.0)
        
        # 停止消息总线
        self.message_bus.stop()
        
        self._running = False
        self.logger.info("Runtime manager shutdown complete")
    
    def get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        return {
            "running": self._running,
            "agent_count": len(self.agents),
            "message_queue_size": self.message_bus._message_queue.qsize(),
            "active_subscribers": sum(
                self.message_bus.get_subscriber_count(topic) 
                for topic in ["broadcast"]
            ) + self.message_bus.get_broadcast_subscriber_count(),
            "timestamp": time.time()
        }