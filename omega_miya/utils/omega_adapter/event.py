"""
@Author         : Ailitonia
@Date           : 2021/10/06 21:50
@FileName       : event.py
@Project        : nonebot2_miya 
@Description    : omega 自定义事件
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing_extensions import Literal

from pydantic import BaseModel
from typing import Optional

from nonebot.typing import overrides
from nonebot.utils import escape_tag
from nonebot.adapters import Event as BaseEvent


class Event(BaseEvent):
    """
    Omega 自定义事件
    """
    __event__ = "omega"
    time: int
    self_id: int
    post_type: str

    @overrides(BaseEvent)
    def get_type(self) -> str:
        return self.post_type

    @overrides(BaseEvent)
    def get_event_name(self) -> str:
        return self.post_type

    @overrides(BaseEvent)
    def get_event_description(self) -> str:
        return escape_tag(str(self.dict()))

    @overrides(BaseEvent)
    def get_message(self) -> str:
        raise ValueError("Event has no message!")

    @overrides(BaseEvent)
    def get_plaintext(self) -> str:
        raise ValueError("Event has no message!")

    @overrides(BaseEvent)
    def get_user_id(self) -> str:
        raise ValueError("Event has no user!")

    @overrides(BaseEvent)
    def get_session_id(self) -> str:
        raise ValueError("Event has no session!")

    @overrides(BaseEvent)
    def is_tome(self) -> bool:
        return False


# Models
class Task(BaseModel):
    task_id: int
    task_name: str
    task_type: str
    task_priority: int
    publish_user: int
    description: Optional[str] = None

    class Config:
        extra = "allow"


class Executor(BaseModel):
    user_id: int
    task: Task

    class Config:
        extra = "allow"


# Task Events
class TaskEvent(Event):
    """任务事件"""
    __event__ = "omega.task"
    post_type: Literal["task"]
    task_event_type: str
    task: Task

    @overrides(Event)
    def get_event_name(self) -> str:
        sub_type = getattr(self, "sub_type", None)
        return f"{self.post_type}" + (f".{sub_type}" if sub_type else "")

    def get_task(self) -> Task:
        return self.task

    def get_task_id(self) -> int:
        return self.task.task_id

    def get_task_name(self) -> str:
        return self.task.task_name

    def get_task_type(self) -> str:
        return self.task.task_type

    def get_task_publisher(self) -> int:
        return self.task.publish_user


class TaskPublishEvent(TaskEvent):
    """任务发布事件"""
    __event__ = "omega.task.publish"
    task_event_type: Literal["publish"]

    @overrides(Event)
    def get_event_description(self) -> str:
        return f'Task {self.get_task_id()}/{self.get_task_name()} published from {self.get_task_publisher()}'


class TaskReceiveEvent(TaskEvent):
    """任务接受事件"""
    __event__ = "omega.task.receive"
    task_event_type: Literal["receive"]
    executor: Executor

    def get_executor(self) -> Executor:
        return self.executor

    @overrides(Event)
    def get_event_description(self) -> str:
        return f'Task {self.get_task_id()}/{self.get_task_name()} received by {self.executor.user_id}'


class TaskStartEvent(TaskEvent):
    """任务开始事件"""
    __event__ = "omega.task.start"
    task_event_type: Literal["start"]
    executor: Executor

    def get_executor(self) -> Executor:
        return self.executor

    @overrides(Event)
    def get_event_description(self) -> str:
        return f'Task {self.get_task_id()}/{self.get_task_name()} started by {self.executor.user_id}'


class TaskPauseEvent(TaskEvent):
    """任务暂停事件"""
    __event__ = "omega.task.pause"
    task_event_type: Literal["pause"]
    executor: Executor

    def get_executor(self) -> Executor:
        return self.executor

    @overrides(Event)
    def get_event_description(self) -> str:
        return f'Task {self.get_task_id()}/{self.get_task_name()} paused by {self.executor.user_id}'


class TaskHaltEvent(TaskEvent):
    """任务中止事件"""
    __event__ = "omega.task.halt"
    task_event_type: Literal["halt"]
    reason: str
    executor: Executor

    def get_executor(self) -> Executor:
        return self.executor

    @overrides(Event)
    def get_event_description(self) -> str:
        return f'Task {self.get_task_id()}/{self.get_task_name()} halted with {self.reason}'


class TaskAccomplishEvent(TaskEvent):
    """任务完成事件"""
    __event__ = "omega.task.accomplish"
    task_event_type: Literal["accomplish"]
    executor: Executor

    def get_executor(self) -> Executor:
        return self.executor

    @overrides(Event)
    def get_event_description(self) -> str:
        return f'Task {self.get_task_id()}/{self.get_task_name()} accomplished by {self.executor.user_id}'


__all__ = [
    'Event', 'TaskEvent', 'TaskPublishEvent', 'TaskReceiveEvent', 'TaskAccomplishEvent'
]
