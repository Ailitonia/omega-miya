"""
@Author         : Ailitonia
@Date           : 2026/9/27 23:30
@FileName       : misc
@Project        : omega-miya
@Description    : Twitter API 杂项辅助函数
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import ujson


def find_dict(obj: list | dict, key: str | int, find_one: bool = False) -> list[Any]:
    """在嵌套字典/列表中递归查找指定键的所有值

    :param obj: 待查找的嵌套字典/列表
    :param key: 目标键
    :param find_one: 找到首个匹配后立即返回
    :return: 匹配到的值列表
    """
    results = []
    if isinstance(obj, dict):
        if key in obj:
            results.append(obj.get(key))
            if find_one:
                return results
    if isinstance(obj, (list, dict)):
        for elem in (obj if isinstance(obj, list) else obj.values()):
            r = find_dict(elem, key, find_one)
            results += r
            if r and find_one:
                return results
    return results


def find_entry_by_type(entries: list[dict], type_filter: str) -> dict | None:
    """在时间线 instructions 列表中查找指定 type 的条目

    入参畸形(非 list/含非 dict 条目)时返回 None
    """
    if not isinstance(entries, list):
        return None
    for entry in entries:
        if isinstance(entry, dict) and entry.get('type') == type_filter:
            return entry
    return None


def flatten_params(params: dict[str, Any]) -> dict[str, Any]:
    """将 params 中的 dict/list 值序列化为 JSON 字符串(GraphQL 查询参数格式)"""
    flattened_params = {}
    for key, value in params.items():
        if isinstance(value, (list, dict)):
            value = ujson.dumps(value)
        flattened_params[key] = value
    return flattened_params


def orig_image_url(url: str) -> str:
    """将 Twitter 图片链接转换为原图链接(?name=orig 形式)

    仅处理 pbs.twimg.com 的 /media/ 图片链接, 其余链接原样返回;
    兼容 ?name=xxx 查询参数与 :orig 等 legacy 后缀两种形式, 保留 format 等其他查询参数
    """
    parts = urlsplit(url)
    if parts.netloc.lower() != 'pbs.twimg.com' or not parts.path.startswith('/media/'):
        return url
    path = parts.path.rsplit(':', maxsplit=1)[0]  # 剥离 :orig 等 legacy 后缀
    query = [('name', 'orig') if k == 'name' else (k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)]
    if all(k != 'name' for k, _ in query):
        query.append(('name', 'orig'))
    return urlunsplit((parts.scheme, parts.netloc, path, urlencode(query), parts.fragment))


__all__ = [
    'find_dict',
    'find_entry_by_type',
    'flatten_params',
    'orig_image_url',
]
