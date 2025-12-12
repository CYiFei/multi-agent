import logging
import time
import os
from dotenv import load_dotenv

# 加载.env文件
load_dotenv()

from runtime.runtime_manager import RuntimeManager
from agents.llm_agent import LLMAgent
from tools.ecosystem import Qwen3MaxAdapter
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
    
    # 从环境变量读取API密钥
    api_key = os.getenv("QWEN_API_KEY", "your_api_key_here")
    
    # 创建Qwen3-Max适配器
    llm_adapter = Qwen3MaxAdapter(model_name="qwen3-max", api_key=api_key)
    
    # 创建LLM智能体
    llm_agent = LLMAgent(
        agent_id="llm_agent_001",
        name="Qwen3MaxBot",
        router=runtime.router,
        llm_adapter=llm_adapter,
        persistent_state=True
    )

    # 注册智能体
    runtime.register_agent(llm_agent)
    
    # 启动智能体
    llm_agent.start()
    
    print("LLM Agent started. Testing conversation...")
    
    # 模拟用户发送聊天消息
    test_messages = [
        "你好，你能介绍一下自己吗？",
        "我想了解人工智能的发展趋势",
        "对于自然语言处理技术，你有什么看法？",
        "谢谢你的回答！"
    ]
    
    for i, msg_text in enumerate(test_messages):
        print(f"\n--- 发送消息 {i+1}: {msg_text} ---")
        
        # 发送测试消息
        msg_id = llm_agent.send_message(
            receiver_id="llm_agent_001",  # 发给自己是为了演示，实际应用中会发给其他智能体或用户接口
            msg_type="chat_message",
            content={
                "text": msg_text
            }
        )
        
        print(f"已发送消息，ID: {msg_id}")
        
        # 等待处理（增加等待时间）
        wait_time = 15  # 增加等待时间以确保消息完全处理
        elapsed_time = 0
        check_interval = 2
        
        # 循环检查直到超时或收到回复
        while elapsed_time < wait_time:
            time.sleep(check_interval)
            elapsed_time += check_interval
            
            # 显示系统状态
            system_status = runtime.get_system_status()
            print(f"系统状态: {system_status}")
            
            # 显示对话历史
            history = llm_agent.get_conversation_history()
            print(f"当前对话历史 ({len(history)} 条):")
            
            # 检查是否有新的回复（检查最后一条是否是assistant的回复）
            if history and history[-1]['role'] == 'assistant':
                # 如果最新的消息是assistant的回复，说明已经处理完了
                break
                
            print(f"等待回复中... ({elapsed_time}/{wait_time} 秒)")

    # 添加最终的对话历史展示
    print("\n--- 最终对话历史 ---")
    final_history = llm_agent.get_conversation_history()
    print(f"最终对话历史 ({len(final_history)} 条):")
    for i, entry in enumerate(final_history):
        print(f"  {i+1}. {entry['role']}: {entry['content'][:100]}{'...' if len(entry['content']) > 100 else ''}")


    # 测试任务处理功能
    print("\n--- 测试任务处理功能 ---")
    task_msg_id = llm_agent.send_message(
        receiver_id="llm_agent_001",
        msg_type=MessageType.TASK,
        content={
            "task_id": "task_llm_123",
            "description": "分析近期科技行业的趋势，并给出投资建议"
        }
    )
    
    print(f"已发送任务消息，ID: {task_msg_id}")
    
    # 等待处理
    time.sleep(50)
    
    # 获取系统状态
    system_status = runtime.get_system_status()
    print(f"\n系统状态: {system_status}")
    
    # 停止系统
    print("\n关闭系统...")
    runtime.shutdown()
    
    print("完成!")

if __name__ == "__main__":
    main()