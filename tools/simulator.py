"""
Agent Behavior Simulator
"""
from typing import Dict, List, Any, Optional, Callable
import time
import random
from agents.agent_impl import BasicAgent
from agents.task import Task
from messaging.router import MessageRouter
from messaging.pubsub import PubSubBus
from runtime.runtime_manager import RuntimeManager

class AgentBehaviorSimulator:
    """智能体行为模拟器"""
    
    def __init__(self, runtime_manager: RuntimeManager):
        self.runtime_manager = runtime_manager
        self.simulation_active = False
        self.simulated_agents: Dict[str, BasicAgent] = {}
        self.behavior_patterns: Dict[str, Callable] = {}
        self.simulation_speed = 1.0  # 1.0表示正常速度，<1.0表示加速，>1.0表示减速
        
    def create_simulated_agent(self, agent_id: str, name: str, behavior_pattern: str = "default") -> BasicAgent:
        """创建模拟智能体"""
        # 创建独立的消息总线和路由器用于模拟
        sim_pubsub = PubSubBus()
        sim_router = MessageRouter(sim_pubsub)
        sim_pubsub.start()
        
        agent = BasicAgent(
            agent_id=agent_id,
            name=name,
            router=sim_router,
            persistent_state=False
        )
        
        # 应用行为模式
        self._apply_behavior_pattern(agent, behavior_pattern)
        
        self.simulated_agents[agent_id] = agent
        return agent
    
    def _apply_behavior_pattern(self, agent: BasicAgent, pattern: str) -> None:
        """应用行为模式"""
        if pattern == "chatty":
            # 健谈型：频繁发送消息
            agent.register_handler("simulate_chatty", self._chatty_behavior)
        elif pattern == "lazy":
            # 懒惰型：很少响应
            agent.register_handler("simulate_lazy", self._lazy_behavior)
        elif pattern == "workaholic":
            # 工作狂：持续处理任务
            agent.register_handler("simulate_workaholic", self._workaholic_behavior)
        else:
            # 默认行为
            agent.register_handler("simulate_default", self._default_behavior)
    
    def _chatty_behavior(self, message) -> Dict[str, Any]:
        """健谈型行为"""
        time.sleep(random.uniform(0.1, 0.5) / self.simulation_speed)
        return {"status": "chatty_response", "message": "Thanks for your message!"}
    
    def _lazy_behavior(self, message) -> Dict[str, Any]:
        """懒惰型行为"""
        # 70%概率不响应
        if random.random() < 0.7:
            time.sleep(random.uniform(0.5, 2.0) / self.simulation_speed)
            return {"status": "no_response"}
        else:
            time.sleep(random.uniform(0.2, 1.0) / self.simulation_speed)
            return {"status": "lazy_response", "message": "Okay, I got it."}
    
    def _workaholic_behavior(self, message) -> Dict[str, Any]:
        """工作狂行为"""
        # 快速处理任务
        time.sleep(random.uniform(0.05, 0.2) / self.simulation_speed)
        return {"status": "work_completed", "result": "Task done efficiently"}
    
    def _default_behavior(self, message) -> Dict[str, Any]:
        """默认行为"""
        time.sleep(random.uniform(0.1, 1.0) / self.simulation_speed)
        return {"status": "default_response", "message": "Processed"}
    
    def run_simulation(self, duration: float = 60.0) -> None:
        """运行模拟"""
        self.simulation_active = True
        start_time = time.time()
        
        # 启动所有模拟智能体
        for agent in self.simulated_agents.values():
            agent.start()
        
        # 运行模拟
        while self.simulation_active and (time.time() - start_time) < duration:
            # 模拟智能体间的消息传递
            self._simulate_interactions()
            time.sleep(0.5 / self.simulation_speed)
        
        # 停止所有模拟智能体
        for agent in self.simulated_agents.values():
            agent.stop()
    
    def _simulate_interactions(self) -> None:
        """模拟智能体间的交互"""
        agent_ids = list(self.simulated_agents.keys())
        if len(agent_ids) < 2:
            return
            
        # 随机选择发送者和接收者
        sender_id = random.choice(agent_ids)
        receiver_id = random.choice([aid for aid in agent_ids if aid != sender_id])
        
        sender = self.simulated_agents[sender_id]
        
        # 发送模拟消息
        message_type = random.choice(["simulate_chatty", "simulate_default", "task"])
        sender.send_message(
            receiver_id=receiver_id,
            msg_type=message_type,
            content={
                "simulation_id": f"sim_msg_{int(time.time()*1000)}",
                "type": message_type,
                "data": f"Simulated message from {sender_id} to {receiver_id}"
            }
        )
    
    def stop_simulation(self) -> None:
        """停止模拟"""
        self.simulation_active = False
    
    def generate_behavior_report(self) -> Dict[str, Any]:
        """生成行为报告"""
        report = {
            "simulation_active": self.simulation_active,
            "agent_count": len(self.simulated_agents),
            "agents": {}
        }
        
        for agent_id, agent in self.simulated_agents.items():
            report["agents"][agent_id] = {
                "name": agent.name,
                "status": agent.status.value if agent.status else "unknown"
            }
            
            # 添加任务统计（如果有任务引擎）
            if hasattr(agent, 'task_engine'):
                tasks = agent.task_engine.get_all_tasks()
                report["agents"][agent_id]["task_stats"] = {
                    "total_tasks": len(tasks),
                    "completed_tasks": len([t for t in tasks if t["status"] == "completed"]),
                    "failed_tasks": len([t for t in tasks if t["status"] == "failed"])
                }
        
        return report