from typing import Dict, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from agents.agent_impl import BasicAgent

class RuntimeManagerInterface:
    """运行时管理器接口定义"""
    
    def get_system_status(self) -> Dict[str, Any]:
        raise NotImplementedError()
    
    def get_agent(self, agent_id: str) -> Optional['BasicAgent']:
        raise NotImplementedError()
    
    def get_all_agents(self) -> Dict[str, 'BasicAgent']:
        raise NotImplementedError()