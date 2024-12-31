"""
@Author         : Ailitonia
@Date           : 2024/11/17 18:11
@FileName       : transfer
@Project        : omega-miya
@Description    : 消息转储工具
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.resource import TemporaryResource
from src.utils import OmegaRequests
from .message import Message as OmegaMessage
from .message import MessageSegment as OmegaMessageSegment

if TYPE_CHECKING:
    from nonebot.internal.adapter import Message as BaseMessage

    from src.resource import TemporaryResource
    from src.service import OmegaMatcherInterface


@dataclass
class MessageTransferPath:
    """消息转储缓存配置"""

    # 缓存文件夹
    default_save_folder: TemporaryResource = TemporaryResource('message_transfer_utils')

    def get_target_folder(self, adapter_name: str, seg_type: str) -> TemporaryResource:
        return self.default_save_folder(adapter_name, seg_type)


_SAVE_PATH = MessageTransferPath()
"""媒体文件缓存路径"""


class MessageTransferUtils[TM: 'BaseMessage']:
    """消息转储工具"""

    def __init__(self, interface: 'OmegaMatcherInterface', origin_message: TM):
        self._adapter_name = interface.bot.adapter.get_name()
        self._origin_message = origin_message
        self.parsed_message: OmegaMessage = interface.get_message_extractor()(message=origin_message).message

    def _generate_resource_file(self, seg_type: str, url: str) -> 'TemporaryResource':
        """生成缓存文件路径"""
        target_folder = _SAVE_PATH.get_target_folder(adapter_name=self._adapter_name, seg_type=seg_type)
        file_name = OmegaRequests.hash_url_file_name(url=url)
        return target_folder(file_name)

    async def _download_resource_file(self, seg_type: str, url: str) -> 'TemporaryResource':
        """下载缓存文件"""
        target_file = self._generate_resource_file(seg_type=seg_type, url=url)
        return await OmegaRequests().download(url=url, file=target_file)

    async def dump_segment_resource(self, message_segment: 'OmegaMessageSegment') -> 'OmegaMessageSegment':
        match message_segment.type:
            case 'audio' | 'image' | 'video' | 'voice':
                if str(image_url := message_segment.data.get('url', '')).startswith(('http://', 'https://')):
                    target_file = await self._download_resource_file(seg_type=message_segment.type, url=image_url)
                    message_segment = OmegaMessageSegment.image(url=target_file.path)
            case _:
                pass

        return message_segment

    async def dumps(self) -> 'OmegaMessage':
        new_message = OmegaMessage()

        for message_segment in self.parsed_message:
            new_message.append(await self.dump_segment_resource(message_segment=message_segment))

        return new_message


__all__ = [
    'MessageTransferUtils',
]
