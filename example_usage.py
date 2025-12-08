from agentscope_core.agent_base import Agent
from agentscope_core.message_system import MessageType
from agentscope_core.runtime import agent_manager
import time

class SimpleAgent(Agent):
    """简单智能体示例"""
    
    def _on_initialize(self):
        print(f"[{self.name}] Initializing...")
        self.update_state("initialized_at", time.time())
    
    def handle_task(self, message: Message):
        """处理任务"""
        print(f"[{self.name}] Received task: {message.content}")
        
        # 模拟处理
        task_id = message.content.get("task_id", "unknown")
        result = f"Processed task {task_id} successfully"
        
        # 发送响应
        response = {
            "task_id": task_id,
            "result": result,
            "status": "completed"
        }
        
        self.send_message(
            message.sender_id,
            MessageType.RESPONSE,
            response
        )
    
    def _on_terminate(self):
        print(f"[{self.name}] Terminating and cleaning up resources...")
    
    def _on_idle(self):
        """空闲时的心跳"""
        if time.time() - self.get_state("last_heartbeat", 0) > 5:
            self.update_state("last_heartbeat", time.time())
            # 可以在这里添加空闲时的处理逻辑

# 启动示例
if __name__ == "__main__":
    # 设置日志
    import logging
    from agentscope_core.utils import setup_logging
    setup_logging(level=logging.INFO)
    
    # 创建两个智能体
    agent1 = SimpleAgent("agent_001", "Worker1")
    agent2 = SimpleAgent("agent_002", "Worker2")
    
    # 注册到管理器
    agent_manager.register_agent(agent1)
    agent_manager.register_agent(agent2)
    
    # 启动监控
    agent_manager.start_monitoring()
    
    # 启动智能体
    agent1.start()
    agent2.start()
    
    print("Agents started. Sending test message from agent1 to agent2...")
    
    # 发送测试消息
    agent1.send_message(
        "agent_002",
        MessageType.TASK,
        {
            "task_id": "task_123",
            "description": "Process this data",
            "data": {"key": "value"}
        }
    )
    
    # 等待处理
    time.sleep(2)
    
    # 查询所有智能体
    agent_manager.send_system_message(
        "system",  # 发送给系统
        "list_agents"
    )
    
    # 再等待一会儿查看响应
    time.sleep(2)
    
    # 关闭所有智能体
    print("Shutting down all agents...")
    agent_manager.shutdown_all_agents()
    
    print("Done.")