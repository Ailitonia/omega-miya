"""
@Author         : Ailitonia
@Date           : 2026/10/12 18:39
@FileName       : __init__.py
@Project        : omega-miya
@Description    : 手动导入 bilibili 登录状态 Cookies 工具
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm

用法:
    python bot.py --tool-execute input_bilibili_cookies

交互式粘贴浏览器 Cookie 头中的 cookies 字符串 (形如 "SESSDATA=xxx; bili_jct=yyy; ...",
支持携带 "Cookie: " 前缀), 解析后调用 bilibili API 校验登录态, 校验通过则全量重建写入数据库
(上一代凭据及 refresh_token 等残留一并清除, 与扫码登录落库语义一致)。

安全说明:
    - cookies 字符串包含登录凭据 (SESSDATA 等效账号密码), tty 下输入不回显, 请注意可视环境
    - 非 tty 环境(管道/重定向)从 stdin 按行读取, 可用于脚本化调用, 如:
      printf 'SESSDATA=xxx; bili_jct=yyy;\\n' | python bot.py --tool-execute input_bilibili_cookies
"""

import getpass
import sys

from nonebot.log import logger

from src.utils.bilibili_api import BilibiliCredential
from src.utils.bilibili_api.credential_manager import BILIBILI_CREDENTIAL_MANAGER, BilibiliCookiesData

if hasattr(sys.stdout, 'reconfigure'):
    # Windows 下 stdout 默认为 GBK 等本地编码, 保证非 ASCII 内容输出到管道/重定向时编码一致
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stdin is not None and not sys.stdin.isatty() and hasattr(sys.stdin, 'reconfigure'):
    # 管道/重定向输入同样统一为 utf-8, 避免非 ASCII 参数按本地编码误解码
    sys.stdin.reconfigure(encoding='utf-8')

_ESSENTIAL_COOKIE_KEYS = ('SESSDATA', 'bili_jct', 'DedeUserID')
"""登录态校验所必需的 Cookie 键"""


def _parse_cookies_string(raw: str) -> dict[str, str]:
    """解析 Cookie 头字符串, 跳过空段与无 '=' 的非法段, 值中允许含 '='"""
    raw = raw.strip()
    if raw.lower().startswith('cookie:'):
        raw = raw[len('cookie:'):]

    cookies = {}
    for item in raw.split(';'):
        key, sep, value = item.partition('=')
        if sep and key.strip():
            cookies[key.strip()] = value.strip()
    return cookies


def _prompt_cookies() -> str:
    """交互式读入一行 cookies 字符串

    stdin 为 tty 时使用 getpass 不回显输入; 否则提示语写入 stderr 后从 stdin 读取一行,
    非 tty 环境(管道/重定向)按行读取可用于脚本化调用
    """
    if sys.stdin is not None and sys.stdin.isatty():
        try:
            return getpass.getpass('Input cookies string (no echo): ')
        except (EOFError, OSError):
            return ''

    if sys.stderr is not None:
        # 提示语无尾随换行, 必须显式 flush, 否则行/块缓冲的 stderr 会将提示语滞留到进程退出才输出
        sys.stderr.write('Input cookies string: ')
        sys.stderr.flush()
    if sys.stdin is None:
        return ''
    try:
        return sys.stdin.readline().rstrip('\r\n')
    except OSError:
        return ''


async def main(*args: str) -> None:
    """手动导入 bilibili 登录状态 Cookies: 交互式读入 -> 解析 -> 校验 -> 全量重建落库"""
    if args:
        raise ValueError('本工具所有参数均为交互式输入, 不接受命令行参数')

    cookies_dict = _parse_cookies_string(_prompt_cookies())
    if not cookies_dict:
        logger.error('未解析到任何有效 Cookie 键值对, 输入应为 "SESSDATA=xxx; bili_jct=yyy; ..." 格式')
        sys.exit(1)

    known_keys = {field.alias or name for name, field in BilibiliCookiesData.model_fields.items()}
    if unknown_keys := sorted(set(cookies_dict) - known_keys):
        logger.warning(f'以下 Cookie 键无法识别, 将被忽略: {", ".join(unknown_keys)}')
    if missing_keys := [key for key in _ESSENTIAL_COOKIE_KEYS if key not in cookies_dict]:
        logger.warning(f'缺少登录态必需的 Cookie 键: {", ".join(missing_keys)}, 校验可能失败')

    BILIBILI_CREDENTIAL_MANAGER.update_cookies(**cookies_dict)

    if not await BilibiliCredential.check_valid():
        logger.error('Cookies 校验未通过, 凭据未保存')
        sys.exit(1)

    await BILIBILI_CREDENTIAL_MANAGER.rebuild_to_database()
    logger.success('Cookies 校验通过, 已全量重建并写入数据库')


__all__ = [
    'main',
]
