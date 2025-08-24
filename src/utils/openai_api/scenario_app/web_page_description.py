"""
@Author         : Ailitonia
@Date           : 2025/8/24 11:50:07
@FileName       : web_page_description.py
@Project        : omega-miya
@Description    : 网页内容提取
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import Literal

from lxml import etree
from nonebot.utils import run_sync
from pydantic import BaseModel

from .base import BaseAIScenarioApp

_SYSTEM_INIT_PROMPT: str = """# Profile

你是一位精通网页内容分析的专家，对HTML代码结构有着深刻的理解，能够运用先进的文本处理技术，从复杂的网页代码中提取有价值的信息。你具备HTML解析能力、自然语言处理技术、关键词提取算法以及文本摘要生成能力，能够高效地处理和分析网页内容。

# Goals

对网页的原始HTML或文本内容进行深度解析，使用**简体中文**提取其中的关键信息，包括**关键词**和**内容概况**，帮助用户快速了解网页的核心主题和主要内容。

# Constrains

以JSON格式输出，其中的键值包括：

- keywords: 关键词数组
- web_overview: 内容概述

## 提取与描述要求

- 仅从HTML代码中提取文本内容，忽略无关的HTML标签和脚本代码。
- 对提取的文本内容进行分词处理，提取关键词，根据词频和重要性进行排序。
- 提取关键词的数量没有上限要求，但需要确保提取的关键词具有代表性。
- 内容概况应当准确、保持客观、避免主观评价、情感色彩或主观臆断。
- 内容概述的长度不做限制，为了确保内容完整性，你还可以适当引用原文。
- 如果网页内容主体语言不是简体中文，尝试先翻译为简体中文再进行信息提取。
- 其中关键词能使用中文进行描述的，尽量使用中文。无对应中文翻译的，可保留原语言原文。

# Examples

这里体现一个用户交互示例，**你的回答不应该照抄此示例**。

在**任何情况下**，你都**不应该**直接返回该示例。

你的输入输出示例如下：

## 输入

HTML内容为一篇中国政府关于对新一代人工智能发展规划的政策文件。

## 输出

```json
{
  "keywords": [
    "人工智能",
    "国务院",
    "发展规划",
    "科技创新",
    "智能经济",
    "智能社会",
    "基础理论",
    "关键共性技术",
    "智能基础设施",
    "伦理规范"
  ],
  "web_overview": "本文是国务院印发的《新一代人工智能发展规划》，旨在推动我国人工智能的快速发展，抢占国际竞争的战略制高点。规划强调人工智能对经济、社会和国防的重大影响，提出到2030年使我国人工智能理论、技术与应用达到世界领先水平。规划明确了构建开放协同的科技创新体系、培育高端智能经济、建设安全便捷的智能社会等重点任务，同时提出加强资源配置和保障措施，包括建立财政引导机制、优化创新基地布局、完善法律法规和伦理规范等，以确保人工智能健康有序发展。"
}
```"""


class WebPageDescription(BaseModel):
    keywords: list[str]
    web_overview: str


class WebPageDescriptionApp(BaseAIScenarioApp):
    """网页内容提取应用"""

    @classmethod
    def _set_init_system_message(cls) -> str | None:
        return _SYSTEM_INIT_PROMPT

    @classmethod
    def _set_max_messages(cls) -> int:
        return 3

    @staticmethod
    @run_sync
    def get_html_pure_text(html_content: str) -> str:
        """提取 html 中文本内容"""
        tree = etree.HTML(html_content)

        # 定义要删除的标签
        tags_to_remove = ['script', 'style', 'meta', 'link', 'noscript']

        # 遍历所有节点，删除不需要的标签
        for tag in tags_to_remove:
            for element in tree.xpath(f'//{tag}'):
                element.getparent().remove(element)

        # 移除换行符
        text_list = [
            str(x).replace('\n', '').replace('\r', '').strip()
            for x in tree.xpath('//text()')
        ]

        return ' '.join(text.strip() for text in text_list if text.strip())

    async def describe_web_page(
            self,
            page_url: str,
            *,
            response_format: Literal['json_schema', 'json_object', None] = 'json_schema',
            temperature: float = 0.5,
    ) -> WebPageDescription:
        """获取网页内容总结"""

        # 获取和初步清理网页 html
        page_content = await self.chat_session.client.get_any_resource_as_bytes(url=page_url)
        page_pure_text = await self.get_html_pure_text(html_content=page_content)

        return await self.chat_session.advance_chat(
            page_pure_text,
            response_format=response_format,
            model_type=WebPageDescription,
            temperature=temperature,
        )


__all__ = [
    'WebPageDescription',
    'WebPageDescriptionApp',
]
