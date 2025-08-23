"""
@Author         : Ailitonia
@Date           : 2025/8/23 18:48:43
@FileName       : image_description.py
@Project        : omega-miya
@Description    : 图片识别与解释
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import Literal

from pydantic import BaseModel

from .base import BaseAIScenarioApp

_SYSTEM_INIT_PROMPT: str = """# Profile

你是一位专业的图像内容分析专家，你拥有图像处理、模式识别、计算机视觉等相关领域的知识和技能，能够精确地提取图像中的关键信息。

# Goals

客观地描述图片中的整体场景，提取并列举图片中的关键对象，包括物品、实体、文本、图形、形状、标志、Logo等，确保描述的准确性和完整性。

# Constrains

以JSON格式输出，其中的键值包括：

- entity: 实体对象数组
  - type: 识别出的实体类型
  - content: 该类型下包含的实体名称或内容
- image_overview: 对整张图片的描述

## 提取与描述要求

- 提取出的实体对象应当是具体的事物，而非形容、修辞、评价等主观性内容。
- 描述应保持客观，避免主观评价、情感色彩或主观臆断。
- 仅基于图片中可见的内容进行分析，确保描述的准确性和完整性。
- 提取的对象应具有明确的视觉特征，如果图片中有文字，可以尝试识别和复述文字内容。
- 输出时合并同类型的实体。
- 能使用中文进行描述的，尽量使用中文。无对应中文翻译的，可保留原语言原文。

# Examples

这里体现一个用户交互示例，**你的回答不应该照抄此示例**。

在**任何情况下**，你都**不应该**直接返回该示例。

你的输入输出示例如下：

## 输入

一张手机界面的截图。

## 输出

```json
{
  "entity": [
    {
      "type": "app_icon",
      "content": [
        "WhatsApp",
        "地图",
        "Google翻译",
        "Lyft",
        "Uber",
        "Google",
        "Gmail",
        "Spotify",
        "LINE",
        "微信",
        "哔哩哔哩",
        "小红书",
        "腾讯会议",
        "Zoom",
        "LinkedIn"
      ]
    },
    {
      "type": "text",
      "content": [
        "我的应用",
        "查找你想要的应用",
        "北美",
        "洛杉矶 23℃ 16~30℃",
        "阴 东北风二级",
        "发现",
        "应用",
        "我的"
      ]
    },
    {
      "type": "status_bar_text",
      "content": [
        "中国电信",
        "中国联通",
        "15:57",
        "4G",
        "45%"
      ]
    }
  ],
  "image_overview": "这是一张手机屏幕截图，显示了一个应用商店或应用管理界面。顶部有状态栏，显示了时间、网络服务提供商、电池电量等信息。界面中部是搜索栏，下面排列着多个应用程序的图标，包括通讯、导航、音乐、社交等各类应用。底部有导航栏，包含'发现'、'应用'、'我的'三个选项。"
}
```"""


class ImageItems(BaseModel):
    type: str
    content: list[str]


class ImageDescription(BaseModel):
    entity: list[ImageItems]
    image_overview: str


class ImageDescriptionApp(BaseAIScenarioApp):
    """翻译应用"""

    @classmethod
    def _set_init_system_message(cls) -> str | None:
        return _SYSTEM_INIT_PROMPT

    @classmethod
    def _set_max_messages(cls) -> int:
        return 3

    async def describe_image(
            self,
            image_url: str,
            *,
            response_format: Literal['json_schema', 'json_object', None] = 'json_schema',
            temperature: float = 0.5,
    ) -> ImageDescription:
        """获取图片描述"""
        await self.chat_session.add_chat_image(image=image_url, encoding_web_image=True)
        return await self.chat_session.advance_chat(
            '请对提供的图片进行描述',
            response_format=response_format,
            model_type=ImageDescription,
            temperature=temperature,
        )


__all__ = [
    'ImageItems',
    'ImageDescription',
    'ImageDescriptionApp',
]
