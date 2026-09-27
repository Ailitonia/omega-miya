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
    """在时间线 instructions 列表中查找指定 type 的条目"""
    for entry in entries:
        if entry.get('type') == type_filter:
            return entry
    return None


def flatten_params(params: dict[str, Any]) -> dict[str, Any]:
    """将 params 中的 dict/list 值序列化为 JSON 字符串(GraphQL 查询参数格式)"""
    import json
    flattened_params = {}
    for key, value in params.items():
        if isinstance(value, (list, dict)):
            value = json.dumps(value)
        flattened_params[key] = value
    return flattened_params


__all__ = [
    'find_dict',
    'find_entry_by_type',
    'flatten_params',
]
