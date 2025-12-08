from typing import Callable, Dict, List, Set, Any, Optional
import threading
import queue
import time
from .message import Message

class PubSubError(Exception):
    """发布/订阅系统错误"""
    pass

class MessageQueue:
    """线程安全的消息队列"""
    
    def __init__(self, maxsize: int = 0):
        self._queue = queue.Queue(maxsize)
        self._lock = threading.Lock()
    
    def put(self, item: Any, block: bool = True, timeout: Optional[float] = None) -> None:
        """放入消息"""
        self._queue.put(item, block, timeout)
    
    def get(self, block: bool = True, timeout: Optional[float] = None) -> Any:
        """获取消息"""
        return self._queue.get(block, timeout)
    
    def empty(self) -> bool:
        """检查队列是否为空"""
        return self._queue.empty()
    
    def qsize(self) -> int:
        """获取队列大小"""
        return self._queue.qsize()

class PubSubBus:
    """发布/订阅消息总线实现"""
    
    def __init__(self):
        self._subscribers: Dict[str, List[Callable[[Message], None]]] = {}
        self._broadcast_subscribers: List[Callable[[Message], None]] = []
        self._topic_lock = threading.Lock()
        self._subscriber_lock = threading.Lock()
        self._message_queue = MessageQueue()
        self._running = False
        self._worker_thread = None
        self._stop_event = threading.Event()
    
    def start(self) -> None:
        """启动消息处理线程"""
        if self._running:
            return
        
        self._running = True
        self._stop_event.clear()
        self._worker_thread = threading.Thread(target=self._message_worker, daemon=True)
        self._worker_thread.start()
    
    def stop(self) -> None:
        """停止消息处理线程"""
        if not self._running:
            return
        
        self._stop_event.set()
        self._running = False
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=2.0)
    
    def _message_worker(self) -> None:
        """后台处理消息的worker"""
        while not self._stop_event.is_set():
            try:
                # 从队列获取消息，设置超时以便定期检查停止信号
                topic, message = self._message_queue.get(timeout=0.5)
                
                # 处理消息
                self._dispatch_message(topic, message)
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Error in message worker: {e}")
    
    def _dispatch_message(self, topic: str, message: Message) -> None:
        """分发消息给订阅者"""
        # 1. 发送给特定主题的订阅者
        with self._subscriber_lock:
            subscribers = self._subscribers.get(topic, [])[:]
        
        for subscriber in subscribers:
            try:
                subscriber(message)
            except Exception as e:
                print(f"Error delivering message to subscriber: {e}")
        
        # 2. 处理广播消息
        if topic == "broadcast" or message.receiver_id == "broadcast":
            with self._subscriber_lock:
                broadcast_subscribers = self._broadcast_subscribers[:]
            
            for subscriber in broadcast_subscribers:
                try:
                    subscriber(message)
                except Exception as e:
                    print(f"Error delivering broadcast message: {e}")
    
    def subscribe(self, topic: str, callback: Callable[[Message], None]) -> None:
        """订阅特定主题"""
        if not callable(callback):
            raise ValueError("Callback must be callable")
        
        with self._topic_lock:
            if topic not in self._subscribers:
                self._subscribers[topic] = []
            
            # 避免重复订阅
            if callback not in self._subscribers[topic]:
                self._subscribers[topic].append(callback)
    
    def unsubscribe(self, topic: str, callback: Callable[[Message], None]) -> None:
        """取消订阅特定主题"""
        with self._topic_lock:
            if topic in self._subscribers and callback in self._subscribers[topic]:
                self._subscribers[topic].remove(callback)
    
    def subscribe_broadcast(self, callback: Callable[[Message], None]) -> None:
        """订阅广播消息"""
        if not callable(callback):
            raise ValueError("Callback must be callable")
        
        with self._subscriber_lock:
            if callback not in self._broadcast_subscribers:
                self._broadcast_subscribers.append(callback)
    
    def unsubscribe_broadcast(self, callback: Callable[[Message], None]) -> None:
        """取消订阅广播消息"""
        with self._subscriber_lock:
            if callback in self._broadcast_subscribers:
                self._broadcast_subscribers.remove(callback)
    
    def publish(self, topic: str, message: Message) -> None:
        """发布消息到指定主题"""
        if not isinstance(message, Message):
            raise ValueError("Message must be an instance of Message class")
        
        if not message.validate():
            raise ValueError("Message validation failed")
        
        # 将消息放入队列，由worker线程处理
        try:
            self._message_queue.put((topic, message), block=False)
        except queue.Full:
            raise PubSubError("Message queue is full, unable to publish message")
    
    def get_subscriber_count(self, topic: str) -> int:
        """获取特定主题的订阅者数量"""
        with self._topic_lock:
            return len(self._subscribers.get(topic, []))
    
    def get_broadcast_subscriber_count(self) -> int:
        """获取广播订阅者数量"""
        with self._subscriber_lock:
            return len(self._broadcast_subscribers)
    
    def __del__(self):
        """析构函数，确保资源清理"""
        self.stop()