"""
@Author         : Ailitonia
@Date           : 2026/10/3
@FileName       : artwork
@Project        : omega-miya
@Description    : v1 图库数据导入工具, 将 Navicat 导出的 v1 artwork_collection JSON 导入 v2 数据库
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from __future__ import annotations

import ast
import asyncio
import json
from collections import Counter
from typing import TYPE_CHECKING, Any

import nonebot
from nonebot.log import logger
from pydantic import Field, ValidationError, ValidationInfo, field_validator

from .core import _DataModel, _truncate_to_v2_limit, gene_output_json_file

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from src.resource import TemporaryResource

_CHUNK_SIZE = 500
"""每批次并发导入的记录数"""

_IMPORT_CONCURRENCY = 8
"""导入并发数 (MySQL/PostgreSQL 后端); sqlite 后端自动降为 1"""

_PROGRESS_INTERVAL = 10000
"""每处理多少条记录输出一次进度日志"""

_MAX_CONSECUTIVE_FAILURES = 50
"""连续失败阈值, 超过则判定为系统性故障并中止导入"""


class ArtworkV1(_DataModel):
    """v1 artwork_collection 数据 (唯一索引: origin + aid)

    v1 created_at/updated_at 为记录级时间戳, 由 v2 服务端默认值管理, 不导入
    """
    origin: str
    aid: str
    title: str
    uid: str
    uname: str
    classification: int = Field(ge=-2, le=4)
    rating: int = Field(ge=-1, le=3)
    width: int
    height: int
    tags: str | None = None
    description: str | None = None
    source: str | None = None
    cover_page: str | None = None

    @field_validator('origin')
    @classmethod
    def _truncate_origin(cls, value: str, info: ValidationInfo) -> str:
        item_desc = f'Artwork(origin={value!r})'
        return _truncate_to_v2_limit('Artwork.origin', value, max_length=64, item_desc=item_desc)

    @field_validator('aid')
    @classmethod
    def _truncate_aid(cls, value: str, info: ValidationInfo) -> str:
        item_desc = f'Artwork(origin={info.data.get("origin")}, aid={value!r})'
        return _truncate_to_v2_limit('Artwork.aid', value, max_length=64, item_desc=item_desc)

    @field_validator('uid')
    @classmethod
    def _truncate_uid(cls, value: str, info: ValidationInfo) -> str:
        item_desc = f'Artwork(origin={info.data.get("origin")}, aid={info.data.get("aid")})'
        return _truncate_to_v2_limit('Artwork.uid', value, max_length=64, item_desc=item_desc)


def parse_v1_tags(raw_tags: str | None) -> list[str]:
    """解析 v1 artwork_collection.tags 字段, 兼容历史多种存储格式

    - 逗号分隔字符串: ``tag1,tag2,...``
    - JSON 数组字符串: ``'["tag1","tag2",...]'``
    - Python repr 列表字符串: ``"['tag1', 'tag2', ...]"`` (单引号, json.loads 无法解析)
    - 以 ``[`` 开头但无法解析为列表的脏数据 (如首个 tag 恰好带方括号), 退化为逗号切分

    解析结果清洗: 元素转字符串, 去首尾空白, 去空标签, 保序去重
    """
    if raw_tags is None:
        return []

    stripped_tags = raw_tags.strip()
    parsed: Any = None
    if stripped_tags.startswith('['):
        for parser in (json.loads, ast.literal_eval):
            try:
                parsed = parser(stripped_tags)
                break
            except Exception:
                continue
    if not isinstance(parsed, list):
        parsed = stripped_tags.split(',')

    result: list[str] = []
    for tag in parsed:
        tag = str(tag).strip()
        if tag and tag not in result:
            result.append(tag)
    return result


def _build_raw_tags(item: ArtworkV1) -> str:
    """将 v1 tags 解析结果归一化为 v2 raw_tags 逗号串, 并对超长标签名截断

    v2 artwork_tag.tag_name 字段长度限制为 255, 超长截断并告警
    """
    item_desc = f'Artwork(origin={item.origin}, aid={item.aid})'
    parsed_tags = parse_v1_tags(item.tags)
    normalized_tags = [
        _truncate_to_v2_limit('tag_name', tag, max_length=255, item_desc=item_desc) for tag in parsed_tags
    ]
    return ','.join(tag for tag in normalized_tags if tag)


async def stream_load_artworks_from_file(
        output_file: TemporaryResource, error_counter: Counter[str],
) -> AsyncIterator[ArtworkV1]:
    """流式读取 Navicat 导出的 v1 artwork_collection JSON 文件 (pretty-printed JSON 数组), 逐条解析为数据模型

    JSON 字符串内不含字面换行 (控制字符按规范转义), 故按行扫描, 以 '{' 起始行与 '}' 起始行界定记录边界是安全的
    """
    async with output_file.async_open('r', encoding='utf-8') as af:
        record_lines: list[str] | None = None
        async for line in af:
            stripped_line = line.strip()
            if stripped_line == '{':
                record_lines = [line]
            elif record_lines is None:
                continue
            elif stripped_line.startswith('}'):
                # 记录结束行仅取到 '}' 为止, 丢弃数组元素分隔逗号
                record_lines.append(line[:line.index('}') + 1])
                try:
                    item = ArtworkV1.model_validate_json(''.join(record_lines))
                except ValidationError as e:
                    error_counter['parse'] += 1
                    logger.error(f'Failed to parse artwork record: {"".join(record_lines)[:200]}... Error: {e}')
                    record_lines = None
                    continue
                yield item
                record_lines = None
            else:
                record_lines.append(line)


async def _import_one_artwork(item: ArtworkV1) -> None:
    """将单条 v1 artwork 数据经 DAL 导入 v2 数据库 (已存在则更新, classification/rating 取 max)"""
    from src.database import ArtworkCollectionDAL

    async with ArtworkCollectionDAL.create() as dal:
        await dal.add_artwork_update_exist(
            origin=item.origin,
            aid=item.aid,
            uid=item.uid,
            title=item.title,
            uname=item.uname,
            classification=item.classification,
            rating=item.rating,
            width=item.width,
            height=item.height,
            # v2 url 列语义与其自身写入约定 (url := source) 一致
            url=item.source or '',
            source=item.source,
            cover_page=item.cover_page,
            raw_tags=_build_raw_tags(item),
            description=item.description,
        )


async def import_artwork_data() -> None:
    """导入 v1 artwork_collection 数据"""
    from src.database.config import database_config
    from src.utils.process_utils import semaphore_gather

    concurrency = 1 if database_config.database == 'sqlite' else _IMPORT_CONCURRENCY
    error_counter: Counter[str] = Counter()
    imported_count = 0
    failed_count = 0
    consecutive_failures = 0
    progress_mark = 0

    output_file = gene_output_json_file('artwork_collection')
    logger.info(f'Artwork data import start, file={output_file}, concurrency={concurrency}')

    async def _import_chunk(records: list[ArtworkV1]) -> tuple[int, int]:
        """并发导入一批记录, 返回 (成功数, 失败数); 单条失败仅记录不中断"""
        results = await semaphore_gather(
            [_import_one_artwork(x) for x in records], semaphore_num=concurrency, return_exceptions=True
        )
        success_count = 0
        for item_, result in zip(records, results, strict=True):
            if isinstance(result, Exception):
                logger.error(f'Failed to import artwork (origin={item_.origin}, aid={item_.aid}): {result!r}')
            else:
                success_count += 1
        return success_count, len(records) - success_count

    chunk: list[ArtworkV1] = []
    async for item in stream_load_artworks_from_file(output_file, error_counter):
        chunk.append(item)
        if len(chunk) < _CHUNK_SIZE:
            continue

        imported, failed = await _import_chunk(chunk)
        imported_count += imported
        failed_count += failed
        consecutive_failures = consecutive_failures + failed if imported == 0 else 0
        chunk.clear()

        processed = imported_count + failed_count
        if processed - progress_mark >= _PROGRESS_INTERVAL:
            progress_mark = processed
            logger.info(f'Artwork data import progress: processed {processed} items, failed {failed_count} items')

        if consecutive_failures >= _MAX_CONSECUTIVE_FAILURES:
            raise RuntimeError(
                f'Artwork data import aborted: {consecutive_failures} consecutive failures, '
                f'likely a systemic problem, please check database connection and configuration'
            )

    if chunk:
        imported, failed = await _import_chunk(chunk)
        imported_count += imported
        failed_count += failed

    logger.info(
        f'Artwork data imported, total {imported_count} items, '
        f'failed {failed_count} items, parse skipped {error_counter["parse"]} items'
    )


async def artwork_main() -> None:
    """导入 v1 artwork_collection 数据入口"""
    await import_artwork_data()
    logger.info('All v1 artwork data import finished')


if __name__ == '__main__':
    nonebot.init(log_level='INFO')

    asyncio.run(artwork_main())
