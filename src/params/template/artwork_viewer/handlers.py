"""
@Author         : Ailitonia
@Date           : 2026/10/17 14:14
@FileName       : handlers
@Project        : omega-miya
@Description    : omega 图站浏览与查询通用命令模板
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from collections.abc import Awaitable, Callable, Sequence
from datetime import datetime
from typing import TYPE_CHECKING, Literal

from arclet.alconna import Alconna, Args, CommandMeta, MultiVar, Option, Subcommand
from nonebot.exception import MatcherException
from nonebot.log import logger
from nonebot_plugin_alconna import AlconnaMatcher, Match, on_alconna
from nonebot_plugin_alconna.uniseg import UniMessage

from src.database.internal.artwork_collection import ArtworkRating
from src.service import OmegaMatcherInterface, enable_processor_state
from src.service.omega_message_context.custom_depends import ARTWORK_CONTEXT_MANAGER
from src.utils.process_utils import semaphore_gather
from ...depends import EVENT_M_IFACE
from ...handler import ensure_arg_text, ensure_multi_args_text
from ...message_builder import build_sendable_image

if TYPE_CHECKING:
    from nonebot.typing import T_Handler

    from src.service.artwork_proxy.internal import ArtworkProcessParamType, ArtworkRankParamType, BaseArtworkProxy

type ArtworkProcessHandler = Callable[[int], 'ArtworkProcessParamType']
"""作品图片分级处理策略"""

ALLOW_R18_NODE: Literal['allow_r18'] = 'allow_r18'
"""允许预览 r18 作品的权限节点"""

_DEFAULT_SHOW_PAGES_LIMITING: int = 10
_DEFAULT_SHOW_ARTWORKS_LIMITING: int = 60

_DEFAULT_REVOKE_DELAY: int = 90
"""默认的消息撤回延迟"""
_HANDLER_PROMPT_TIMEOUT: float = 60
"""命令交互等待用户响应超时时间"""


async def _allow_r18_node_checker(interface: OmegaMatcherInterface) -> bool:
    """判断当前主体是否具有允许预览 r18 作品的权限"""
    if interface.matcher.plugin is None:
        return False

    async with interface.create_current_entity_session() as entity:
        if not await entity.check_global_permission():
            return False
        verified_auth = await entity.verify_auth_setting(
            module=interface.matcher.plugin.module_name,
            plugin=interface.matcher.plugin.name,
            node=ALLOW_R18_NODE
        )
        return verified_auth == 1


def _default_normal_artwork_process_handler(rating: int) -> 'ArtworkProcessParamType':
    """普通模式对 QUESTIONABLE 以上作品模糊; UNKNOWN 默认仅标记, 源站特定策略由应用层注入"""
    return 'blur' if rating >= ArtworkRating.QUESTIONABLE else 'mark'


def _default_allow_r18_artwork_process_handler(rating: int) -> 'ArtworkProcessParamType':
    """允许 R-18 模式对 QUESTIONABLE 以上作品噪点处理; UNKNOWN 默认仅标记, 由应用层注入特定策略"""
    return 'noise' if rating >= ArtworkRating.QUESTIONABLE else 'mark'


class ArtworkViewerHandlerFactory[AP_T: BaseArtworkProxy]:
    """图站作品浏览查询等命令整合"""

    def __init__(
            self,
            artwork_proxy: type[AP_T],
            command_prefix: str | None = None,
            *,
            aliases_command_prefix: set[str] | None = None,
            normal_artwork_process_handler: ArtworkProcessHandler | None = None,
            allow_r18_artwork_process_handler: ArtworkProcessHandler | None = None,
            need_decimal_artwork_id: bool = False,
            need_decimal_user_id: bool = False,
    ) -> None:
        self._artwork_proxy = artwork_proxy

        command_prefix = (
            artwork_proxy.get_origin_name() if command_prefix is None else command_prefix
        ).strip().lower()
        if not command_prefix:
            raise ValueError('command_prefix must not be empty')
        self._command_prefix = command_prefix

        self._aph_normal = normal_artwork_process_handler or _default_normal_artwork_process_handler
        self._aph_allow_r18 = allow_r18_artwork_process_handler or _default_allow_r18_artwork_process_handler

        self._aliases_command_prefix: set[str] = set(aliases_command_prefix or set())
        self._need_decimal_artwork_id = need_decimal_artwork_id
        self._need_decimal_user_id = need_decimal_user_id

    def __str__(self) -> str:
        return f'ArtworkViewerHandlerFactory | {self.origin.title()}'

    @property
    def origin(self) -> str:
        """获取作品来源名称"""
        return self._artwork_proxy.get_origin_name()

    def get_artwork_proxy(self, artwork_id: str | int) -> AP_T:
        """实例化 ArtworkProxy"""
        return self._artwork_proxy(artwork_id)

    async def check_allow_r18(self, interface: OmegaMatcherInterface) -> bool:
        """判断当前主体是否具有允许预览 r18 作品的权限, 检查失败时按无权限处理"""
        try:
            return await _allow_r18_node_checker(interface=interface)
        except Exception as e:
            logger.warning(f'{self} | Checking {interface} ALLOW_R18_NODE node failed, {e}')
            return False

    async def send_artwork_message(
            self,
            interface: OmegaMatcherInterface,
            artwork: AP_T,
            *,
            allow_r18: bool = False,
            show_pages_limiting: int = _DEFAULT_SHOW_PAGES_LIMITING,
    ) -> None:
        """发送作品图片消息

        撤回策略: QUESTIONABLE 以上且实际处理模式不是 blur 时撤回
        """
        if show_pages_limiting < 1:
            raise ValueError('show_pages_limiting must be greater than or equal to 1')

        artwork_data = await artwork.query()
        if not artwork_data.pages:
            raise ValueError(f'{artwork} has no available pages')
        artwork_desc = await artwork.get_std_desc()

        process_mode = (self._aph_allow_r18 if allow_r18 else self._aph_normal)(artwork_data.rating)
        need_revoke = (artwork_data.rating >= ArtworkRating.QUESTIONABLE) and (process_mode != 'blur')

        show_pages_num = min(len(artwork_data.pages), show_pages_limiting)
        if len(artwork_data.pages) > show_pages_num:
            artwork_desc = f'({show_pages_num} of {len(artwork_data.pages)} pages)\n{"-" * 16}\n{artwork_desc}'

        tasks = [
            artwork.get_custom_proceed_page_file(page_index=page_index, process_mode=process_mode)
            for page_index in range(show_pages_num)
        ]
        proceed_pages = await semaphore_gather(tasks=tasks, semaphore_num=8, return_exceptions=False)

        pages_path_tasks = [x.get_hosting_path() for x in proceed_pages]
        pages_hosting_paths = await semaphore_gather(tasks=pages_path_tasks, semaphore_num=8, return_exceptions=False)

        send_msg = UniMessage(build_sendable_image(path) for path in pages_hosting_paths) + f'\n{artwork_desc}'
        receipt = await interface.send_reply(send_msg)

        try:
            await ARTWORK_CONTEXT_MANAGER.set_message_context(receipt=receipt, **artwork_data.model_dump())
        except Exception as e:
            logger.warning(f'{self} | Set {artwork} context failed, {e}')

        if need_revoke:
            try:
                await interface.revoke_bot_sent_msg(receipt=receipt, revoke_delay=_DEFAULT_REVOKE_DELAY)
            except Exception as e:
                logger.warning(f'{self} | Schedule revoking {artwork} message failed, {e}')

    async def send_artworks_preview_message(
            self,
            interface: OmegaMatcherInterface,
            title: str,
            artworks: Sequence[AP_T],
            *,
            allow_r18: bool = False,
            show_artworks_limiting: int = _DEFAULT_SHOW_ARTWORKS_LIMITING,
    ) -> None:
        """生成并发送多个作品的预览图消息

        撤回策略: 仅在 allow_r18 时撤回, 各作品的实际分级在预览图生成前是懒加载的, 无法在发送前廉价判定
        """
        if show_artworks_limiting < 1:
            raise ValueError('show_artworks_limiting must be greater than or equal to 1')
        if not artworks:
            raise ValueError('artworks must not be empty')

        selected_artworks = artworks[:show_artworks_limiting]
        preview_image = await self._artwork_proxy.generate_artworks_preview(
            preview_name=title,
            artworks=selected_artworks,
            process_handler=(self._aph_allow_r18 if allow_r18 else self._aph_normal),
            preview_size=(360, 360),
            num_of_line=6,
            limit=show_artworks_limiting,
        )
        send_msg = UniMessage(build_sendable_image(await preview_image.get_hosting_path()))
        receipt = await interface.send_reply(send_msg)

        if allow_r18:
            try:
                await interface.revoke_bot_sent_msg(receipt=receipt, revoke_delay=_DEFAULT_REVOKE_DELAY)
            except Exception as e:
                logger.warning(f'{self} | Schedule revoking {title} preview message failed, {e}')

    @staticmethod
    def _parse_ranking_mode(mode: str) -> 'ArtworkRankParamType | None':
        """解析榜单类型, 未提供时默认月榜, 非法模式返回 None"""
        match mode.strip().lower():
            case '' | '月榜' | '每月' | '月' | 'month' | 'monthly':
                return 'monthly'
            case '日榜' | '每日' | '日' | 'day' | 'daily':
                return 'daily'
            case '周榜' | '每周' | '周' | 'week' | 'weekly':
                return 'weekly'
            case _:
                return None

    async def query_artwork(self, artwork_id: str) -> tuple[list[AP_T], str]:
        """构造单作品详情查询结果"""
        return [self.get_artwork_proxy(artwork_id)], ''

    async def query_random(self, limit: int) -> tuple[list[AP_T], str]:
        """随机获取作品"""
        artworks = await self._artwork_proxy.random(limit=limit)
        return artworks, f'{self.origin.title()} Random Artworks'

    async def query_search(self, keyword: str, page: int) -> tuple[list[AP_T], str]:
        """根据关键词搜索作品"""
        artworks = await self._artwork_proxy.search(keyword=keyword, page=page)
        return artworks, f'{self.origin.title()} Search: {keyword}'

    async def query_ranking(self, mode: 'ArtworkRankParamType', page: int) -> tuple[list[AP_T], str]:
        """获取榜单作品"""
        artworks = await self._artwork_proxy.ranking(mode=mode, page=page)
        title = f'{self.origin.title()} {mode.title()} Ranking {datetime.now().strftime("%Y-%m-%d")}'
        return artworks, title

    async def query_bookmark(self, uid: str, page: int) -> tuple[list[AP_T], str]:
        """获取用户收藏作品"""
        artworks = await self._artwork_proxy.query_user_bookmark_artworks(uid=uid, page=page)
        return artworks, f'{self.origin.title()} User Bookmark - UID: {uid}'

    async def query_user(
            self,
            uid: str,
            page: int,
            *,
            page_size: int = _DEFAULT_SHOW_ARTWORKS_LIMITING,
    ) -> tuple[list[AP_T], str]:
        """获取用户作品, 复用同一次用户信息查询结果进行分页"""
        user_data = await self._artwork_proxy.query_user(uid=uid, use_cache=False)
        page_start = page_size * (page - 1)
        artwork_ids = user_data.artwork_ids[page_start:page_start + page_size]
        artworks = [self.get_artwork_proxy(artwork_id) for artwork_id in artwork_ids]
        return artworks, f'{self.origin.title()} User Artwork - {user_data.name}/UID: {user_data.uid}'

    async def execute_query_and_send_result(
            self,
            interface: OmegaMatcherInterface,
            query_handler: Awaitable[tuple[list[AP_T], str]],
            *,
            allow_r18: bool,
            show_artworks_limiting: int = _DEFAULT_SHOW_ARTWORKS_LIMITING,
    ) -> None:
        """执行作品查询并统一转换异常, 根据查询结果发送作品消息"""
        try:
            artworks, title = await query_handler
            if not artworks:
                await interface.finish_reply('未找到相关作品, 请尝试调整查询条件后重试')
            elif len(artworks) == 1:
                await self.send_artwork_message(
                    interface=interface,
                    artwork=artworks[0],
                    allow_r18=allow_r18,
                )
            else:
                await self.send_artworks_preview_message(
                    interface=interface,
                    title=title,
                    artworks=artworks,
                    allow_r18=allow_r18,
                    show_artworks_limiting=show_artworks_limiting
                )
        except MatcherException:
            raise
        except NotImplementedError as e:
            logger.warning(f'{self} | Artwork operation is not supported, {e}')
            await interface.finish_reply(f'{self.origin.title()}不支持该功能, 请确认后再重试')
        except Exception as e:
            logger.error(f'{self} | Query or send artworks failed, {e}')
            await interface.finish_reply('获取作品失败了, 可能是网络原因或者作品已经被删除, 请稍后再试')

    def _generate_view_artwork_handler(self) -> 'T_Handler':
        """生成单作品详情查看流程"""

        async def _view_artwork_handler(
                matcher: AlconnaMatcher,
                interface: EVENT_M_IFACE,
                artwork_id: Match[str],
        ) -> None:
            target_artwork_id = await ensure_arg_text(
                matcher=matcher,
                interface=interface,
                arg=artwork_id,
                prompt_text='请输入要查看的作品ID:',
                timeout=_HANDLER_PROMPT_TIMEOUT,
            )
            if self._need_decimal_artwork_id and not target_artwork_id.isdecimal():
                await interface.finish_reply('作品ID应当为纯数字, 请确认后重试')

            allow_r18 = await self.check_allow_r18(interface=interface)
            await interface.send_reply('稍等, 正在获取作品信息~')
            await self.execute_query_and_send_result(
                interface=interface,
                query_handler=self.query_artwork(artwork_id=target_artwork_id),
                allow_r18=allow_r18,
            )

        return _view_artwork_handler

    def _generate_random_artworks_handler(self) -> 'T_Handler':
        """生成随机作品查询流程"""

        async def _random_artworks_handler(
                interface: EVENT_M_IFACE,
                num: Match[int],
        ) -> None:
            num_value = num.result if num.available else _DEFAULT_SHOW_ARTWORKS_LIMITING
            if not 1 <= num_value <= _DEFAULT_SHOW_ARTWORKS_LIMITING:
                await interface.finish_reply(f'作品数量应当在 1~{_DEFAULT_SHOW_ARTWORKS_LIMITING} 之间, 请确认后重试')

            allow_r18 = await self.check_allow_r18(interface=interface)
            await interface.send_reply('稍等, 正在获取作品信息~')
            await self.execute_query_and_send_result(
                interface=interface,
                query_handler=self.query_random(limit=num_value),
                allow_r18=allow_r18,
                show_artworks_limiting=num_value,
            )

        return _random_artworks_handler

    def _generate_search_artworks_handler(self) -> 'T_Handler':
        """生成关键词搜索流程"""

        async def _search_artworks_handler(
                matcher: AlconnaMatcher,
                interface: EVENT_M_IFACE,
                keywords: Match[Sequence[str]],
                page: Match[int],
        ) -> None:
            page_value = page.result if page is not None and page.available else 1
            if page_value < 1:
                await interface.finish_reply('查询页码应当为正整数, 请确认后重试')

            keywords_list = await ensure_multi_args_text(
                matcher=matcher,
                interface=interface,
                multi_args=keywords,
                prompt_text='请输入要搜索的作品关键词:',
                timeout=_HANDLER_PROMPT_TIMEOUT,
            )
            allow_r18 = await self.check_allow_r18(interface=interface)
            await interface.send_reply('稍等, 正在获取作品信息~')
            await self.execute_query_and_send_result(
                interface=interface,
                query_handler=self.query_search(keyword=' '.join(keywords_list), page=page_value),
                allow_r18=allow_r18,
            )

        return _search_artworks_handler

    def _generate_ranking_artworks_handler(self) -> 'T_Handler':
        """生成榜单作品查询流程"""

        async def _ranking_artworks_handler(
                interface: EVENT_M_IFACE,
                mode: Match[str],
                page: Match[int],
        ) -> None:
            ranking_mode = self._parse_ranking_mode(mode.result if mode.available else '')
            if ranking_mode is None:
                await interface.finish_reply('榜单类型应当为【日榜/周榜/月榜】, 请确认后重试')

            page_value = page.result if page is not None and page.available else 1
            if page_value < 1:
                await interface.finish_reply('查询页码应当为正整数, 请确认后重试')

            allow_r18 = await self.check_allow_r18(interface=interface)
            await interface.send_reply('稍等, 正在获取作品信息~')
            await self.execute_query_and_send_result(
                interface=interface,
                query_handler=self.query_ranking(mode=ranking_mode, page=page_value),
                allow_r18=allow_r18,
            )

        return _ranking_artworks_handler

    def _generate_bookmark_artworks_handler(self) -> 'T_Handler':
        """生成用户收藏作品查询流程"""

        async def _bookmark_artworks_handler(
                matcher: AlconnaMatcher,
                interface: EVENT_M_IFACE,
                uid: Match[str],
                page: Match[int],
        ) -> None:
            target_uid = await ensure_arg_text(
                matcher=matcher,
                interface=interface,
                arg=uid,
                prompt_text='请输入要查询收藏作品的用户ID:',
                timeout=_HANDLER_PROMPT_TIMEOUT,
            )
            if self._need_decimal_user_id and not target_uid.isdecimal():
                await interface.finish_reply('用户ID应当为纯数字, 请确认后重试')

            page_value = page.result if page is not None and page.available else 1
            if page_value < 1:
                await interface.finish_reply('查询页码应当为正整数, 请确认后重试')

            allow_r18 = await self.check_allow_r18(interface=interface)
            await interface.send_reply('稍等, 正在获取作品信息~')
            await self.execute_query_and_send_result(
                interface=interface,
                query_handler=self.query_bookmark(uid=target_uid, page=page_value),
                allow_r18=allow_r18,
            )

        return _bookmark_artworks_handler

    def _generate_user_artworks_handler(self) -> 'T_Handler':
        """生成用户作品查询流程"""

        async def _user_artworks_handler(
                matcher: AlconnaMatcher,
                interface: EVENT_M_IFACE,
                uid: Match[str],
                page: Match[int],
        ) -> None:
            target_uid = await ensure_arg_text(
                matcher=matcher,
                interface=interface,
                arg=uid,
                prompt_text='请输入要查询作品的用户ID:',
                timeout=_HANDLER_PROMPT_TIMEOUT,
            )
            if self._need_decimal_user_id and not target_uid.isdecimal():
                await interface.finish_reply('用户ID应当为纯数字, 请确认后重试')

            page_value = page.result if page is not None and page.available else 1
            if page_value < 1:
                await interface.finish_reply('查询页码应当为正整数, 请确认后重试')

            allow_r18 = await self.check_allow_r18(interface=interface)
            await interface.send_reply('稍等, 正在获取作品信息~')
            await self.execute_query_and_send_result(
                interface=interface,
                query_handler=self.query_user(uid=target_uid, page=page_value),
                allow_r18=allow_r18,
            )

        return _user_artworks_handler

    def register_handlers(
            self,
            *,
            priority: int = 10,
            block: bool = True,
            permission_level: int = 50,
            auth_node: str | None = None,
            extra_auth_node: set[str] | None = None,
            cooldown: int = 60,
            handler_echo_processor_result: bool = True,
    ) -> type[AlconnaMatcher]:
        """注册图站作品查询与浏览命令组"""
        artwork_matcher = on_alconna(
            Alconna(
                self._command_prefix,
                Args['artwork_id?#作品ID', str],
                Subcommand(
                    '随机',
                    Option('--num|-n', Args['num#作品数量', int], help_text='限制输出作品数量'),
                    alias=['random'],
                    help_text='随机获取作品',
                ),
                Subcommand(
                    '搜索',
                    Args['keywords?#搜索关键词', MultiVar(str)],
                    Option('--page|-p', Args['page#页码', int], help_text='查询页码'),
                    alias=['search'],
                    help_text='根据关键词搜索作品',
                ),
                Subcommand(
                    '榜单',
                    Args['mode?#日榜/周榜/月榜', str],
                    Option('--page|-p', Args['page#页码', int], help_text='查询页码'),
                    alias=['ranking'],
                    help_text='获取榜单作品',
                ),
                Subcommand(
                    '收藏',
                    Args['uid?#用户ID', str],
                    Option('--page|-p', Args['page#页码', int], help_text='查询页码'),
                    alias=['bookmark'],
                    help_text='获取用户收藏作品',
                ),
                Subcommand(
                    '用户',
                    Args['uid?#用户ID', str],
                    Option('--page|-p', Args['page#页码', int], help_text='查询页码'),
                    alias=['user'],
                    help_text='获取用户作品',
                ),
                meta=CommandMeta(
                    description=f'{self.origin.title()}作品查询与浏览',
                    usage=f'{self._command_prefix} <随机|搜索|榜单|收藏|用户> [参数] [选项]',
                    example=f'{self._command_prefix} 搜索 keyword --page 1',
                    compact=True,
                ),
            ),
            use_cmd_start=True,
            aliases=self._aliases_command_prefix if self._aliases_command_prefix else None,
            priority=priority,
            block=block,
            default_state=enable_processor_state(
                name=self._command_prefix.title(),
                level=permission_level,
                auth_node=auth_node or self._command_prefix,
                extra_auth_node={ALLOW_R18_NODE} | set(extra_auth_node or set()),
                cooldown=cooldown,
                echo_processor_result=handler_echo_processor_result,
            ),
        )

        artwork_matcher.assign('$main')(self._generate_view_artwork_handler())
        artwork_matcher.assign('随机')(self._generate_random_artworks_handler())
        artwork_matcher.assign('搜索')(self._generate_search_artworks_handler())
        artwork_matcher.assign('榜单')(self._generate_ranking_artworks_handler())
        artwork_matcher.assign('收藏')(self._generate_bookmark_artworks_handler())
        artwork_matcher.assign('用户')(self._generate_user_artworks_handler())

        artwork_matcher.test(f'{self._command_prefix} 123456')
        artwork_matcher.test(f'{self._command_prefix} 随机 --num 3')
        artwork_matcher.test(f'{self._command_prefix} random -n 3')
        artwork_matcher.test(f'{self._command_prefix} 搜索 foo bar --page 2')
        artwork_matcher.test(f'{self._command_prefix} search foo bar -p 2')
        artwork_matcher.test(f'{self._command_prefix} 榜单 日榜')
        artwork_matcher.test(f'{self._command_prefix} ranking weekly')
        artwork_matcher.test(f'{self._command_prefix} 收藏 12345 --page 2')
        artwork_matcher.test(f'{self._command_prefix} 用户 12345')

        return artwork_matcher


__all__ = [
    'ALLOW_R18_NODE',
    'ArtworkViewerHandlerFactory',
    'ArtworkProcessHandler',
]
