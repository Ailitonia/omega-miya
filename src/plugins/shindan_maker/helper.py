"""
@Author         : Ailitonia
@Date           : 2024/4/25 上午12:04
@FileName       : helper
@Project        : nonebot2_miya
@Description    : shindan maker parse tools
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

import re

from lxml import etree
from nonebot.utils import run_sync

from src.compat import parse_obj_as

from .model import ShindanMakerResult, ShindanMakerSearchResult


@run_sync
def parse_searching_result_page(content: str) -> list[ShindanMakerSearchResult]:
    """解析 shindan 搜索结果页面"""
    html = etree.HTML(content)

    # 定位搜索结果列表
    shindan_index_group = html.xpath('/html/body//div[@class="index" and @id="shindan-index"]')
    if not shindan_index_group:
        return []

    shindan_index = shindan_index_group.pop(0)
    shindan_links = shindan_index.xpath('.//a[contains(@class, "shindanLink")]')

    result = []
    for link in shindan_links:
        try:
            link_url = link.attrib.get('href')
            link_id = re.search(r'/(\d+?)$', link_url).group(1)
            link_name = link.xpath('.//h2/span').pop(-1).text
            result.append({'id': link_id, 'name': link_name, 'url': link_url})
        except (KeyError, AttributeError):
            continue
    return parse_obj_as(list[ShindanMakerSearchResult], result)


@run_sync
def parse_shindan_page_title(content: str) -> str:
    """解析 shindan 占卜页面获取占卜名称和 id"""
    html = etree.HTML(content)

    title_element = html.xpath('/html/body//h1[@id="shindanTitle"]').pop(0)
    title = title_element.attrib.get('data-shindan_title')
    title_href = title_element.xpath('./a[contains(@class, "shindanTitleLink")]').pop(0).text

    return title or title_href


@run_sync
def parse_shindan_page_token(content: str) -> dict:
    """解析 shindan 占卜页面 token 并生成具体的请求参数"""
    html = etree.HTML(content)

    input_form = html.xpath('/html/body//div[@id="shindanFormMain"]/form[@id="shindanForm" and @method="POST"]').pop(0)

    _token = input_form.xpath('.//input[@type="hidden" and @name="_token"]').pop(0).attrib.get('value')
    shindan_name = input_form.xpath('.//input[@id="shindanInput" and @name="shindanName"]').pop(0).attrib.get('value')
    hidden_name = input_form.xpath('.//input[@type="hidden" and @name="hiddenName"]').pop(0).attrib.get('value')
    type_ = input_form.xpath('.//input[@type="hidden" and @name="type"]').pop(0).attrib.get('value')
    shindan_token = input_form.xpath(
        './/input[@type="hidden" and @id="shindan_token" and @name="shindan_token"]').pop(0).attrib.get('value')

    return {
        '_token': _token,
        'shindanName': shindan_name,
        'hiddenName': hidden_name,
        'type': type_,
        'shindan_token': shindan_token
    }


@run_sync
def parse_shindan_result_page(content: str) -> ShindanMakerResult:
    """解析 shindan 占卜结果页面"""
    content = re.sub(re.compile(r'<br\s?/?>', re.IGNORECASE), '\n', content)
    html = etree.HTML(content)

    shindan_result = html.xpath('/html/body//span[@id="shindanResult"]').pop(0)
    result_image = [x.attrib.get('src') for x in shindan_result.xpath('.//img') if x.attrib.get('src') is not None]

    result_text = ''.join(text for text in shindan_result.itertext()).strip()
    return ShindanMakerResult(text=result_text, image_url=result_image)


__all__ = [
    'parse_searching_result_page',
    'parse_shindan_page_title',
    'parse_shindan_page_token',
    'parse_shindan_result_page'
]
