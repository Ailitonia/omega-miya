"""
@Author         : Ailitonia
@Date           : 2023/7/16 22:00
@FileName       : data_source.py
@Project        : nonebot2_miya
@Description    : nbnhhsh api
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from collections.abc import Sequence
from typing import TYPE_CHECKING

from nonebot.log import logger
from pydantic import BaseModel

from src.compat import parse_obj_as
from src.utils import OmegaRequests
from src.utils.openai_api.scenario_app import ImageDescriptionApp, KnowledgeExtractorApp, WebPageDescriptionApp
from .config import nbnhhsh_plugin_config

if TYPE_CHECKING:
    from src.utils.openai_api.scenario_app.knowledge_extractor import InputKeywords


class AttrGuessResult(BaseModel):
    name: str
    trans: list[str] | None = None
    inputting: list[str] | None = None

    @property
    def guess_result(self) -> list[str]:
        result = []
        if self.trans is not None:
            result.extend(self.trans)
        if self.inputting is not None:
            result.extend(self.inputting)
        result = list(set(result))
        result.sort()
        return result


async def _query_attr_guess(guess: str) -> list[AttrGuessResult]:
    """从 magiconch API 处获取缩写查询结果"""
    # 该 api 当前不支持查询的缩写中有空格 这里去除待查询文本中的空格
    guess = guess.replace(' ', '').strip()
    url = 'https://lab.magiconch.com/api/nbnhhsh/guess'
    payload = {'text': guess}
    response = await OmegaRequests().post(url=url, json=payload)
    return parse_obj_as(list[AttrGuessResult], OmegaRequests.parse_content_as_json(response=response))


async def query_abbr_guess(guess: str) -> list[str]:
    guess_result = await _query_attr_guess(guess=guess)
    return [trans_word for x in guess_result for trans_word in x.guess_result]


async def simple_guess(query_message: str) -> str:
    """查询缩写"""
    guess_result = await query_abbr_guess(guess=query_message)
    if guess_result:
        trans = '\n'.join(guess_result)
        trans = f'为你找到了{query_message!r}的以下解释:\n\n{trans}'
    else:
        trans = f'没有找到{query_message!r}的解释'
    return trans


async def ai_guess(query_message: str, msg_images: Sequence[str]) -> str:
    """使用 AI 进行解释"""

    # 只有文本内容为纯字母的时候才尝试查询缩写
    need_query_attr = query_message.isalpha() and query_message.isascii()
    input_keywords: list[InputKeywords] = []

    try:
        if msg_images:
            images_desc = await ImageDescriptionApp(
                service_name=nbnhhsh_plugin_config.nbnhhsh_plugin_ai_vision_service_name,
                model_name=nbnhhsh_plugin_config.nbnhhsh_plugin_ai_vision_model_name,
            ).describe_image(
                image_urls=msg_images,
                response_format=nbnhhsh_plugin_config.nbnhhsh_plugin_ai_vision_json_output,
                temperature=nbnhhsh_plugin_config.nbnhhsh_plugin_ai_temperature,
            )
            need_query_attr = False
            input_keywords.extend(
                {
                    'type': f'image_keywords_{x.type}',
                    'content': x.content,
                }
                for x in images_desc.entity
            )
            image_overview = images_desc.image_overview
        else:
            image_overview = ''
    except Exception as e:
        logger.warning(f'nbnhhsh | 尝试解析图片({msg_images})失败, {e}')
        image_overview = ''

    try:
        if urls := OmegaRequests.get_url_in_text(text=query_message):
            web_desc = await WebPageDescriptionApp(
                service_name=nbnhhsh_plugin_config.nbnhhsh_plugin_ai_description_service_name,
                model_name=nbnhhsh_plugin_config.nbnhhsh_plugin_ai_description_model_name,
            ).describe_web_page(
                page_url=urls[0],
                response_format=nbnhhsh_plugin_config.nbnhhsh_plugin_ai_description_json_output,
                temperature=nbnhhsh_plugin_config.nbnhhsh_plugin_ai_temperature,
            )
            need_query_attr = False
            input_keywords.append({
                'type': 'web_page_keywords',
                'content': web_desc.keywords,
            })
            web_overview = web_desc.web_overview
        else:
            web_overview = ''
    except Exception as e:
        logger.warning(f'nbnhhsh | 尝试解析链接({query_message})失败, {e}')
        web_overview = ''

    try:
        if need_query_attr and (attr_desc_result := await query_abbr_guess(guess=query_message)):
            input_keywords.append({
                'type': 'abbreviation_explanation',
                'content': attr_desc_result
            })
            abbr_overview = f'查询缩写{query_message!r}可能的含义:\n\n{"\n".join(attr_desc_result)}'
        else:
            abbr_overview = ''
    except Exception as e:
        logger.warning(f'nbnhhsh | 查询{query_message!r}缩写失败, {e}')
        abbr_overview = ''

    knowledge_extract_result = await KnowledgeExtractorApp(
        service_name=nbnhhsh_plugin_config.nbnhhsh_plugin_ai_description_service_name,
        model_name=nbnhhsh_plugin_config.nbnhhsh_plugin_ai_description_model_name,
    ).extract_knowledge(
        user_message=query_message,
        input_keywords=input_keywords,
        response_format=nbnhhsh_plugin_config.nbnhhsh_plugin_ai_description_json_output,
        temperature=nbnhhsh_plugin_config.nbnhhsh_plugin_ai_temperature,
        max_tokens=nbnhhsh_plugin_config.nbnhhsh_plugin_ai_max_tokens,
    )

    pre_message = f'{abbr_overview}\n\n{image_overview}\n\n{web_overview}'

    if knowledge_extract_result.result:
        desc_text = '\n\n'.join(f'{x.object}: {x.description}' for x in knowledge_extract_result.result)
    else:
        desc_text = '没有识别到相关需要解释的实体或概念'

    return f'{pre_message.strip()}\n\n{desc_text.strip()}'.strip()


__all__ = [
    'simple_guess',
    'ai_guess',
]
