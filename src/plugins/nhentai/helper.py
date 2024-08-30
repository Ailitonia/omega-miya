"""
@Author         : Ailitonia
@Date           : 2024/6/8 下午11:10
@FileName       : helper
@Project        : nonebot2_miya
@Description    : Nhentai helper
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import TYPE_CHECKING, Literal

from nonebot.rule import ArgumentParser, Namespace
from pydantic import BaseModel, ConfigDict

from src.service import OmegaMessage, OmegaMessageSegment

if TYPE_CHECKING:
    from src.utils.nhentai import NhentaiGallery


def get_searching_argument_parser() -> ArgumentParser:
    """搜索命令的 shell command argument parser"""
    parser = ArgumentParser(prog='搜索命令参数解析', description='Parse searching arguments')
    parser.add_argument('-p', '--page', type=int, default=1)
    parser.add_argument('-s', '--sort', type=str, default='recent', choices=['recent', 'popular-today', 'popular-week', 'popular'])
    parser.add_argument('keyword', nargs='+')
    return parser


class SearchingArguments(BaseModel):
    """搜索命令 argument parser 的解析结果 Model"""
    page: int
    sort: Literal['recent', 'popular-today', 'popular-week', 'popular']
    keyword: list[str]

    model_config = ConfigDict(extra='ignore', from_attributes=True)


def parse_from_searching_parser(args: Namespace) -> SearchingArguments:
    """解析搜索命令参数"""
    return SearchingArguments.model_validate(args)


async def format_gallery_desc_msg(gallery: "NhentaiGallery") -> OmegaMessage:
    """获取格式化作品描述文本"""
    gallery_data = await gallery.query_gallery()
    folder_name = f'gallery_{gallery_data.id}'

    cover_image = await gallery.download_resource(url=gallery_data.cover_image, folder_name=folder_name)

    tags: dict[str, set[str]] = {}
    for tag in gallery_data.tags:
        if tag.type not in tags:
            tags[tag.type] = {tag.name}
        else:
            tags[tag.type].add(tag.name)

    tag_text = '\n'.join(
        f'{tag_type.title()}: {" ".join("#" + tag_name for tag_name in tag_names)}'
        for tag_type, tag_names in tags.items()
    )
    title_text = f'{gallery_data.title.english}\n{gallery_data.title.japanese}'
    desc_text = f'{title_text}\n\nGID:{gallery_data.id}\nMID:{gallery_data.media_id}\n\n{tag_text}'

    return OmegaMessageSegment.image(cover_image.path) + OmegaMessageSegment.text(desc_text)


__all__ = [
    'get_searching_argument_parser',
    'parse_from_searching_parser',
    'format_gallery_desc_msg',
]
