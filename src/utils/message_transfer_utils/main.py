"""
@Author         : Ailitonia
@Date           : 2024/10/9 14:59:09
@FileName       : main.py
@Project        : omega-miya
@Description    : 消息转储工具
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import TYPE_CHECKING

from src.service import OmegaMessage, OmegaMessageSegment
from src.utils import OmegaRequests
from .consts import save_path

if TYPE_CHECKING:
    from nonebot.internal.adapter import Message as BaseMessage
    from src.resource import TemporaryResource
    from src.service import OmegaMatcherInterface


class MessageTransferUtils[TM: "BaseMessage"]:
    """消息转储工具"""

    def __init__(self, interface: "OmegaMatcherInterface", origin_message: TM):
        self._adapter_name = interface.bot.adapter.get_name()
        self._origin_message = origin_message
        self.parsed_message: "OmegaMessage" = interface.get_message_extractor()(message=origin_message).message

    def _generate_resource_file(self, seg_type: str, url: str) -> "TemporaryResource":
        """生成缓存文件路径"""
        target_folder = save_path.get_target_folder(adapter_name=self._adapter_name, seg_type=seg_type)
        file_name = OmegaRequests.hash_url_file_name(url=url)
        return target_folder(file_name)

    async def _download_resource_file(self, seg_type: str, url: str) -> "TemporaryResource":
        """下载缓存文件"""
        target_file = self._generate_resource_file(seg_type=seg_type, url=url)
        return await OmegaRequests().download(url=url, file=target_file)

    async def dump_segment_resource(self, message_segment: "OmegaMessageSegment") -> "OmegaMessageSegment":
        match message_segment.type:
            case 'image':
                if str(image_url := message_segment.data.get('url', '')).startswith(('http://', 'https://')):
                    target_file = await self._download_resource_file(seg_type=message_segment.type, url=image_url)
                    message_segment = OmegaMessageSegment.image(url=target_file.path)
            case _:
                pass

        return message_segment

    async def dumps(self) -> "OmegaMessage":
        new_message = OmegaMessage()

        for message_segment in self.parsed_message:
            new_message.append(await self.dump_segment_resource(message_segment=message_segment))

        return new_message


__all__ = [
    'MessageTransferUtils',
]
