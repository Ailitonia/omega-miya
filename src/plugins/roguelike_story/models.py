"""
@Author         : Ailitonia
@Date           : 2025/2/16 20:33
@FileName       : models
@Project        : omega-miya
@Description    : AI 交互返回模型
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from pydantic import BaseModel, ConfigDict


class BaseRoguelikeStoryEventModel(BaseModel):
    """肉鸽故事事件基类"""

    model_config = ConfigDict(extra='ignore', coerce_numbers_to_str=True, frozen=True)


class Character(BaseRoguelikeStoryEventModel):
    """故事人物角色"""
    name: str
    type: str
    gender: str
    age: str
    description: str

    @property
    def overview(self) -> str:
        """抽取并格式化人物描述"""
        return f'{self.name}，{self.type}，{self.gender}，{self.age}岁。{self.description}'


class Story(BaseRoguelikeStoryEventModel):
    """构建出的故事框架及背景"""
    background: str
    characters: list[Character]
    story_summary: str
    prologue: str

    @property
    def characters_overview(self) -> str:
        """抽取并格式化人物描述"""
        return '\n\n'.join(x.overview for x in self.characters)

    @property
    def overview(self) -> str:
        """格式化故事概述供提示词使用"""
        return (
            '# Background\n\n'
            '以下是游戏的世界观、主要人物及故事背景，请在编写事件时予以参考：\n\n'
            f'## 世界观\n\n{self.background}\n\n'
            f'## 主要人物\n\n{"\n\n".join(x.overview for x in self.characters)}\n\n'
            f'## 故事背景\n\n{self.story_summary}'
        )


class CurrentSituation(BaseRoguelikeStoryEventModel):
    """当前故事发展情况"""
    current_situation: str
    player_action: str
    roll_result: str


class FastCurrentSituation(BaseRoguelikeStoryEventModel):
    """快速故事续写结果"""
    background: str
    current_situation: str


class NextSituation(BaseRoguelikeStoryEventModel):
    """故事发展后续"""
    next_situation: str
    player_options: str


class RollCondition(BaseRoguelikeStoryEventModel):
    """掷骰子的事件描述"""
    current_situation: str
    action: str


class RollResults(BaseModel):
    """掷骰事件描述"""
    characteristics: str
    success: str
    failure: str
    completed_success: str
    critical_failure: str


__all__ = [
    'Character',
    'Story',
    'CurrentSituation',
    'FastCurrentSituation',
    'NextSituation',
    'RollCondition',
    'RollResults',
]
