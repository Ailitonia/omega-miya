"""
@Author         : Ailitonia
@Date           : 2026/10/18 17:32
@FileName       : __init__.py
@Project        : omega-miya
@Description    : 手动导入邮箱账号工具(仅支持 IMAP)
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm

用法:
    python bot.py --tool-execute input_email_account

交互式依次输入邮箱 IMAP 服务器地址、邮箱地址、邮箱密码, 通过 IMAP 登录校验后
将账号加密写入数据库 (protocol=imap, port=993), 导入成功后可在会话中使用
/邮箱 绑定 绑定该邮箱。本工具不接受任何命令行参数。

安全说明:
    - 邮箱密码为登录凭据, tty 下输入不回显, 请注意可视环境
    - 非 tty 环境(管道/重定向)从 stdin 按行读取 (依次为服务器地址/邮箱地址/密码),
      可用于脚本化调用, 如:
      printf 'imap.example.com\\nuser@example.com\\npassword\\n' | python bot.py --tool-execute input_email_account
"""

import getpass
import sys

from nonebot.log import logger

if hasattr(sys.stdout, 'reconfigure'):
    # Windows 下 stdout 默认为 GBK 等本地编码, 保证非 ASCII 内容输出到管道/重定向时编码一致
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stdin is not None and not sys.stdin.isatty() and hasattr(sys.stdin, 'reconfigure'):
    # 管道/重定向输入同样统一为 utf-8, 避免非 ASCII 参数按本地编码误解码
    sys.stdin.reconfigure(encoding='utf-8')


def _prompt(text: str, *, secret: bool = False) -> str:
    """交互式读入一行输入

    secret 且 stdin 为 tty 时使用 getpass 不回显输入; 否则提示语写入 stderr 后从 stdin 读取一行,
    非 tty 环境(管道/重定向)按行读取可用于脚本化调用
    """
    if secret and sys.stdin is not None and sys.stdin.isatty():
        try:
            return getpass.getpass(text)
        except (EOFError, OSError):
            return ''

    if sys.stderr is not None:
        # 提示语无尾随换行, 必须显式 flush, 否则行/块缓冲的 stderr 会将提示语滞留到进程退出才输出
        sys.stderr.write(text)
        sys.stderr.flush()
    if sys.stdin is None:
        return ''
    try:
        return sys.stdin.readline().rstrip('\r\n')
    except OSError:
        return ''


async def main(*args: str) -> None:
    """手动导入邮箱账号: 交互式读入 -> 解析 -> 校验 -> 落库"""
    from src.plugins.omega_email.helpers import check_mailbox, is_valid_email_address, save_mailbox_into_database

    if args:
        raise ValueError('本工具所有参数均为交互式输入, 不接受命令行参数')

    server_host = _prompt('请输入邮箱IMAP服务器地址: ').strip()
    if not server_host:
        raise ValueError('未输入有效的IMAP服务器地址')

    address = _prompt('请输入邮箱地址: ').strip()
    if not is_valid_email_address(address):
        raise ValueError(f'非法的邮箱地址: {address!r}')

    password = _prompt('请输入邮箱密码: ', secret=True)
    if not password:
        raise ValueError('未输入有效的邮箱密码')

    try:
        check_result = await check_mailbox(address=address, server_host=server_host, password=password)
    except Exception as e:
        logger.error(f'添加邮箱: {address} 失败, 邮箱验证异常, {e}')
        raise
    if not check_result:
        logger.error(f'添加邮箱: {address} 失败, 邮箱验证未通过')
        raise RuntimeError('邮箱验证未通过')

    try:
        await save_mailbox_into_database(
            address=address,
            server_host=server_host,
            password=password,
            protocol='imap',
            port=993,
        )
        logger.success(f'添加邮箱: {address} 成功, 可在会话中使用 /邮箱 绑定 该邮箱')
    except Exception as e:
        logger.error(f'添加邮箱: {address} 失败, 数据库写入失败, {e}')
        raise


__all__ = [
    'main',
]
