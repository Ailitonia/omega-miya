"""
@Author         : Ailitonia
@Date           : 2024/6/3 上午2:12
@FileName       : command
@Project        : nonebot2_miya
@Description    : bilibili 账户及凭据管理工具
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import Annotated

from nonebot.log import logger
from nonebot.params import Depends
from nonebot.permission import SUPERUSER
from nonebot.plugin import on_command
from nonebot.rule import to_me

from src.service import OmegaMatcherInterface as OmMI, OmegaMessageSegment, enable_processor_state
from src.utils.bilibili_api import BilibiliCredential


@on_command(
    'bilibili扫码登录',
    rule=to_me(),
    aliases={'Bilibili扫码登录'},
    priority=20,
    block=True,
    permission=SUPERUSER,
    state=enable_processor_state(name='BilibiliQrcodeLogin', enable_processor=False),
).handle()
async def handle_qrcode_login(interface: Annotated[OmMI, Depends(OmMI.depend())]) -> None:
    bc = BilibiliCredential()

    try:
        if await bc.check_valid():
            await interface.finish_reply('bilibili账号已登录, 无需重复登录')
    except Exception as e:
        logger.warning(f'BilibiliQrcodeLogin | 检查登录状态失败, 尝试重新登录, {e}')

    try:
        qrcode_info = await bc.get_login_qrcode()
        qrcode_file = await bc.generate_login_qrcode(qrcode_info=qrcode_info)
        qrcode_msg = OmegaMessageSegment.text('请扫码登录:\n') + OmegaMessageSegment.image(qrcode_file.path)
        await interface.send_reply(qrcode_msg)

        is_login = await bc.login_with_qrcode(qrcode_info=qrcode_info)
        if is_login:
            logger.success('BilibiliQrcodeLogin | 登录成功')
            await interface.send_reply('登录成功')
        else:
            logger.warning('BilibiliQrcodeLogin | 登录失败')
            await interface.send_reply('登录失败, 请稍后重试')
    except Exception as e:
        logger.error(f'BilibiliQrcodeLogin | 登录失败, {e}')
        await interface.send_reply('登录失败, 登录流程中出现异常, 请稍后重试或检查日志处理')


__all__ = []
