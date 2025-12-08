import threading
from typing import Dict, Any, List, Optional
import time
from .message_system import MessageBus, Message, MessageType
from .agent_base import Agent

class AgentManager:
    """智能体管理器"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AgentManager, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        self.agents: Dict[str, Agent] = {}
        self.message_bus = MessageBus()
        self.system_topic = "system.runtime"
        self._setup_system_handlers()
        self._stop_flag = threading.Event()
        self._monitor_thread = None
    
    def _setup_system_handlers(self):
        """设置系统级消息处理器"""
        self.message_bus.subscribe(self.system_topic, self._handle_system_message)
        
        # 注册广播处理器
        self.message_bus.subscribe_broadcast(self._handle_broadcast_message)
    
    def _handle_system_message(self, message: Message):
        """处理系统级消息"""
        command = message.content.get("command")
        if command == "list_agents":
            self._respond_agent_list(message.sender_id)
        elif command == "agent_status":
            agent_id = message.content.get("agent_id")
            if agent_id in self.agents:
                self.agents[agent_id]._respond_status(message.sender_id)
        elif command == "shutdown_all":
            self.shutdown_all_agents()
    
    def _handle_broadcast_message(self, message: Message):
        """处理广播消息"""
        if message.receiver_id == "broadcast":
            print(f"System received broadcast message from {message.sender_id}")
    
    def _respond_agent_list(self, requester_id: str):
        """响应智能体列表查询"""
        agent_list = [
            {
                "agent_id": agent.agent_id,
                "name": agent.name,
                "status": agent.status.value
            }
            for agent in self.agents.values()
        ]
        
        response = Message(
            sender_id="system",
            receiver_id=requester_id,
            msg_type=MessageType.RESPONSE,
            content={
                "agents": agent_list,
                "total_count": len(agent_list)
            }
        )
        MessageRouter(self.message_bus).route_message(response)
    
    def register_agent(self, agent: Agent):
        """注册智能体"""
        if agent.agent_id in self.agents:
            raise ValueError(f"Agent with ID {agent.agent_id} already registered")
        
        self.agents[agent.agent_id] = agent
        print(f"Registered agent: {agent.name} ({agent.agent_id})")
    
    def unregister_agent(self, agent_id: str):
        """注销智能体"""
        if agent_id in self.agents:
            del self.agents[agent_id]
            print(f"Unregistered agent: {agent_id}")
    
    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """获取智能体"""
        return self.agents.get(agent_id)
    
    def start_monitoring(self):
        """启动监控"""
        if self._monitor_thread is None or not self._monitor_thread.is_alive():
            self._stop_flag.clear()
            self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self._monitor_thread.start()
    
    def _monitor_loop(self):
        """监控循环"""
        while not self._stop_flag.is_set():
            # 可以添加健康检查、性能监控等
            self._check_agent_health()
            time.sleep(5)  # 每5秒检查一次
    
    def _check_agent_health(self):
        """检查智能体健康状态"""
        for agent_id, agent in list(self.agents.items()):
            if agent.status == AgentStatus.TERMINATED:
                print(f"Agent {agent_id} has terminated, removing from registry")
                self.unregister_agent(agent_id)
    
    def shutdown_all_agents(self):
        """关闭所有智能体"""
        print("Shutting down all agents...")
        for agent in list(self.agents.values()):
            agent.terminate()
        self._stop_flag.set()
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=3.0)
        print("All agents terminated")
    
    def send_system_message(self, receiver_id: str, command: str, content: Dict[str, Any] = None):
        """发送系统命令"""
        if content is None:
            content = {}
        content["command"] = command
        
        message = Message(
            sender_id="system",
            receiver_id=receiver_id,
            msg_type=MessageType.SYSTEM,
            content=content
        )
        MessageRouter(self.message_bus).route_message(message)

# 全局访问点
agent_manager = AgentManager()