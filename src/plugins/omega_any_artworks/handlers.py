"""
@Author         : Ailitonia
@Date           : 2024/8/31 上午1:53
@FileName       : handlers
@Project        : omega-miya
@Description    : 命令处理流程
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import TYPE_CHECKING, Annotated, Sequence

from nonebot.log import logger
from nonebot.params import Depends, ShellCommandArgs
from nonebot.plugin import on_shell_command
from nonebot.rule import ArgumentParser, Namespace
from pydantic import BaseModel, ConfigDict

from src.params.handler import get_shell_command_parse_failed_handler
from src.service import OmegaMatcherInterface as OmMI, OmegaMessage, OmegaMessageSegment, enable_processor_state
from src.utils.process_utils import semaphore_gather
from .consts import ALLOW_R18_NODE

if TYPE_CHECKING:
    from nonebot.typing import T_Handler
    from src.service.artwork_proxy.add_ons.image_ops import ImageOpsMixin


class ArtworkHandlerQueryArguments(BaseModel):
    """命令的参数解析结果"""
    random: bool
    search: bool
    page: int
    keywords: list[str]

    model_config = ConfigDict(extra='ignore', coerce_numbers_to_str=True, from_attributes=True)


class ArtworkHandlerManager[T: "ImageOpsMixin"]:
    """图站作品搜索预览等命令整合"""

    def __init__(self, artwork_class: type[T]):
        self._artwork_class = artwork_class
        self._command_name = artwork_class.get_base_origin_name().lower()

    @staticmethod
    async def _allow_r18_node_checker(interface: "OmMI") -> bool:
        """判断当前 entity 主体是否具有允许预览 r18 作品的权限"""
        if interface.matcher.plugin is None:
            return False

        return (
                await interface.entity.check_global_permission() and
                await interface.entity.check_auth_setting(
                    module=interface.matcher.plugin.module_name,
                    plugin=interface.matcher.plugin.name,
                    node=ALLOW_R18_NODE
                )
        )

    @classmethod
    async def _has_allow_r18_node(cls, interface: "OmMI") -> bool:
        """判断当前 entity 主体是否具有允许预览 r18 作品的权限"""
        try:
            allow_r18 = await cls._allow_r18_node_checker(interface=interface)
        except Exception as e:
            logger.warning(f'Checking {interface.entity} r18 node failed, {e!r}')
            allow_r18 = False
        return allow_r18

    @staticmethod
    def _get_query_argument_parser() -> ArgumentParser:
        """命令的参数解析器"""
        parser = ArgumentParser(prog=f'作品查询命令参数解析', description='Parse artwork query arguments')
        parser.add_argument('-r', '--random', action='store_true')
        parser.add_argument('-s', '--search', action='store_true')
        parser.add_argument('-p', '--page', type=int, default=1)
        parser.add_argument('keywords', nargs='*')
        return parser

    @staticmethod
    def _parse_from_query_parser(args: Namespace) -> ArtworkHandlerQueryArguments:
        """解析查询命令参数"""
        return ArtworkHandlerQueryArguments.model_validate(args)

    async def _send_artwork_message(
            self,
            interface: OmMI,
            artwork_id: str | int,
            *,
            no_blur_rating: int = 1,
            show_page_limiting: int = 10,
    ) -> None:
        """预处理待发送图片"""
        artwork_ap: T = self._artwork_class(artwork_id=artwork_id)
        artwork_data = await artwork_ap.query()
        artwork_desc = await artwork_ap.get_std_desc()
        need_revoke = True if (artwork_data.rating.value >= 2 and no_blur_rating >= 2) else False

        # 处理作品预览
        show_page_num = min(len(artwork_data.pages), show_page_limiting)
        if len(artwork_data.pages) > show_page_num:
            artwork_desc = f'({show_page_limiting} of {len(artwork_data.pages)} pages)\n{"-" * 16}\n{artwork_desc}'

        tasks = [
            artwork_ap.get_proceed_page_file(page_index=page_index, no_blur_rating=no_blur_rating)
            for page_index in range(show_page_num)
        ]
        proceed_pages = await semaphore_gather(tasks=tasks, semaphore_num=10, return_exceptions=False)

        # 拼接待发送消息
        send_msg = OmegaMessage(OmegaMessageSegment.image(url=x.path) for x in proceed_pages)
        send_msg = send_msg + f'\n{artwork_desc}'

        if need_revoke:
            await interface.send_reply_auto_revoke(send_msg, 60)
        else:
            await interface.send_reply(send_msg)

    async def _send_artworks_preview_message(
            self,
            interface: OmMI,
            title: str,
            artworks: Sequence[T],
            *,
            no_blur_rating: int = 1,
    ) -> None:
        """生成多个作品的预览图"""
        need_revoke = True if no_blur_rating >= 2 else False

        preview_image = await self._artwork_class.generate_artworks_preview(
            preview_name=title,
            artworks=artworks,
            no_blur_rating=no_blur_rating,
            preview_size=(360, 360),
            num_of_line=6,
        )
        send_msg = OmegaMessageSegment.image(preview_image.path)

        if need_revoke:
            await interface.send_reply_auto_revoke(send_msg, 60)
        else:
            await interface.send_reply(send_msg)

    def generate_shell_handler(self) -> "T_Handler":
        """生成插件命令流程函数以供注册"""

        async def _handler(
                interface: Annotated[OmMI, Depends(OmMI.depend())],
                args: Annotated[Namespace, ShellCommandArgs()],
        ) -> None:
            try:
                parsed_args = self._parse_from_query_parser(args=args)
                keyword = ' '.join(parsed_args.keywords)
            except Exception as e:
                logger.warning(f'OmegaAnyArtwork | 命令参数解析错误, {e}')
                await interface.finish_reply('命令参数解析错误, 请确认后重试')

            # 检查权限确定图片处理模式
            allow_r18 = await self._has_allow_r18_node(interface=interface)
            no_blur_rating = 3 if allow_r18 else 1

            await interface.send_reply_auto_revoke('稍等, 正在获取作品信息~', 30)

            try:
                if parsed_args.random:
                    artworks = await self._artwork_class.random()
                    await self._send_artworks_preview_message(
                        interface=interface,
                        title=f'{self._command_name.title()} Random Artworks',
                        artworks=artworks,
                        no_blur_rating=no_blur_rating,
                    )
                elif parsed_args.search:
                    artworks = await self._artwork_class.search(keyword=keyword, page=parsed_args.page)
                    await self._send_artworks_preview_message(
                        interface=interface,
                        title=f'{self._command_name.title()} Search: {keyword}',
                        artworks=artworks,
                        no_blur_rating=no_blur_rating,
                    )
                elif (artwork_id := keyword.strip()).isdigit():
                    await self._send_artwork_message(
                        interface=interface,
                        artwork_id=artwork_id,
                        no_blur_rating=no_blur_rating,
                    )
                else:
                    await interface.send_reply('作品ArtworkID应当为纯数字, 请确认后再重试吧')
            except Exception as e:
                logger.error(f'OmegaAnyArtwork | 获取作品预览失败, {parsed_args}, {e}')
                await interface.finish_reply(message='获取作品失败了QAQ, 可能是网络原因或者作品已经被删除, 请稍后再试')

        return _handler

    def register_handler(self) -> "T_Handler":
        """注册插件命令"""
        return on_shell_command(
            cmd=self._command_name,
            aliases={self._command_name.title()},
            parser=self._get_query_argument_parser(),
            handlers=[get_shell_command_parse_failed_handler()],
            priority=10,
            block=True,
            state=enable_processor_state(
                name=self._command_name.title(),
                level=50,
                auth_node=self._command_name,
                extra_auth_node={ALLOW_R18_NODE},
                cooldown=60,
            )
        ).handle()(self.generate_shell_handler())


__all__ = [
    "ArtworkHandlerManager",
]
