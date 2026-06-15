"""
分布式流水线阶段模块
每个阶段可以独立运行、水平扩展
"""

from .state_manager import StateManager, EventDriver, StageState, StageStatus
from .task_queue import TaskQueue
