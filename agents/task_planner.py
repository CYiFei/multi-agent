from typing import Dict, List, Any, Optional, Tuple
import logging
from .task_engine import Task, TaskStatus
from .agent_impl import BasicAgent
from runtime.runtime_manager import RuntimeManager

class TaskDecompositionStrategy:
    """任务分解策略基类"""
    
    def __init__(self):
        self.logger = logging.getLogger("task_decomposition")
    
    def decompose(self, task: Task, context: Dict[str, Any]) -> List[Task]:
        """
        分解任务为子任务
        
        Args:
            task: 要分解的任务
            context: 上下文信息
            
        Returns:
            子任务列表
        """
        raise NotImplementedError("Subclasses must implement decompose method")

class SimpleTaskDecomposition(TaskDecompositionStrategy):
    """简单任务分解策略"""
    
    def decompose(self, task: Task, context: Dict[str, Any]) -> List[Task]:
        """基于任务描述中的关键词进行简单分解"""
        description = task.description.lower()
        subtasks = []
        
        if "and" in description:
            # 如果描述中有"and"，则按"and"分割成多个子任务
            parts = description.split("and")
            for i, part in enumerate(parts):
                subtask = Task(
                    task_id=None,
                    description=part.strip(),
                    payload=task.payload.copy(),
                    priority=task.priority,
                    creator_id=task.creator_id
                )
                subtask.add_dependency(task.task_id)  # 依赖父任务
                subtasks.append(subtask)
        else:
            # 简单任务不分割
            subtasks.append(task)
            
        return subtasks

class ComplexTaskDecomposition(TaskDecompositionStrategy):
    """复杂任务分解策略"""
    
    def decompose(self, task: Task, context: Dict[str, Any]) -> List[Task]:
        """基于任务类型和上下文进行复杂分解"""
        task_type = task.payload.get("task_type", "")
        subtasks = []
        
        if task_type == "data_processing":
            # 数据处理任务分解为读取、处理、写入三个步骤
            read_task = Task(
                task_id=None,
                description=f"Read data for {task.description}",
                payload={"operation": "read", "source": task.payload.get("source")},
                priority=task.priority,
                creator_id=task.creator_id
            )
            read_task.add_dependency(task.task_id)
            
            process_task = Task(
                task_id=None,
                description=f"Process data for {task.description}",
                payload={"operation": "process", "processor": task.payload.get("processor")},
                priority=task.priority,
                creator_id=task.creator_id
            )
            process_task.add_dependency(read_task.task_id)
            
            write_task = Task(
                task_id=None,
                description=f"Write data for {task.description}",
                payload={"operation": "write", "destination": task.payload.get("destination")},
                priority=task.priority,
                creator_id=task.creator_id
            )
            write_task.add_dependency(process_task.task_id)
            
            subtasks.extend([read_task, process_task, write_task])
        else:
            # 默认使用简单分解
            simple_decomposer = SimpleTaskDecomposition()
            subtasks = simple_decomposer.decompose(task, context)
            
        return subtasks

class TaskAllocationStrategy:
    """任务分配策略基类"""
    
    def __init__(self):
        self.logger = logging.getLogger("task_allocation")
    
    def allocate(self, tasks: List[Task], agents: Dict[str, BasicAgent], context: Dict[str, Any]) -> None:
        """
        将任务分配给智能体
        
        Args:
            tasks: 要分配的任务列表
            agents: 可用智能体字典
            context: 上下文信息
        """
        raise NotImplementedError("Subclasses must implement allocate method")

class RoundRobinAllocation(TaskAllocationStrategy):
    """轮询分配策略"""
    
    def __init__(self):
        super().__init__()
        self.last_agent_index = 0
    
    def allocate(self, tasks: List[Task], agents: Dict[str, BasicAgent], context: Dict[str, Any]) -> None:
        """轮询方式分配任务"""
        agent_ids = list(agents.keys())
        if not agent_ids:
            self.logger.warning("No agents available for task allocation")
            return
        
        for i, task in enumerate(tasks):
            agent_id = agent_ids[self.last_agent_index % len(agent_ids)]
            task.assign_to(agent_id)
            self.last_agent_index += 1

class LoadBalancedAllocation(TaskAllocationStrategy):
    """负载均衡分配策略"""
    
    def allocate(self, tasks: List[Task], agents: Dict[str, BasicAgent], context: Dict[str, Any]) -> None:
        """基于智能体负载情况分配任务"""
        if not agents:
            self.logger.warning("No agents available for task allocation")
            return
        
        # 计算每个智能体的负载（未完成任务数）
        agent_loads = {}
        for agent_id, agent in agents.items():
            # 这里简化处理，实际应用中可以从agent的状态管理器获取更准确的信息
            agent_loads[agent_id] = len([t for t in context.get("all_tasks", []) 
                                        if t.assigned_agent == agent_id and 
                                        t.status not in [TaskStatus.COMPLETED, TaskStatus.FAILED]])
        
        # 按负载排序，优先分配给负载较低的智能体
        sorted_agents = sorted(agent_loads.items(), key=lambda x: x[1])
        
        for i, task in enumerate(tasks):
            agent_id = sorted_agents[i % len(sorted_agents)][0]
            task.assign_to(agent_id)

class PriorityBasedAllocation(TaskAllocationStrategy):
    """优先级分配策略"""
    
    def allocate(self, tasks: List[Task], agents: Dict[str, BasicAgent], context: Dict[str, Any]) -> None:
        """基于任务优先级和智能体能力分配任务"""
        if not agents:
            self.logger.warning("No agents available for task allocation")
            return
        
        # 按任务优先级排序
        sorted_tasks = sorted(tasks, key=lambda t: t.priority, reverse=True)
        
        # 获取智能体能力信息（简化处理）
        agent_capabilities = context.get("agent_capabilities", {})
        
        for task in sorted_tasks:
            # 查找最适合的智能体
            best_agent = self._find_best_agent(task, agents, agent_capabilities)
            if best_agent:
                task.assign_to(best_agent)
            else:
                # 如果找不到最适合的，使用轮询方式
                agent_ids = list(agents.keys())
                if agent_ids:
                    task.assign_to(agent_ids[hash(task.task_id) % len(agent_ids)])
    
    def _find_best_agent(self, task: Task, agents: Dict[str, BasicAgent], 
                         capabilities: Dict[str, List[str]]) -> Optional[str]:
        """查找最适合处理任务的智能体"""
        task_type = task.payload.get("task_type", "default")
        
        # 查找具备相应能力的智能体
        suitable_agents = []
        for agent_id, agent_caps in capabilities.items():
            if task_type in agent_caps or "general" in agent_caps:
                suitable_agents.append(agent_id)
        
        if suitable_agents:
            # 在适合的智能体中返回第一个
            return suitable_agents[0]
        
        return None

class TaskPlanner:
    """任务规划器"""
    
    def __init__(self, agent: BasicAgent):
        self.agent = agent
        self.logger = logging.getLogger(f"task_planner.{agent.agent_id}")
        self.decomposition_strategy = ComplexTaskDecomposition()
        self.allocation_strategy = LoadBalancedAllocation()
        
        # 注册相关消息处理器
        self.agent.register_handler("task_planning_request", self._handle_planning_request)
    
    def set_decomposition_strategy(self, strategy: TaskDecompositionStrategy) -> None:
        """设置任务分解策略"""
        self.decomposition_strategy = strategy
    
    def set_allocation_strategy(self, strategy: TaskAllocationStrategy) -> None:
        """设置任务分配策略"""
        self.allocation_strategy = strategy
    
    def plan_and_allocate(self, task: Task) -> List[Task]:
        """
        规划和分配任务
        
        Args:
            task: 要规划的任务
            
        Returns:
            分解后的任务列表
        """
        try:
            # 1. 获取系统上下文
            context = self._get_system_context()
            
            # 2. 分解任务
            subtasks = self.decomposition_strategy.decompose(task, context)
            self.logger.info(f"Decomposed task {task.task_id} into {len(subtasks)} subtasks")
            
            # 3. 获取可用智能体
            runtime = RuntimeManager()
            agents = runtime.get_all_agents()
            
            # 4. 分配任务
            self.allocation_strategy.allocate(subtasks, agents, context)
            self.logger.info(f"Allocated {len(subtasks)} tasks to agents")
            
            # 5. 提交任务到系统
            for subtask in subtasks:
                # 这里应该通过某种机制提交任务，比如发送消息给任务管理器
                self._submit_task_for_execution(subtask)
            
            return subtasks
            
        except Exception as e:
            self.logger.error(f"Error in task planning: {e}")
            raise
    
    def _get_system_context(self) -> Dict[str, Any]:
        """获取系统上下文信息"""
        runtime = RuntimeManager()
        agents = runtime.get_all_agents()
        
        # 获取智能体能力信息（示例）
        agent_capabilities = {}
        for agent_id, agent in agents.items():
            caps = agent.state_manager.get("capabilities", ["general"])
            agent_capabilities[agent_id] = caps
        
        return {
            "agents": agents,
            "agent_count": len(agents),
            "agent_capabilities": agent_capabilities,
            "system_load": runtime.get_system_status()
        }
    
    def _submit_task_for_execution(self, task: Task) -> None:
        """提交任务执行"""
        if task.assigned_agent:
            # 发送任务分配消息给指定智能体
            runtime = RuntimeManager()
            agent = runtime.get_agent(task.assigned_agent)
            if agent:
                message = Message(
                    sender_id=self.agent.agent_id,
                    receiver_id=task.assigned_agent,
                    msg_type="task_assignment",
                    content={
                        "task": task.to_dict()
                    }
                )
                self.agent.router.route_message(message)
    
    def _handle_planning_request(self, message: Message) -> Dict[str, Any]:
        """处理任务规划请求"""
        task_data = message.content.get("task", {})
        task = Task(
            task_id=task_data.get("task_id"),
            description=task_data.get("description", ""),
            payload=task_data.get("payload", {}),
            priority=task_data.get("priority", 2)
        )
        
        try:
            subtasks = self.plan_and_allocate(task)
            return {
                "status": "success",
                "task_id": task.task_id,
                "subtasks_count": len(subtasks)
            }
        except Exception as e:
            self.logger.error(f"Error handling planning request: {e}")
            return {
                "status": "error",
                "message": str(e)
            }