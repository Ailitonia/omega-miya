"""
@Author         : Ailitonia
@Date           : 2023/2/3 23:49
@FileName       : helper
@Project        : nonebot2_miya
@Description    : Weibo 工具函数
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from lxml import etree

from src.compat import parse_json_as
from .model import WeiboCardStatus


def parse_weibo_card_from_status_page(content: str) -> WeiboCardStatus:
    """用微博页面解析微博 Json 数据"""
    html = etree.HTML(content)
    render_data = html.xpath('/html/body/script[2]').pop(0)

    start_mark = 'var $render_data = [{'
    start_index = render_data.text.find(start_mark) + len(start_mark) - 1
    end_mark = '][0] || {};'
    end_index = render_data.text.find(end_mark)
    return parse_json_as(WeiboCardStatus, render_data.text[start_index:end_index])


__all__ = [
    'parse_weibo_card_from_status_page',
]
