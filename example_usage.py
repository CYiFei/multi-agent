import logging
import time
from runtime.runtime_manager import RuntimeManager
from agents.agent_impl import BasicAgent
from messaging.message import MessageType

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def main():
    """主函数"""
    # 获取运行时管理器（单例）
    runtime = RuntimeManager()
    
    # 创建两个智能体
    agent1 = BasicAgent(
        agent_id="agent_001",
        name="Worker1",
        router=runtime.router,
        persistent_state=True
    )
    
    agent2 = BasicAgent(
        agent_id="agent_002",
        name="Worker2",
        router=runtime.router,
        persistent_state=True
    )
    
    # 注册智能体
    runtime.register_agent(agent1)
    runtime.register_agent(agent2)
    
    # 启动智能体
    agent1.start()
    agent2.start()
    
    print("Agents started. Sending test messages...")
    
    # 发送测试消息
    msg_id = agent1.send_message(
        receiver_id="agent_002",
        msg_type=MessageType.TASK,
        content={
            "task_id": "task_123",
            "description": "Process this data",
            "data": {"key": "value"}
        }
    )
    
    print(f"Sent message with ID: {msg_id}")
    
    # 等待处理
    time.sleep(2)
    
    # 发送系统命令查询状态
    agent1.send_message(
        receiver_id="agent_002",
        msg_type=MessageType.SYSTEM,
        content={"command": "status"}
    )
    
    # 再等待一会儿
    time.sleep(2)
    
    # 获取系统状态
    system_status = runtime.get_system_status()
    print(f"System status: {system_status}")
    
    # 等待更多时间以观察心跳
    print("Waiting to observe heartbeat...")
    time.sleep(6)
    
    # 停止系统
    print("Shutting down system...")
    runtime.shutdown()
    
    print("Done.")

if __name__ == "__main__":
    main()