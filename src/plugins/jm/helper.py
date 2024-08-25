"""
@Author         : Ailitonia
@Date           : 2024/6/26 上午3:27
@FileName       : helper
@Project        : nonebot2_miya
@Description    : jm helper
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Literal, Optional

from nonebot.rule import ArgumentParser, Namespace
from pydantic import BaseModel, ConfigDict
from zhconv import convert as zh_convert

from src.service import OmegaMessage, OmegaMessageSegment
from src.utils.comic18 import Comic18


def get_searching_argument_parser() -> ArgumentParser:
    """搜索命令的 shell command argument parser"""
    parser = ArgumentParser(prog='搜索命令参数解析', description='Parse searching arguments')
    parser.add_argument('-p', '--page', type=int, default=None)
    parser.add_argument('-c', '--type', type=str, default=None, choices=['another', 'doujin', 'hanman', 'meiman', 'short', 'single'])
    parser.add_argument('-t', '--time', type=str, default=None, choices=['a', 't', 'w', 'm'])
    parser.add_argument('-o', '--order', type=str, default=None, choices=['mr', 'mv', 'mp', 'md', 'tr', 'tf'])
    parser.add_argument('-a', '--tag', type=str, default=None, choices=['0', '1', '2', '3', '4'])
    parser.add_argument('keyword', nargs='+')
    return parser


class SearchingArguments(BaseModel):
    """搜索命令 argument parser 的解析结果 Model"""
    page: Optional[int]
    type: Optional[Literal['another', 'doujin', 'hanman', 'meiman', 'short', 'single']]
    time: Optional[Literal['a', 't', 'w', 'm']]
    order: Optional[Literal['mr', 'mv', 'mp', 'md', 'tr', 'tf']]
    tag: Optional[Literal['0', '1', '2', '3', '4']]
    keyword: list[str]

    model_config = ConfigDict(extra='ignore', from_attributes=True)


def parse_from_searching_parser(args: Namespace) -> SearchingArguments:
    """解析搜索命令参数"""
    return SearchingArguments.model_validate(args)


async def format_album_desc_msg(album: Comic18) -> OmegaMessage:
    """获取格式化作品描述文本"""
    album_data = await album.query_album()

    cover_image = await album.download_resource(url=album_data.cover_image_url, folder_name=f'album_{album.aid}')

    title_text = f'JM{album_data.aid}\n{album_data.title}\n作者: {album_data.artist}'
    artwork_text = '作品: ' + (', '.join(f'#{x}' for x in album_data.artwork_tag) or '无数据')
    characters_text = '登场人物: ' + (', '.join(f'#{x}' for x in album_data.characters) or '无数据')
    tag_text = '标签: ' + (', '.join(f'#{x}' for x in album_data.tags) or '无数据')

    desc_text = f'{artwork_text}\n{characters_text}\n{tag_text}\n\n{album_data.description}'
    desc_text = zh_convert(desc_text, 'zh-cn')
    send_text = f'{title_text}\n\n{desc_text}'

    return OmegaMessageSegment.image(cover_image.path) + OmegaMessageSegment.text(send_text)


__all__ = [
    'get_searching_argument_parser',
    'parse_from_searching_parser',
    'format_album_desc_msg',
]
