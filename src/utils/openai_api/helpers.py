"""
@Author         : Ailitonia
@Date           : 2025/2/12 15:39:43
@FileName       : helpers.py
@Project        : omega-miya
@Description    : 本地文件处理
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import base64
from io import BytesIO
from typing import TYPE_CHECKING

import ujson as json
from PIL import Image
from nonebot.utils import run_sync

if TYPE_CHECKING:
    from src.resource import BaseResource


@run_sync
def _base64_encode(content: bytes, *, encoding: str = 'utf-8') -> str:
    return base64.b64encode(content).decode(encoding)


@run_sync
def _convert_image_format(input_image: bytes, format_: str = 'webp') -> bytes:
    with BytesIO(input_image) as input_bf:
        with Image.open(input_bf) as image:
            with BytesIO() as output_bf:
                image.save(output_bf, format=format_)
                content = output_bf.getvalue()
    return content


async def encode_local_audio(audio: 'BaseResource') -> tuple[str, str]:
    """将本地音频文件编码成 base64 格式的 input_audio, 返回 (data, format) 的数组"""
    async with audio.async_open('rb') as af:
        content = await af.read()
    return await _base64_encode(content), audio.suffix.removeprefix('.')


async def encode_local_file(file: 'BaseResource') -> str:
    """将本地文件编码成 base64 格式文本"""
    async with file.async_open('rb') as af:
        content = await af.read()
    return await _base64_encode(content)


async def encode_local_image(image: 'BaseResource', *, convert_format: str | None = None) -> str:
    """将本地图片文件编码成 base64 格式的 image_url"""
    async with image.async_open('rb') as af:
        content = await af.read()

    if convert_format is not None:
        content = await _convert_image_format(content, format_=convert_format)
        format_suffix = convert_format
    else:
        format_suffix = image.suffix.removeprefix('.')

    return f'data:image/{format_suffix};base64,{await _base64_encode(content)}'


async def encode_bytes_image(image_content: bytes, *, convert_format: str = 'webp') -> str:
    """将图片编码成 base64 格式的 image_url"""
    content = await _convert_image_format(image_content, format_=convert_format)
    return f'data:image/{convert_format};base64,{await _base64_encode(content)}'


def fix_broken_generated_json(json_str: str) -> str:
    """Fixes a malformed JSON string by:
        - Removing the last comma and any trailing content.
        - Iterating over the JSON string once to determine and fix unclosed braces or brackets.
        - Ensuring braces and brackets inside string literals are not considered.

    If the original json_str string can be successfully loaded by json.loads(),
    will directly return it without any modification.

    Reference from HippoRAG2:
    https://github.com/OSU-NLP-Group/HippoRAG/blob/b67f86a92fe886b3aa537cc4a92b935171890228/src/hipporag/utils/llm_utils.py#L146C1-L215C20

    :param json_str: The malformed JSON string to be fixed.
    :return: The corrected JSON string.
    """

    def find_unclosed(inner_json_str: str) -> list[str]:
        """Identifies the unclosed braces and brackets in the JSON string.

        :param inner_json_str: The JSON string to analyze.
        :return: A list of unclosed elements in the order they were opened.
        """
        unclosed = []
        inside_string = False
        escape_next = False

        for char in inner_json_str:
            if inside_string:
                if escape_next:
                    escape_next = False
                elif char == '\\':
                    escape_next = True
                elif char == '"':
                    inside_string = False
            else:
                if char == '"':
                    inside_string = True
                elif char in '{[':
                    unclosed.append(char)
                elif char in '}]':
                    if unclosed and ((char == '}' and unclosed[-1] == '{') or (char == ']' and unclosed[-1] == '[')):
                        unclosed.pop()

        return unclosed

    def remove_external_newlines(inner_json_str: str) -> str:
        """移除 JSON 字符串中不在字符串字面量内部的换行符

        :param inner_json_str: 可能包含不规范换行符的 JSON 字符串
        :return: 清理后的 JSON 字符串
        """
        result = []
        inside_string = False  # 标记是否在字符串内部
        escape_next = False  # 标记下一个字符是否被转义

        for char in inner_json_str:
            if inside_string:
                if escape_next:
                    escape_next = False  # 当前字符被转义（包括转义的引号、转义符本身等）
                elif char == '\\':
                    escape_next = True  # 遇到转义符，下一个字符将被转义
                elif char == '"':
                    inside_string = False  # 遇到非转义的引号，字符串结束
                result.append(char)
            else:
                if char == '"':
                    inside_string = True  # 遇到引号，进入字符串
                    result.append(char)
                elif char == '\n':
                    continue  # 外部换行符，跳过不添加
                else:
                    result.append(char)  # 其他外部字符保留

        return ''.join(result)

    try:
        # Try to load the JSON to see if it is valid
        json.loads(json_str)
        return json_str  # Return as-is if valid
    except json.JSONDecodeError:
        pass

    # Step 0: Remove external newlines.
    json_str = remove_external_newlines(json_str)

    # Step 1: Remove trailing content after the last comma.
    last_comma_index = json_str.rfind(',')
    if last_comma_index != -1:
        json_str = json_str[:last_comma_index]

    # Step 2: Identify unclosed braces and brackets.
    unclosed_elements = find_unclosed(json_str)

    # Step 3: Append the necessary closing elements in reverse order of opening.
    closing_map = {'{': '}', '[': ']'}
    for open_char in reversed(unclosed_elements):
        json_str += closing_map[open_char]

    return json_str


__all__ = [
    'encode_local_audio',
    'encode_local_file',
    'encode_local_image',
    'encode_bytes_image',
    'fix_broken_generated_json',
]
