from typing import Dict, List, Any, Optional
import threading
import time
import logging
from agents.base_agent import AgentStatus
from agents.task import TaskStatus
from .types import RuntimeManagerInterface

class ExecutionMonitor:
    """执行监控器"""
    
    def __init__(self, runtime_manager: RuntimeManagerInterface):
        self.runtime_manager = runtime_manager
        self.logger = logging.getLogger("execution_monitor")
        self.monitoring = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
    def start_monitoring(self) -> None:
        """开始监控"""
        if self.monitoring:
            return
            
        self.monitoring = True
        self.stop_event.clear()
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        self.logger.info("Execution monitoring started")
    
    def stop_monitoring(self) -> None:
        """停止监控"""
        if not self.monitoring:
            return
            
        self.monitoring = False
        self.stop_event.set()
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2.0)
        self.logger.info("Execution monitoring stopped")
    
    def _monitor_loop(self) -> None:
        """监控循环"""
        while not self.stop_event.is_set():
            try:
                self._collect_metrics()
                self._check_system_health()
                time.sleep(5.0)  # 每5秒检查一次
            except Exception as e:
                self.logger.error(f"Error in monitor loop: {e}")
                time.sleep(1.0)
    
    def _collect_metrics(self) -> None:
        """收集系统指标"""
        metrics = self.get_system_metrics()
        self.logger.debug(f"System metrics: {metrics}")
        
        # 检查是否有性能问题
        if metrics["high_priority_tasks"] > 10:
            self.logger.warning(f"High number of high priority tasks: {metrics['high_priority_tasks']}")
        
        if metrics["failed_tasks"] > metrics["total_tasks"] * 0.1:  # 超过10%任务失败
            self.logger.warning("High task failure rate detected")
    
    def _check_system_health(self) -> None:
        """检查系统健康状态"""
        system_status = self.runtime_manager.get_system_status()
        
        # 检查消息队列
        if system_status["message_queue_size"] > 100:
            self.logger.warning(f"High message queue size: {system_status['message_queue_size']}")
        
        # 检查智能体状态
        agents = self.runtime_manager.get_all_agents()
        terminated_agents = [aid for aid, agent in agents.items() 
                           if agent.status == AgentStatus.TERMINATED]
        if terminated_agents:
            self.logger.warning(f"Terminated agents detected: {terminated_agents}")
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """获取系统指标"""
        agents = self.runtime_manager.get_all_agents()
        total_tasks = 0
        completed_tasks = 0
        failed_tasks = 0
        high_priority_tasks = 0
        
        # 收集所有智能体的任务信息
        for agent in agents.values():
            if hasattr(agent, 'task_engine'):
                tasks = agent.task_engine.get_all_tasks()
                total_tasks += len(tasks)
                completed_tasks += len([t for t in tasks if t["status"] == TaskStatus.COMPLETED.value])
                failed_tasks += len([t for t in tasks if t["status"] == TaskStatus.FAILED.value])
                high_priority_tasks += len([t for t in tasks if t["priority"] >= 3])
        
        return {
            "total_agents": len(agents),
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "failed_tasks": failed_tasks,
            "high_priority_tasks": high_priority_tasks,
            "system_uptime": time.time() - self.runtime_manager.get_system_status()["timestamp"]
        }
    
    def get_agent_metrics(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """获取特定智能体的指标"""
        agent = self.runtime_manager.get_agent(agent_id)
        if not agent:
            return None
            
        metrics = {
            "agent_id": agent_id,
            "status": agent.status.value,
            "task_count": 0,
            "completed_tasks": 0,
            "failed_tasks": 0
        }
        
        if hasattr(agent, 'task_engine'):
            tasks = agent.task_engine.get_all_tasks()
            metrics["task_count"] = len(tasks)
            metrics["completed_tasks"] = len([t for t in tasks if t["status"] == TaskStatus.COMPLETED.value])
            metrics["failed_tasks"] = len([t for t in tasks if t["status"] == TaskStatus.FAILED.value])
        
        return metrics
    
    def generate_report(self) -> Dict[str, Any]:
        """生成监控报告"""
        system_metrics = self.get_system_metrics()
        agents = self.runtime_manager.get_all_agents()
        
        agent_reports = {}
        for agent_id in agents:
            agent_metrics = self.get_agent_metrics(agent_id)
            if agent_metrics:
                agent_reports[agent_id] = agent_metrics
        
        return {
            "timestamp": time.time(),
            "system_metrics": system_metrics,
            "agent_reports": agent_reports
        }