"""
@Author         : Ailitonia
@Date           : 2024/8/31 上午1:53
@FileName       : handlers
@Project        : omega-miya
@Description    : 命令处理流程
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from collections.abc import Sequence
from datetime import datetime
from random import sample
from typing import TYPE_CHECKING, Annotated

from nonebot.log import logger
from nonebot.params import ShellCommandArgs
from nonebot.plugin import on_shell_command
from nonebot.rule import ArgumentParser, Namespace
from pydantic import BaseModel, ConfigDict

from src.params.depends import EVENT_MATCHER_INTERFACE
from src.params.handler import get_shell_command_parse_failed_handler
from src.service import OmegaMessage, OmegaMessageSegment, enable_processor_state
from src.service.artwork_proxy.add_ons import ImageOpsMixin, UserSpaceMixin
from src.service.omega_message_context.custom_depends import ARTWORK_CONTEXT_MANAGER
from src.utils import semaphore_gather
from .consts import ALLOW_R18_NODE

if TYPE_CHECKING:
    from nonebot.typing import T_Handler


type ProcessorReturn[T: 'ImageOpsMixin'] = tuple[list[T], str]


class ArtworkHandlerQueryArguments(BaseModel):
    """命令的参数解析结果"""
    random: bool
    search: bool
    view: bool
    ranking: bool
    bookmark: bool
    user: bool
    num: int
    page: int
    keywords: list[str]

    model_config = ConfigDict(extra='ignore', coerce_numbers_to_str=True, from_attributes=True)


class ArtworkHandlerManager[T: 'ImageOpsMixin']:
    """图站作品搜索预览等命令整合"""

    def __init__(self, artwork_class: type[T]):
        self._artwork_class = artwork_class
        self._command_name = artwork_class.get_base_origin_name().lower()

    @staticmethod
    async def _allow_r18_node_checker(interface: EVENT_MATCHER_INTERFACE) -> bool:
        """判断当前 entity 主体是否具有允许预览 r18 作品的权限"""
        if interface.matcher.plugin is None:
            return False

        return (
            await interface.entity.check_global_permission()
            and await interface.entity.check_auth_setting(
                module=interface.matcher.plugin.module_name,
                plugin=interface.matcher.plugin.name,
                node=ALLOW_R18_NODE
            )
        )

    @classmethod
    async def has_allow_r18_node(cls, interface: EVENT_MATCHER_INTERFACE) -> bool:
        """判断当前 entity 主体是否具有允许预览 r18 作品的权限"""
        try:
            allow_r18 = await cls._allow_r18_node_checker(interface=interface)
        except Exception as e:
            logger.warning(f'OmegaAnyArtwork | Checking {interface.entity} r18 node failed, {e!r}')
            allow_r18 = False
        return allow_r18

    @staticmethod
    def _get_query_argument_parser() -> ArgumentParser:
        """命令的参数解析器"""
        parser = ArgumentParser(prog='作品查询命令参数解析', description='Parse artwork query arguments')
        parser.add_argument('-r', '--random', action='store_true')
        parser.add_argument('-s', '--search', action='store_true')
        parser.add_argument('-v', '--view', action='store_true')
        parser.add_argument('-k', '--ranking', action='store_true')
        parser.add_argument('-b', '--bookmark', action='store_true')
        parser.add_argument('-u', '--user', action='store_true')
        parser.add_argument('-n', '--num', type=int, default=6)
        parser.add_argument('-p', '--page', type=int, default=1)
        parser.add_argument('keywords', nargs='*')
        return parser

    @staticmethod
    def _parse_from_query_parser(args: Namespace) -> ArtworkHandlerQueryArguments:
        """解析查询命令参数"""
        return ArtworkHandlerQueryArguments.model_validate(args)

    def _get_artwork_ap(self, artwork_id: str | int) -> T:
        """获取作品对应的 ArtworkProxy 对象"""
        return self._artwork_class(artwork_id=artwork_id)

    @classmethod
    async def send_artwork_message(
            cls,
            interface: EVENT_MATCHER_INTERFACE,
            artwork: T,
            *,
            no_blur_rating: int = 1,
            show_page_limiting: int = 10,
    ) -> None:
        """发送作品图片消息"""
        artwork_data = await artwork.query()
        artwork_desc = await artwork.get_std_desc()
        need_revoke = True if (artwork_data.rating.value >= 2 and no_blur_rating >= 2) else False

        # 处理作品预览
        show_page_num = min(len(artwork_data.pages), show_page_limiting)
        if len(artwork_data.pages) > show_page_num:
            artwork_desc = f'({show_page_limiting} of {len(artwork_data.pages)} pages)\n{"-" * 16}\n{artwork_desc}'

        tasks = [
            artwork.get_proceed_page_file(page_index=page_index, no_blur_rating=no_blur_rating)
            for page_index in range(show_page_num)
        ]
        proceed_pages = await semaphore_gather(tasks=tasks, semaphore_num=10, return_exceptions=False)

        pages_url_tasks = [
            x.get_hosting_path()
            for x in proceed_pages
        ]
        pages_hosting_urls = await semaphore_gather(tasks=pages_url_tasks, semaphore_num=10, return_exceptions=False)

        # 拼接待发送消息
        send_msg = OmegaMessage(OmegaMessageSegment.image(url) for url in pages_hosting_urls)
        send_msg = send_msg + f'\n{artwork_desc}'

        if need_revoke:
            response, _ = await interface.send_reply_auto_revoke(send_msg, 60)
        else:
            response = await interface.send_reply(send_msg)

        await ARTWORK_CONTEXT_MANAGER.set_message_context(response=response, **artwork_data.model_dump())

    @classmethod
    async def send_artworks_preview_message(
            cls,
            interface: EVENT_MATCHER_INTERFACE,
            title: str,
            artworks: Sequence[T],
            *,
            no_blur_rating: int = 1,
            artworks_num_limiting: int = 60,
    ) -> None:
        """生成并发送多个作品的预览图"""
        need_revoke = True if no_blur_rating >= 2 else False
        artwork_proxy: type[T] = artworks[0].__class__

        preview_image = await artwork_proxy.generate_artworks_preview(
            preview_name=title,
            artworks=artworks,
            no_blur_rating=no_blur_rating,
            preview_size=(360, 360),
            num_of_line=6,
            limit=artworks_num_limiting,
        )
        send_msg = OmegaMessageSegment.image(await preview_image.get_hosting_path())

        if need_revoke:
            await interface.send_reply_auto_revoke(send_msg, 60)
        else:
            await interface.send_reply(send_msg)

    async def _send_artworks_messages(
            self,
            interface: EVENT_MATCHER_INTERFACE,
            artworks: Sequence[T],
            *,
            no_blur_rating: int = 1,
            show_page_limiting: int = 10,
            artworks_num_limiting: int = 8,
            random_artworks: bool = False,
    ) -> None:
        """发送多个作品图片消息"""
        if len(artworks) > artworks_num_limiting:
            if random_artworks:
                artworks = sample(artworks, k=artworks_num_limiting)
            else:
                artworks = artworks[:artworks_num_limiting]

        # 预载作品图片文件
        await semaphore_gather(
            tasks=[artwork.get_all_pages_file(page_limit=show_page_limiting) for artwork in artworks],
            semaphore_num=artworks_num_limiting,
            filter_exception=True,
        )

        # 顺序发送作品图片
        for artwork in artworks:
            try:
                await self.send_artwork_message(
                    interface=interface,
                    artwork=artwork,
                    no_blur_rating=no_blur_rating,
                    show_page_limiting=show_page_limiting,
                )
            except Exception as e:
                logger.error(f'OmegaAnyArtwork | Send artwork {artwork} failed, {e}')

    async def _send_artworks_preview_message(
            self,
            interface: EVENT_MATCHER_INTERFACE,
            title: str,
            artworks: Sequence[T],
            *,
            no_blur_rating: int = 1,
            artworks_num_limiting: int = 60,
    ) -> None:
        """生成并发送多个作品的预览图"""

        # 预载作品图片文件
        await semaphore_gather(
            tasks=[artwork.get_page_file(page_type='preview') for artwork in artworks],
            semaphore_num=10,
            filter_exception=True,
        )

        return await self.send_artworks_preview_message(
            interface=interface,
            title=title,
            artworks=artworks,
            no_blur_rating=no_blur_rating,
            artworks_num_limiting=artworks_num_limiting,
        )

    def generate_default_shell_handler(self) -> 'T_Handler':
        """生成插件命令命令函数以供注册"""

        origin_title = self._command_name.title()

        async def _random_processor(limit: int) -> ProcessorReturn[T]:
            artworks = await self._artwork_class.random(limit=limit)
            title = f'{origin_title} Random Artworks'
            return artworks, title

        async def _search_processor(keyword: str, page: int) -> ProcessorReturn[T]:
            artworks = await self._artwork_class.search(keyword=keyword, page=page)
            title = f'{origin_title} Search: {keyword}'
            return artworks, title

        async def _ranking_processor(mode: str, page: int) -> ProcessorReturn[T]:
            if not issubclass(self._artwork_class, UserSpaceMixin):
                raise TypeError(f'{self._artwork_class.__name__} not support ranking method')

            match mode:
                case '日榜' | '每日' | '日' | 'day' | 'daily':
                    artworks = await self._artwork_class.ranking(mode='daily', page=page)
                    title = f'{origin_title} Daily Ranking {datetime.now().strftime("%Y-%m-%d")}'
                case '周榜' | '每周' | '周' | 'week' | 'weekly':
                    artworks = await self._artwork_class.ranking(mode='weekly', page=page)
                    title = f'{origin_title} Weekly Ranking {datetime.now().strftime("%Y-%m-%d")}'
                case '月榜' | '每月' | '月' | 'month' | 'monthly' | _:
                    artworks = await self._artwork_class.ranking(mode='monthly', page=page)
                    title = f'{origin_title} Monthly Ranking {datetime.now().strftime("%Y-%m-%d")}'
            return artworks, title

        async def _bookmark_processor(uid: str, page: int) -> ProcessorReturn[T]:
            if not issubclass(self._artwork_class, UserSpaceMixin):
                raise TypeError(f'{self._artwork_class.__name__} not support bookmark method')

            artworks = await self._artwork_class.query_user_bookmark_artworks(uid=uid, page=page)
            title = f'{origin_title} User Bookmark - {uid}'
            return artworks, title

        async def _user_artwork_processor(uid: str, page: int) -> ProcessorReturn[T]:
            if not issubclass(self._artwork_class, UserSpaceMixin):
                raise TypeError(f'{self._artwork_class.__name__} not support user-artwork method')

            user_data = await self._artwork_class.query_user(uid=uid)
            artworks = await self._artwork_class.query_user_artworks(uid=uid)
            title = f'{origin_title} User Artwork - {user_data.name}'

            p_start = 48 * (page - 1)
            p_end = 48 * page
            return artworks[p_start:p_end], title

        async def _handler(
                interface: EVENT_MATCHER_INTERFACE,
                args: Annotated[Namespace, ShellCommandArgs()],
        ) -> None:
            try:
                parsed_args = self._parse_from_query_parser(args=args)
                keyword = ' '.join(parsed_args.keywords)

            except Exception as e:
                logger.warning(f'OmegaAnyArtwork | 命令参数解析错误, {e}')
                await interface.finish_reply('命令参数解析错误, 请确认后重试')

            # 检查权限确定图片处理模式
            allow_r18 = await self.has_allow_r18_node(interface=interface)
            no_blur_rating = 3 if allow_r18 else 1

            await interface.send_reply('稍等, 正在获取作品信息~')

            try:
                # 校验 ArtworkProxy 类型
                if not issubclass(self._artwork_class, ImageOpsMixin):
                    raise TypeError(f'{self._artwork_class.__name__} not support ImageOps method')

                # 处理互斥的选项
                if len([
                    x
                    for x in (parsed_args.search, parsed_args.ranking, parsed_args.bookmark, parsed_args.user)
                    if x
                ]) > 1:
                    raise TypeError('Mutually exclusive options are set')

                # 处理命令分支
                if parsed_args.search:  # 搜索作品
                    artworks, title = await _search_processor(keyword=keyword, page=parsed_args.page)
                elif parsed_args.ranking:  # 排行榜
                    artworks, title = await _ranking_processor(mode=keyword.strip(), page=parsed_args.page)
                elif parsed_args.bookmark and (uid := keyword.strip()).isdigit():  # 用户收藏作品
                    artworks, title = await _bookmark_processor(uid=uid, page=parsed_args.page)
                elif parsed_args.user and (uid := keyword.strip()).isdigit():  # 用户作品
                    artworks, title = await _user_artwork_processor(uid=uid, page=parsed_args.page)
                elif parsed_args.random:  # 随机作品
                    artworks, title = await _random_processor(limit=max(parsed_args.num, 24))
                elif (artwork_id := keyword.strip()).isdigit():  # 作品详情
                    artworks = [self._get_artwork_ap(artwork_id=artwork_id)]
                    title = ''
                    parsed_args.view = True
                else:
                    await interface.send_reply('作品或用户ID应当为纯数字, 请确认后再重试吧')
                    return

                if parsed_args.view:
                    await self._send_artworks_messages(
                        interface=interface,
                        artworks=artworks,
                        no_blur_rating=no_blur_rating,
                        artworks_num_limiting=parsed_args.num,
                        random_artworks=parsed_args.random,
                    )
                else:
                    await self._send_artworks_preview_message(
                        interface=interface,
                        title=title,
                        artworks=artworks,
                        no_blur_rating=no_blur_rating,
                        artworks_num_limiting=max(parsed_args.num, 60),
                    )
            except TypeError as e:
                logger.warning(f'OmegaAnyArtwork | 不支持的参数或作品来源类型, {origin_title}, {parsed_args}, {e}')
                await interface.finish_reply(message=f'{origin_title}不支持该参数, 请确认后再重试吧')
            except Exception as e:
                logger.error(f'OmegaAnyArtwork | 获取作品预览失败, {parsed_args}, {e}')
                await interface.finish_reply(message='获取作品失败了QAQ, 可能是网络原因或者作品已经被删除, 请稍后再试')

        return _handler

    def register_handler(self) -> 'T_Handler':
        """注册图库调用命令"""
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
        ).handle()(self.generate_default_shell_handler())


__all__ = [
    'ArtworkHandlerManager',
]
