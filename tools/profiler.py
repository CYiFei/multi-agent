"""
Performance Profiling Tools
"""
from typing import Dict, List, Any, Optional
import time
import psutil
import threading
from collections import defaultdict
from agents.base_agent import AgentStatus
from agents.task import TaskStatus
from runtime.types import RuntimeManagerInterface

class PerformanceProfiler:
    """性能分析器"""
    
    def __init__(self, runtime_manager: RuntimeManagerInterface):
        self.runtime_manager = runtime_manager
        self.profiling_active = False
        self.profiles: Dict[str, List] = defaultdict(list)
        self.profile_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
    def start_profiling(self, interval: float = 1.0) -> None:
        """开始性能分析"""
        if self.profiling_active:
            return
            
        self.profiling_active = True
        self.stop_event.clear()
        self.profile_thread = threading.Thread(
            target=self._profile_loop,
            args=(interval,),
            daemon=True
        )
        self.profile_thread.start()
    
    def stop_profiling(self) -> None:
        """停止性能分析"""
        if not self.profiling_active:
            return
            
        self.profiling_active = False
        self.stop_event.set()
        if self.profile_thread and self.profile_thread.is_alive():
            self.profile_thread.join(timeout=2.0)
    
    def _profile_loop(self, interval: float) -> None:
        """性能分析循环"""
        while not self.stop_event.is_set():
            try:
                self._collect_profile_data()
                time.sleep(interval)
            except Exception as e:
                print(f"Error in profile loop: {e}")
                time.sleep(1.0)
    
    def _collect_profile_data(self) -> None:
        """收集性能数据"""
        timestamp = time.time()
        
        # 收集系统级指标
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory_info = psutil.virtual_memory()
        disk_io = psutil.disk_io_counters()
        
        system_profile = {
            "timestamp": timestamp,
            "cpu_percent": cpu_percent,
            "memory_percent": memory_info.percent,
            "memory_used": memory_info.used,
            "memory_total": memory_info.total,
            "disk_read_bytes": disk_io.read_bytes if disk_io else 0,
            "disk_write_bytes": disk_io.write_bytes if disk_io else 0
        }
        
        self.profiles["system"].append(system_profile)
        
        # 收集应用级指标
        app_profile = self._collect_app_metrics()
        app_profile["timestamp"] = timestamp
        self.profiles["application"].append(app_profile)
    
    def _collect_app_metrics(self) -> Dict[str, Any]:
        """收集应用级指标"""
        agents = self.runtime_manager.get_all_agents()
        
        # 统计智能体状态
        status_counts = defaultdict(int)
        total_tasks = 0
        completed_tasks = 0
        failed_tasks = 0
        
        for agent in agents.values():
            status_counts[agent.status.value] += 1
            
            # 统计任务信息
            if hasattr(agent, 'task_engine'):
                tasks = agent.task_engine.get_all_tasks()
                total_tasks += len(tasks)
                completed_tasks += len([t for t in tasks if t["status"] == TaskStatus.COMPLETED.value])
                failed_tasks += len([t for t in tasks if t["status"] == TaskStatus.FAILED.value])
        
        return {
            "agent_count": len(agents),
            "agent_status_distribution": dict(status_counts),
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "failed_tasks": failed_tasks,
            "message_queue_size": self.runtime_manager.get_system_status().get("message_queue_size", 0)
        }
    
    def get_performance_report(self) -> Dict[str, Any]:
        """获取性能报告"""
        if not self.profiles:
            return {"error": "No profiling data available"}
        
        # 计算系统指标统计
        system_data = self.profiles["system"]
        app_data = self.profiles["application"]
        
        if not system_data or not app_data:
            return {"error": "Insufficient profiling data"}
        
        # 系统指标统计
        cpu_values = [d["cpu_percent"] for d in system_data]
        memory_values = [d["memory_percent"] for d in system_data]
        
        system_stats = {
            "cpu_avg": sum(cpu_values) / len(cpu_values) if cpu_values else 0,
            "cpu_max": max(cpu_values) if cpu_values else 0,
            "cpu_min": min(cpu_values) if cpu_values else 0,
            "memory_avg": sum(memory_values) / len(memory_values) if memory_values else 0,
            "memory_max": max(memory_values) if memory_values else 0,
            "memory_min": min(memory_values) if memory_values else 0
        }
        
        # 应用指标统计
        agent_counts = [d["agent_count"] for d in app_data]
        task_counts = [d["total_tasks"] for d in app_data]
        
        app_stats = {
            "avg_agents": sum(agent_counts) / len(agent_counts) if agent_counts else 0,
            "max_agents": max(agent_counts) if agent_counts else 0,
            "avg_tasks": sum(task_counts) / len(task_counts) if task_counts else 0,
            "max_tasks": max(task_counts) if task_counts else 0
        }
        
        return {
            "system_stats": system_stats,
            "app_stats": app_stats,
            "data_points": len(system_data),
            "duration_seconds": system_data[-1]["timestamp"] - system_data[0]["timestamp"] if len(system_data) > 1 else 0
        }
    
    def get_profile_data(self) -> Dict[str, List]:
        """获取原始性能数据"""
        return dict(self.profiles)
    
    def clear_profiles(self) -> None:
        """清空性能数据"""
        self.profiles.clear()