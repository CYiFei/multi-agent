from typing import Dict, List, Any, Optional, Set
from enum import Enum
import uuid
import time
import logging
from .agent_impl import BasicAgent
from messaging.message import Message, MessageType
from runtime.runtime_manager import RuntimeManager

class ConversationState(Enum):
    """对话状态"""
    ACTIVE = "active"
    PENDING = "pending"
    RESOLVED = "resolved"
    CLOSED = "closed"

class ConflictResolutionStrategy(Enum):
    """冲突解决策略"""
    VOTING = "voting"           # 投票
    AUTHORITY = "authority"     # 权威决策
    CONSISTENCY = "consistency" # 一致性协商

class ConsensusMethod(Enum):
    """共识方法"""
    MAJORITY = "majority"       # 简单多数
    UNANIMOUS = "unanimous"     # 全体一致
    WEIGHTED = "weighted"       # 加权投票

class DialogueManager:
    """对话管理器"""
    
    def __init__(self, agent: BasicAgent):
        self.agent = agent
        self.logger = logging.getLogger(f"dialogue_manager.{agent.agent_id}")
        self.active_conversations: Dict[str, Dict[str, Any]] = {}
        
        # 注册对话相关消息处理器
        self.agent.register_handler("dialogue_init", self._handle_dialogue_init)
        self.agent.register_handler("dialogue_message", self._handle_dialogue_message)
        self.agent.register_handler("dialogue_end", self._handle_dialogue_end)
    
    def initiate_dialogue(self, participants: List[str], topic: str, 
                         initial_message: Optional[str] = None) -> str:
        """
        发起对话
        
        Args:
            participants: 参与者列表
            topic: 对话主题
            initial_message: 初始消息
            
        Returns:
            对话ID
        """
        conversation_id = str(uuid.uuid4())
        
        # 创建对话记录
        self.active_conversations[conversation_id] = {
            "participants": participants,
            "topic": topic,
            "messages": [],
            "initiator": self.agent.agent_id,
            "created_at": time.time(),
            "state": ConversationState.ACTIVE
        }
        
        # 通知所有参与者
        for participant_id in participants:
            if participant_id != self.agent.agent_id:
                message = Message(
                    sender_id=self.agent.agent_id,
                    receiver_id=participant_id,
                    msg_type="dialogue_init",
                    content={
                        "conversation_id": conversation_id,
                        "topic": topic,
                        "participants": participants,
                        "initial_message": initial_message
                    }
                )
                self.agent.router.route_message(message)
        
        self.logger.info(f"Initiated dialogue {conversation_id} with topic: {topic}")
        return conversation_id
    
    def send_dialogue_message(self, conversation_id: str, content: str, 
                             recipients: Optional[List[str]] = None) -> None:
        """
        发送对话消息
        
        Args:
            conversation_id: 对话ID
            content: 消息内容
            recipients: 接收者列表，如果为None则发送给所有参与者
        """
        if conversation_id not in self.active_conversations:
            self.logger.warning(f"Conversation {conversation_id} not found")
            return
        
        conversation = self.active_conversations[conversation_id]
        participants = recipients or conversation["participants"]
        
        # 记录消息
        message_record = {
            "sender": self.agent.agent_id,
            "content": content,
            "timestamp": time.time()
        }
        conversation["messages"].append(message_record)
        
        # 发送消息给参与者
        for participant_id in participants:
            if participant_id != self.agent.agent_id:
                message = Message(
                    sender_id=self.agent.agent_id,
                    receiver_id=participant_id,
                    msg_type="dialogue_message",
                    content={
                        "conversation_id": conversation_id,
                        "content": content,
                        "sender": self.agent.agent_id
                    }
                )
                self.agent.router.route_message(message)
    
    def end_dialogue(self, conversation_id: str, reason: str = "completed") -> None:
        """
        结束对话
        
        Args:
            conversation_id: 对话ID
            reason: 结束原因
        """
        if conversation_id not in self.active_conversations:
            self.logger.warning(f"Conversation {conversation_id} not found")
            return
        
        conversation = self.active_conversations[conversation_id]
        conversation["state"] = ConversationState.CLOSED
        conversation["ended_at"] = time.time()
        conversation["end_reason"] = reason
        
        # 通知所有参与者对话结束
        for participant_id in conversation["participants"]:
            if participant_id != self.agent.agent_id:
                message = Message(
                    sender_id=self.agent.agent_id,
                    receiver_id=participant_id,
                    msg_type="dialogue_end",
                    content={
                        "conversation_id": conversation_id,
                        "reason": reason
                    }
                )
                self.agent.router.route_message(message)
        
        self.logger.info(f"Ended dialogue {conversation_id} with reason: {reason}")
    
    def get_conversation_history(self, conversation_id: str) -> Optional[List[Dict[str, Any]]]:
        """获取对话历史"""
        if conversation_id in self.active_conversations:
            return self.active_conversations[conversation_id]["messages"]
        return None
    
    def _handle_dialogue_init(self, message: Message) -> Dict[str, Any]:
        """处理对话初始化消息"""
        conversation_id = message.content.get("conversation_id")
        topic = message.content.get("topic")
        participants = message.content.get("participants", [])
        initial_message = message.content.get("initial_message")
        
        # 记录对话
        self.active_conversations[conversation_id] = {
            "participants": participants,
            "topic": topic,
            "messages": [],
            "initiator": message.sender_id,
            "created_at": time.time(),
            "state": ConversationState.ACTIVE
        }
        
        self.logger.info(f"Joined dialogue {conversation_id} initiated by {message.sender_id}")
        
        # 如果有初始消息，记录它
        if initial_message:
            self.active_conversations[conversation_id]["messages"].append({
                "sender": message.sender_id,
                "content": initial_message,
                "timestamp": time.time()
            })
        
        return {"status": "accepted", "conversation_id": conversation_id}
    
    def _handle_dialogue_message(self, message: Message) -> Dict[str, Any]:
        """处理对话消息"""
        conversation_id = message.content.get("conversation_id")
        content = message.content.get("content")
        sender = message.content.get("sender")
        
        if conversation_id not in self.active_conversations:
            self.logger.warning(f"Received message for unknown conversation {conversation_id}")
            return {"status": "error", "message": "Conversation not found"}
        
        # 记录消息
        self.active_conversations[conversation_id]["messages"].append({
            "sender": sender,
            "content": content,
            "timestamp": time.time()
        })
        
        self.logger.debug(f"Received dialogue message in {conversation_id} from {sender}")
        return {"status": "acknowledged"}
    
    def _handle_dialogue_end(self, message: Message) -> Dict[str, Any]:
        """处理对话结束消息"""
        conversation_id = message.content.get("conversation_id")
        reason = message.content.get("reason")
        
        if conversation_id in self.active_conversations:
            self.active_conversations[conversation_id]["state"] = ConversationState.CLOSED
            self.active_conversations[conversation_id]["ended_at"] = time.time()
            self.active_conversations[conversation_id]["end_reason"] = reason
            self.logger.info(f"Dialogue {conversation_id} ended with reason: {reason}")
        
        return {"status": "acknowledged"}

class ConsensusMechanism:
    """共识机制"""
    
    def __init__(self, agent: BasicAgent):
        self.agent = agent
        self.logger = logging.getLogger(f"consensus_mechanism.{agent.agent_id}")
        self.active_consensus_processes: Dict[str, Dict[str, Any]] = {}
        
        # 注册共识相关消息处理器
        self.agent.register_handler("consensus_proposal", self._handle_consensus_proposal)
        self.agent.register_handler("consensus_vote", self._handle_consensus_vote)
        self.agent.register_handler("consensus_result", self._handle_consensus_result)
    
    def propose_decision(self, participants: List[str], proposal: Any, 
                        method: ConsensusMethod = ConsensusMethod.MAJORITY,
                        timeout: float = 30.0) -> str:
        """
        提出决策提案
        
        Args:
            participants: 参与者列表
            proposal: 提案内容
            method: 共识方法
            timeout: 超时时间（秒）
            
        Returns:
            共识过程ID
        """
        consensus_id = str(uuid.uuid4())
        
        # 创建共识过程记录
        self.active_consensus_processes[consensus_id] = {
            "participants": participants,
            "proposal": proposal,
            "method": method,
            "votes": {self.agent.agent_id: True},  # 自己自动投赞成票
            "initiator": self.agent.agent_id,
            "created_at": time.time(),
            "timeout": timeout,
            "deadline": time.time() + timeout
        }
        
        # 通知所有参与者
        for participant_id in participants:
            if participant_id != self.agent.agent_id:
                message = Message(
                    sender_id=self.agent.agent_id,
                    receiver_id=participant_id,
                    msg_type="consensus_proposal",
                    content={
                        "consensus_id": consensus_id,
                        "proposal": proposal,
                        "method": method.value,
                        "timeout": timeout
                    }
                )
                self.agent.router.route_message(message)
        
        # 启动计时器检查共识结果
        self._schedule_consensus_check(consensus_id)
        
        self.logger.info(f"Proposed decision {consensus_id} to {len(participants)} participants")
        return consensus_id
    
    def vote(self, consensus_id: str, approve: bool) -> None:
        """
        投票
        
        Args:
            consensus_id: 共识过程ID
            approve: 是否赞成
        """
        if consensus_id not in self.active_consensus_processes:
            self.logger.warning(f"Consensus process {consensus_id} not found")
            return
        
        # 记录投票
        self.active_consensus_processes[consensus_id]["votes"][self.agent.agent_id] = approve
        
        # 发送投票消息给发起者
        process = self.active_consensus_processes[consensus_id]
        message = Message(
            sender_id=self.agent.agent_id,
            receiver_id=process["initiator"],
            msg_type="consensus_vote",
            content={
                "consensus_id": consensus_id,
                "vote": approve
            }
        )
        self.agent.router.route_message(message)
    
    def _schedule_consensus_check(self, consensus_id: str) -> None:
        """安排共识检查"""
        # 简化实现，在实际应用中应该使用定时器
        pass
    
    def _check_consensus_result(self, consensus_id: str) -> None:
        """检查共识结果"""
        if consensus_id not in self.active_consensus_processes:
            return
        
        process = self.active_consensus_processes[consensus_id]
        participants = process["participants"]
        votes = process["votes"]
        method = process["method"]
        
        # 检查是否所有参与者都已投票或超时
        all_voted = len(votes) >= len(participants)
        timed_out = time.time() > process["deadline"]
        
        if all_voted or timed_out:
            # 计算结果
            result = self._calculate_consensus_result(votes, method, len(participants))
            
            # 通知所有参与者结果
            for participant_id in participants:
                message = Message(
                    sender_id=self.agent.agent_id,
                    receiver_id=participant_id,
                    msg_type="consensus_result",
                    content={
                        "consensus_id": consensus_id,
                        "result": result,
                        "votes": votes
                    }
                )
                self.agent.router.route_message(message)
            
            # 移除已完成的共识过程
            del self.active_consensus_processes[consensus_id]
            
            self.logger.info(f"Consensus {consensus_id} completed with result: {result}")
    
    def _calculate_consensus_result(self, votes: Dict[str, bool], 
                                  method: ConsensusMethod, 
                                  total_participants: int) -> bool:
        """计算共识结果"""
        if method == ConsensusMethod.UNANIMOUS:
            # 全体一致
            return all(votes.values()) and len(votes) == total_participants
        elif method == ConsensusMethod.WEIGHTED:
            # 加权投票（简化实现，假设权重相等）
            approve_votes = sum(1 for v in votes.values() if v)
            return approve_votes / len(votes) > 0.5
        else:  # MAJORITY
            # 简单多数
            approve_votes = sum(1 for v in votes.values() if v)
            return approve_votes > len(votes) / 2
    
    def _handle_consensus_proposal(self, message: Message) -> Dict[str, Any]:
        """处理共识提案"""
        consensus_id = message.content.get("consensus_id")
        proposal = message.content.get("proposal")
        method = ConsensusMethod(message.content.get("method", "majority"))
        timeout = message.content.get("timeout", 30.0)
        
        # 记录共识过程
        self.active_consensus_processes[consensus_id] = {
            "participants": [],  # 不知道其他参与者
            "proposal": proposal,
            "method": method,
            "votes": {},
            "initiator": message.sender_id,
            "created_at": time.time(),
            "timeout": timeout,
            "deadline": time.time() + timeout
        }
        
        self.logger.info(f"Received consensus proposal {consensus_id} from {message.sender_id}")
        
        # 默认投赞成票（在实际应用中可能需要更复杂的决策逻辑）
        self.vote(consensus_id, True)
        
        return {"status": "acknowledged"}
    
    def _handle_consensus_vote(self, message: Message) -> Dict[str, Any]:
        """处理共识投票"""
        consensus_id = message.content.get("consensus_id")
        vote = message.content.get("vote")
        
        if consensus_id in self.active_consensus_processes:
            self.active_consensus_processes[consensus_id]["votes"][message.sender_id] = vote
            self.logger.debug(f"Recorded vote from {message.sender_id} in consensus {consensus_id}")
            
            # 检查是否达成共识
            self._check_consensus_result(consensus_id)
        
        return {"status": "acknowledged"}
    
    def _handle_consensus_result(self, message: Message) -> Dict[str, Any]:
        """处理共识结果"""
        consensus_id = message.content.get("consensus_id")
        result = message.content.get("result")
        votes = message.content.get("votes")
        
        self.logger.info(f"Consensus {consensus_id} result: {result}")
        
        # 在实际应用中，这里可能需要触发相应的行动
        
        return {"status": "acknowledged"}

class ConflictResolver:
    """冲突解决器"""
    
    def __init__(self, agent: BasicAgent):
        self.agent = agent
        self.logger = logging.getLogger(f"conflict_resolver.{agent.agent_id}")
        
        # 注册冲突相关消息处理器
        self.agent.register_handler("conflict_detected", self._handle_conflict_detected)
        self.agent.register_handler("conflict_resolution", self._handle_conflict_resolution)
    
    def detect_and_resolve_conflict(self, conflict_info: Dict[str, Any], 
                                  strategy: ConflictResolutionStrategy) -> Dict[str, Any]:
        """
        检测并解决冲突
        
        Args:
            conflict_info: 冲突信息
            strategy: 解决策略
            
        Returns:
            解决方案
        """
        conflict_id = conflict_info.get("conflict_id", str(uuid.uuid4()))
        conflicting_agents = conflict_info.get("agents", [])
        
        self.logger.info(f"Detected conflict {conflict_id} among agents: {conflicting_agents}")
        
        resolution = None
        if strategy == ConflictResolutionStrategy.VOTING:
            resolution = self._resolve_by_voting(conflict_info)
        elif strategy == ConflictResolutionStrategy.AUTHORITY:
            resolution = self._resolve_by_authority(conflict_info)
        elif strategy == ConflictResolutionStrategy.CONSISTENCY:
            resolution = self._resolve_by_consistency_negotiation(conflict_info)
        
        # 通知所有冲突方解决方案
        for agent_id in conflicting_agents:
            if agent_id != self.agent.agent_id:
                message = Message(
                    sender_id=self.agent.agent_id,
                    receiver_id=agent_id,
                    msg_type="conflict_resolution",
                    content={
                        "conflict_id": conflict_id,
                        "resolution": resolution,
                        "resolver": self.agent.agent_id
                    }
                )
                self.agent.router.route_message(message)
        
        return resolution
    
    def _resolve_by_voting(self, conflict_info: Dict[str, Any]) -> Dict[str, Any]:
        """通过投票解决冲突"""
        # 简化实现：发起投票共识过程
        consensus = ConsensusMechanism(self.agent)
        participants = conflict_info.get("agents", [])
        proposal = conflict_info.get("proposed_solutions", [{}])[0]  # 简化处理
        
        consensus_id = consensus.propose_decision(
            participants=participants,
            proposal=proposal,
            method=ConsensusMethod.MAJORITY
        )
        
        return {
            "method": "voting",
            "consensus_id": consensus_id,
            "proposal": proposal
        }
    
    def _resolve_by_authority(self, conflict_info: Dict[str, Any]) -> Dict[str, Any]:
        """通过权威解决冲突"""
        # 简化实现：假设有预定义的权威顺序
        authority_order = conflict_info.get("authority_order", [])
        if not authority_order:
            authority_order = sorted(conflict_info.get("agents", []))
        
        authority_agent = authority_order[0] if authority_order else self.agent.agent_id
        
        return {
            "method": "authority",
            "authority_agent": authority_agent,
            "decision": "accept_proposal"  # 简化处理
        }
    
    def _resolve_by_consistency_negotiation(self, conflict_info: Dict[str, Any]) -> Dict[str, Any]:
        """通过一致性协商解决冲突"""
        # 简化实现：返回协商建议
        return {
            "method": "consistency",
            "negotiation_rounds": 3,
            "compromise_solution": conflict_info.get("compromise_proposal", {})
        }
    
    def _handle_conflict_detected(self, message: Message) -> Dict[str, Any]:
        """处理冲突检测消息"""
        conflict_info = message.content.get("conflict_info", {})
        strategy = ConflictResolutionStrategy(message.content.get("strategy", "voting"))
        
        resolution = self.detect_and_resolve_conflict(conflict_info, strategy)
        
        return {
            "status": "resolved",
            "resolution": resolution
        }
    
    def _handle_conflict_resolution(self, message: Message) -> Dict[str, Any]:
        """处理冲突解决消息"""
        conflict_id = message.content.get("conflict_id")
        resolution = message.content.get("resolution")
        
        self.logger.info(f"Received conflict resolution for {conflict_id}: {resolution}")
        
        # 在实际应用中，这里可能需要执行解决方案
        
        return {"status": "acknowledged"}