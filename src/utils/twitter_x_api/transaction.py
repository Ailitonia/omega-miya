"""
@Author         : Ailitonia
@Date           : 2026/9/27 23:30
@FileName       : transaction
@Project        : omega-miya
@Description    : X-Client-Transaction-Id 计算(移植自 twikit x_client_transaction, HTML 解析改用 lxml)
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import base64
import hashlib
import math
import random
import re
import time
from typing import TYPE_CHECKING

from lxml import etree

from src.utils.omega_requests import OmegaRequests

if TYPE_CHECKING:
    from src.utils.omega_common_api.types import Response

_ON_DEMAND_FILE_REGEX = re.compile(
    r"""['"]ondemand\.s['"]:\s*['"](\w*)['"]""", flags=(re.VERBOSE | re.MULTILINE)
)
"""首页源码中 ondemand.s 脚本文件哈希正则(旧格式)"""

_ON_DEMAND_CHUNK_NAME_REGEX = re.compile(r',(\d+):["\']ondemand\.s["\']')
"""首页源码中 ondemand.s 的 webpack chunk 索引正则(新格式, 文件哈希需另行从 chunk 哈希映射表中查找)"""

_INDICES_REGEX = re.compile(
    r"""(\(\w{1}\[(\d{1,2})],\s*16\))+""", flags=(re.VERBOSE | re.MULTILINE)
)
"""ondemand.s 脚本中 key byte 索引正则"""

_MIGRATION_REDIRECTION_REGEX = re.compile(
    r"""(http(?:s)?://(?:www\.)?(twitter|x)\.com(/x)?/migrate([/?])?tok=[a-zA-Z0-9%\-_]+)+""", flags=re.VERBOSE
)
"""twitter.com 向 x.com 迁移跳转链接正则"""


def _float_to_hex(x: float) -> str:
    """将浮点数转换为十六进制字符串(与浏览器 Number.prototype.toString(16) 行为一致)"""
    result = []
    quotient = int(x)
    fraction = x - quotient

    while quotient > 0:
        quotient = int(x / 16)
        remainder = int(x - (float(quotient) * 16))

        if remainder > 9:
            result.insert(0, chr(remainder + 55))
        else:
            result.insert(0, str(remainder))

        x = float(quotient)

    if fraction == 0:
        return ''.join(result)

    result.append('.')

    while fraction > 0:
        fraction *= 16
        integer = int(fraction)
        fraction -= float(integer)

        if integer > 9:
            result.append(chr(integer + 55))
        else:
            result.append(str(integer))

    return ''.join(result)


def _is_odd(num: float) -> float:
    return -1.0 if num % 2 else 0.0


def _interpolate_num(from_val: float, to_val: float, f: float) -> float:
    return from_val * (1 - f) + to_val * f


def _interpolate(from_list: list[float], to_list: list[float], f: float) -> list[float]:
    if len(from_list) != len(to_list):
        raise ValueError(f'Mismatched interpolation arguments {from_list}: {to_list}')
    return [_interpolate_num(from_list[i], to_list[i], f) for i in range(len(from_list))]


def _convert_rotation_to_matrix(rotation: float) -> list[float]:
    rad = math.radians(rotation)
    return [math.cos(rad), -math.sin(rad), math.sin(rad), math.cos(rad)]


class _Cubic:
    """三次贝塞尔曲线求值"""

    def __init__(self, curves: list[float]) -> None:
        self.curves = curves

    def get_value(self, time_: float) -> float:
        start_gradient = end_gradient = start = mid = 0.0
        end = 1.0

        if time_ <= 0.0:
            if self.curves[0] > 0.0:
                start_gradient = self.curves[1] / self.curves[0]
            elif self.curves[1] == 0.0 and self.curves[2] > 0.0:
                start_gradient = self.curves[3] / self.curves[2]
            return start_gradient * time_

        if time_ >= 1.0:
            if self.curves[2] < 1.0:
                end_gradient = (self.curves[3] - 1.0) / (self.curves[2] - 1.0)
            elif self.curves[2] == 1.0 and self.curves[0] < 1.0:
                end_gradient = (self.curves[1] - 1.0) / (self.curves[0] - 1.0)
            return 1.0 + end_gradient * (time_ - 1.0)

        while start < end:
            mid = (start + end) / 2
            x_est = self.calculate(self.curves[0], self.curves[2], mid)
            if abs(time_ - x_est) < 0.00001:
                return self.calculate(self.curves[1], self.curves[3], mid)
            if x_est < time_:
                start = mid
            else:
                end = mid
        return self.calculate(self.curves[1], self.curves[3], mid)

    @staticmethod
    def calculate(a: float, b: float, m: float) -> float:
        return 3.0 * a * (1 - m) * (1 - m) * m + 3.0 * b * (1 - m) * m * m + m * m * m


def _parse_html(content: str) -> etree._Element:
    """解析 HTML 文本, 解析失败时抛出异常"""
    home_page = etree.HTML(content)
    if home_page is None:
        raise RuntimeError('Parsing home page failed, invalid response content')
    return home_page


def _element_children(element: etree._Element) -> list[etree._Element]:
    """获取元素的子元素节点(过滤注释等非元素节点)"""
    return [child for child in element if isinstance(child.tag, str)]


class ClientTransaction:
    """X-Client-Transaction-Id 计算器

    通过解析 X 首页中的验证 meta 与加载动画 SVG, 结合 ondemand.s 脚本中的索引计算出每次请求的 transaction id
    """

    _ADDITIONAL_RANDOM_NUMBER = 3
    _DEFAULT_KEYWORD = 'obfiowerehiring'

    def __init__(self) -> None:
        self.home_page: etree._Element | None = None
        self.home_page_content: str | None = None
        self.default_row_index: int | None = None
        self.default_key_bytes_indices: list[int] | None = None
        self.key: str | None = None
        self.key_bytes: list[int] | None = None
        self.animation_key: str | None = None

    @property
    def is_initialized(self) -> bool:
        """是否已完成初始化(可生成 transaction id)"""
        return self.animation_key is not None and self.key is not None

    @staticmethod
    def _parse_response_text(response: 'Response') -> str:
        return OmegaRequests.parse_content_as_text(response)

    async def init(self, requester: OmegaRequests) -> None:
        """初始化计算状态, 请求 X 首页并解析出 key 与 animation key"""
        self.home_page = await self._handle_x_migration(requester)
        self.default_row_index, self.default_key_bytes_indices = await self._get_indices(
            requester=requester, home_page=self.home_page
        )
        self.key = self._get_key(home_page=self.home_page)
        self.key_bytes = self._get_key_bytes(key=self.key)
        self.animation_key = self._get_animation_key(key_bytes=self.key_bytes, home_page=self.home_page)

    async def _handle_x_migration(self, requester: OmegaRequests) -> etree._Element:
        """请求 X 首页, 处理 twitter.com 到 x.com 的迁移跳转"""
        response = await requester.get(url='https://x.com')
        content = self._parse_response_text(response)
        home_page = _parse_html(content)

        migration_meta = home_page.xpath('//meta[@http-equiv="refresh"]')
        migration_url_match = None
        if migration_meta:
            migration_url_match = _MIGRATION_REDIRECTION_REGEX.search(
                etree.tostring(migration_meta[0], encoding='unicode')
            )
        if migration_url_match is None:
            migration_url_match = _MIGRATION_REDIRECTION_REGEX.search(content)
        if migration_url_match is not None:
            response = await requester.get(url=migration_url_match.group(0))
            content = self._parse_response_text(response)
            home_page = _parse_html(content)

        migration_form = (
                home_page.xpath('//form[@name="f"]')
                or home_page.xpath('//form[@action="https://x.com/x/migrate"]')
        )
        if migration_form:
            form = migration_form[0]
            url = form.get('action', 'https://x.com/x/migrate') + '/?mx=2'
            request_payload = {field.get('name'): field.get('value') for field in form.xpath('.//input')}
            response = await requester.post(url=url, data=request_payload)
            content = self._parse_response_text(response)
            home_page = _parse_html(content)

        # 保留首页原始源码供 ondemand.s 哈希正则匹配(避免 lxml 序列化改写内容)
        self.home_page_content = content
        return home_page

    @staticmethod
    def _extract_on_demand_file_hash(home_page_content: str) -> str | None:
        """从首页源码中提取 ondemand.s 脚本文件哈希(兼容新旧两种打包格式)"""
        # 旧格式: 'ondemand.s': 'hash'
        if match := _ON_DEMAND_FILE_REGEX.search(home_page_content):
            return match.group(1)
        # 新 webpack chunk 格式: ,123:"ondemand.s" 的 chunk 映射, 再由 ,123:"hash" 的哈希映射表取文件哈希
        if chunk_match := _ON_DEMAND_CHUNK_NAME_REGEX.search(home_page_content):
            chunk_id = chunk_match.group(1)
            hash_pattern = re.compile(rf',{chunk_id}:["\']([0-9a-f]+)["\']')
            if hash_match := hash_pattern.search(home_page_content):
                return hash_match.group(1)
        return None

    async def _get_indices(self, requester: OmegaRequests, home_page: etree._Element) -> tuple[int, list[int]]:
        """从首页引用的 ondemand.s 脚本中提取 key byte 索引"""
        file_hash = self._extract_on_demand_file_hash(self.home_page_content or '')

        key_byte_indices: list[int] = []
        if file_hash:
            on_demand_file_url = f'https://abs.twimg.com/responsive-web/client-web/ondemand.s.{file_hash}a.js'
            response = await requester.get(url=on_demand_file_url)
            js_content = self._parse_response_text(response)
            key_byte_indices = [int(match.group(2)) for match in _INDICES_REGEX.finditer(js_content)]

        if not key_byte_indices:
            raise RuntimeError("Couldn't get KEY_BYTE indices")

        return key_byte_indices[0], key_byte_indices[1:]

    @staticmethod
    def _get_key(home_page: etree._Element) -> str:
        """从首页 meta 中获取 twitter-site-verification 作为 key"""
        elements = home_page.xpath('//meta[@name="twitter-site-verification"]')
        if not elements:
            raise RuntimeError("Couldn't get key from the page source")
        return elements[0].get('content')

    @staticmethod
    def _get_key_bytes(key: str) -> list[int]:
        return list(base64.b64decode(key.encode('utf-8')))

    @staticmethod
    def _get_frames(home_page: etree._Element) -> list[etree._Element]:
        """获取首页中的 loading-x-anim 加载动画 SVG 帧元素"""
        return home_page.xpath('//*[starts-with(@id, "loading-x-anim")]')

    def _get_2d_array(self, key_bytes: list[int], home_page: etree._Element) -> list[list[int]]:
        frames = self._get_frames(home_page)
        # 选取指定帧的第二个 path 元素的 d 属性, 按 "C" 分割并解析为整数二维数组
        target = _element_children(_element_children(frames[key_bytes[5] % 4])[0])[1]
        return [
            [int(x) for x in re.sub(r'[^\d]+', ' ', item).strip().split()]
            for item in target.get('d')[9:].split('C')
        ]

    @staticmethod
    def _solve(value: float, min_val: float, max_val: float, rounding: bool) -> float:
        result = value * (max_val - min_val) / 255 + min_val
        return math.floor(result) if rounding else round(result, 2)

    def _animate(self, frames: list[int], target_time: float) -> str:
        from_color = [float(item) for item in [*frames[:3], 1]]
        to_color = [float(item) for item in [*frames[3:6], 1]]
        from_rotation = [0.0]
        to_rotation = [self._solve(float(frames[6]), 60.0, 360.0, True)]
        frames = frames[7:]
        curves = [self._solve(float(item), _is_odd(counter), 1.0, False) for counter, item in enumerate(frames)]
        cubic = _Cubic(curves)
        val = cubic.get_value(target_time)
        color = _interpolate(from_color, to_color, val)
        color = [value if value > 0 else 0 for value in color]
        rotation = _interpolate(from_rotation, to_rotation, val)
        matrix = _convert_rotation_to_matrix(rotation[0])
        str_arr = [format(round(value), 'x') for value in color[:-1]]
        for value in matrix:
            rounded = round(value, 2)
            if rounded < 0:
                rounded = -rounded
            hex_value = _float_to_hex(rounded)
            str_arr.append(f'0{hex_value}'.lower() if hex_value.startswith('.') else hex_value if hex_value else '0')
        str_arr.extend(['0', '0'])
        return re.sub(r'[.-]', '', ''.join(str_arr))

    def _get_animation_key(self, key_bytes: list[int], home_page: etree._Element) -> str:
        total_time = 4096
        row_index = key_bytes[self.default_row_index] % 16
        frame_time = math.prod([key_bytes[index] % 16 for index in self.default_key_bytes_indices])
        arr = self._get_2d_array(key_bytes=key_bytes, home_page=home_page)
        frame_row = arr[row_index]

        target_time = float(frame_time) / total_time
        return self._animate(frame_row, target_time)

    def generate_transaction_id(
            self,
            method: str,
            path: str,
            *,
            time_now: int | None = None,
    ) -> str:
        """生成 X-Client-Transaction-Id

        :param method: 请求方法
        :param path: 请求路径(不含域名与查询参数)
        :param time_now: 可选, 覆盖计算用时间戳
        """
        if not self.is_initialized:
            raise RuntimeError('ClientTransaction is not initialized')

        if time_now is None:
            time_now = math.floor((time.time() * 1000 - 1682924400 * 1000) / 1000)
        time_now_bytes = [(time_now >> (i * 8)) & 0xFF for i in range(4)]
        key_bytes = self._get_key_bytes(self.key)
        hash_val = hashlib.sha256(
            f'{method}!{path}!{time_now}{self._DEFAULT_KEYWORD}{self.animation_key}'.encode()
        ).digest()
        hash_bytes = list(hash_val)
        random_num = random.randint(0, 255)
        bytes_arr = [*key_bytes, *time_now_bytes, *hash_bytes[:16], self._ADDITIONAL_RANDOM_NUMBER]
        out = bytearray([random_num, *[item ^ random_num for item in bytes_arr]])
        return base64.b64encode(bytes(out)).decode().strip('=')


__all__ = [
    'ClientTransaction',
]
