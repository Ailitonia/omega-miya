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
    from collections.abc import AsyncIterator, Sequence

    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from src.database import ArtworkCollectionDAL
    from src.resource import TemporaryResource

_CHUNK_SIZE = 500
"""导入队列的最大缓冲记录数 (背压阈值)"""

_BULK_BATCH_SIZE = 1000
"""MySQL 批量导入时每批记录数"""

_IMPORT_CONCURRENCY = 8
"""导入并发数 (MySQL/PostgreSQL 后端); sqlite 后端自动降为 1"""

_PROGRESS_INTERVAL = 10000
"""每处理多少条记录输出一次进度日志"""

_MAX_CONSECUTIVE_FAILURES = 50
"""连续失败阈值, 超过则判定为系统性故障并中止导入"""

_MAX_RETRY_TIMES = 5
"""单条记录导入失败时的最大尝试次数

并发导入下存在瞬态竞争 (InnoDB 死锁检测回滚整个事务导致会话 SAVEPOINT 失效等),
单条记录的事务具有原子性且导入幂等, 退避后换新会话重试即可成功
"""

_RETRY_BACKOFF_SECONDS = 0.5
"""重试退避基数, 按 2 的幂增长 (0.5s/1s/2s/4s), 避开同一竞争窗口"""


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

    @field_validator('title')
    @classmethod
    def _truncate_title(cls, value: str, info: ValidationInfo) -> str:
        item_desc = f'Artwork(origin={info.data.get("origin")}, aid={info.data.get("aid")})'
        return _truncate_to_v2_limit('Artwork.title', value, max_length=255, item_desc=item_desc)

    @field_validator('uname')
    @classmethod
    def _truncate_uname(cls, value: str, info: ValidationInfo) -> str:
        item_desc = f'Artwork(origin={info.data.get("origin")}, aid={info.data.get("aid")})'
        return _truncate_to_v2_limit('Artwork.uname', value, max_length=255, item_desc=item_desc)


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


def _normalize_item_tags(item: ArtworkV1) -> tuple[str, list[str]]:
    """解析 v1 tags 并归一化为 (raw_tags 逗号串, 小写标签列表), 每记录只需调用一次

    标签名截断至 v2 artwork_tag.tag_name 长度限制 255, 超长截断并告警;
    raw_tags 保留原始大小写 (与 DAL 写入约定一致), 关联标签列表小写归一化 (与 DAL `_parse_raw_tags` 一致)
    """
    item_desc = f'Artwork(origin={item.origin}, aid={item.aid})'
    normalized_tags = [
        _truncate_to_v2_limit('tag_name', tag, max_length=255, item_desc=item_desc)
        for tag in parse_v1_tags(item.tags)
    ]
    raw_tags = ','.join(tag for tag in normalized_tags if tag)
    lowered_tags = [tag.lower() for tag in normalized_tags if tag]
    return raw_tags, lowered_tags


def _build_raw_tags(item: ArtworkV1) -> str:
    """将 v1 tags 解析结果归一化为 v2 raw_tags 逗号串, 并对超长标签名截断"""
    raw_tags, _ = _normalize_item_tags(item)
    return raw_tags


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


async def _import_one_artwork(item: ArtworkV1, dal: ArtworkCollectionDAL) -> None:
    """将单条 v1 artwork 数据经 DAL 导入 v2 数据库 (已存在则更新, classification/rating 取 max)"""
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


async def _import_one_artwork_with_retry(item: ArtworkV1, session_maker: async_sessionmaker[AsyncSession]) -> None:
    """导入单条记录, 失败时按指数退避换新会话重试 (并发瞬态竞争)"""
    from src.database import ArtworkCollectionDAL

    last_exc: Exception | None = None
    for attempt in range(_MAX_RETRY_TIMES):
        try:
            async with session_maker() as session:
                await _import_one_artwork(item, ArtworkCollectionDAL(session))
                # DAL 写方法仅在会话边界统一提交 (与 database_session 语义一致), 此处需显式提交
                await session.commit()
            return
        except Exception as e:
            last_exc = e
            if attempt + 1 < _MAX_RETRY_TIMES:
                logger.warning(
                    f'Import artwork (origin={item.origin}, aid={item.aid}) attempt {attempt + 1} failed, '
                    f'retrying: {e!r}'
                )
                await asyncio.sleep(_RETRY_BACKOFF_SECONDS * (2 ** attempt))
    assert last_exc is not None
    raise last_exc


async def _import_worker(
        queue: asyncio.Queue[ArtworkV1 | None],
        session_maker: async_sessionmaker[AsyncSession],
        result_counter: Counter[str],
        failed_items: list[ArtworkV1],
) -> None:
    """从队列消费记录并逐条导入, 单条失败仅记录不中断

    不使用 `ArtworkCollectionDAL.create()`: 直接使用底层会话工厂, 每条记录独立会话并显式逐条
    commit, 便于控制失败重试粒度 (单条失败不影响同批次其他记录的提交状态)
    """
    consecutive_failures = 0
    while True:
        item = await queue.get()
        if item is None:
            return

        try:
            await _import_one_artwork_with_retry(item, session_maker)
        except Exception as e:
            result_counter['failed'] += 1
            failed_items.append(item)
            consecutive_failures += 1
            logger.error(f'Failed to import artwork (origin={item.origin}, aid={item.aid}): {e!r}')
            if consecutive_failures >= _MAX_CONSECUTIVE_FAILURES:
                raise RuntimeError(
                    f'Artwork data import aborted: {consecutive_failures} consecutive failures, '
                    f'likely a systemic problem, please check database connection and configuration'
                )
        else:
            result_counter['imported'] += 1
            consecutive_failures = 0


def _build_artwork_row(item: ArtworkV1, raw_tags: str) -> dict[str, Any]:
    """构造 v2 artwork_collection 行数据 (列语义与 DAL 写入约定一致)"""
    from src.database import ArtworkCollectionDAL

    return {
        'origin': item.origin,
        'aid': item.aid,
        'uid': item.uid,
        'title': item.title,
        'uname': item.uname,
        'classification': item.classification,
        'rating': item.rating,
        'width': item.width,
        'height': item.height,
        'orientation': ArtworkCollectionDAL._calc_orientation(item.width, item.height),
        # v2 url 列语义与其自身写入约定 (url := source) 一致
        'url': item.source or '',
        'source': item.source,
        'cover_page': item.cover_page,
        'raw_tags': raw_tags,
        'description': item.description,
    }


async def _flush_bulk_batch(
        session: AsyncSession, batch: Sequence[ArtworkV1], tag_id_map: dict[str, int],
) -> dict[str, int]:
    """批量写入一批记录 (单事务, 方法内不提交): 作品 upsert + 标签确保存在 + 关联插入

    行数据语义与 `ArtworkCollectionDAL.add_artwork_update_exist` 一致 (classification/rating 取 max,
    nullable 字段仅在新值非 None 时更新, 标签小写归一化去重, 关联幂等), 但以多行语句批量执行,
    避免逐标签/逐关联的数据库往返

    与 DAL 的已知差异: DAL 更新已存在作品时会删除并重建 tag 关联, 此处仅增量 INSERT IGNORE 不清理旧关联;
    对"导入全新库"与"自我重跑"均幂等无差异, 但不适用于向已有更完整关联数据的库合并导入

    返回本批新解析出的 {tag_name: tag_id} 映射, 由调用方在事务提交成功后再合并进 tag_id_map,
    避免事务回滚后 map 残留幻影 id 导致后续批次关联插入引用不存在的标签行 (FK 报错)
    """
    from sqlalchemy import func, select, tuple_
    from sqlalchemy.dialects.mysql import insert as mysql_insert

    from src.database.schema import ArtworkCollectionOrm, ArtworkTagOrm, ArtworkWithTagsOrm

    # 0. 每记录解析一次 tags, raw_tags 串与关联标签列表均由该结果派生
    prepared_rows: list[dict[str, Any]] = []
    per_item_tags: list[list[str]] = []
    batch_tags: dict[str, None] = {}
    for item in batch:
        raw_tags, item_tags = _normalize_item_tags(item)
        prepared_rows.append(_build_artwork_row(item, raw_tags))
        per_item_tags.append(item_tags)
        for tag in item_tags:
            batch_tags.setdefault(tag)

    # 1. 作品行 upsert, classification/rating 与库内已有值取 max,
    #    nullable 字段仅在新值非 None 时更新 (均与 DAL 非强制更新语义一致)
    upsert_stmt = mysql_insert(ArtworkCollectionOrm).values(prepared_rows)
    upsert_stmt = upsert_stmt.on_duplicate_key_update(
        uid=upsert_stmt.inserted.uid,
        title=upsert_stmt.inserted.title,
        uname=upsert_stmt.inserted.uname,
        classification=func.greatest(ArtworkCollectionOrm.classification, upsert_stmt.inserted.classification),
        rating=func.greatest(ArtworkCollectionOrm.rating, upsert_stmt.inserted.rating),
        width=upsert_stmt.inserted.width,
        height=upsert_stmt.inserted.height,
        orientation=upsert_stmt.inserted.orientation,
        url=upsert_stmt.inserted.url,
        source=func.coalesce(upsert_stmt.inserted.source, ArtworkCollectionOrm.source),
        cover_page=func.coalesce(upsert_stmt.inserted.cover_page, ArtworkCollectionOrm.cover_page),
        raw_tags=func.coalesce(upsert_stmt.inserted.raw_tags, ArtworkCollectionOrm.raw_tags),
        description=func.coalesce(upsert_stmt.inserted.description, ArtworkCollectionOrm.description),
    )
    await session.execute(upsert_stmt)

    # 2. 标签行: 仅插入本批次新出现的标签 (tag_name 唯一索引, INSERT IGNORE 幂等)
    #    解析结果先写入局部 resolved_tags, 由调用方在 commit 成功后合并, 见方法 docstring
    resolved_tags: dict[str, int] = {}
    missing_tags = [tag for tag in batch_tags if tag not in tag_id_map]
    if missing_tags:
        insert_tag_stmt = mysql_insert(ArtworkTagOrm).values(
            [{'tag_name': tag, 'tag_alt_name': None} for tag in missing_tags]
        )
        await session.execute(insert_tag_stmt.prefix_with('IGNORE'))
        select_tag_stmt = select(ArtworkTagOrm.id, ArtworkTagOrm.tag_name).where(
            ArtworkTagOrm.tag_name.in_(missing_tags)
        )
        for tag_id, tag_name in (await session.execute(select_tag_stmt)).all():
            resolved_tags[tag_name] = tag_id
        # utf8mb4_0900_ai_ci 下新标签可能与库内已有标签折叠等价 (如半角/全角片假名) 而被 INSERT IGNORE 跳过,
        # 按名精确查询无法命中返回行, 此时按请求标签名单个查询 (服务端 CI 匹配) 解析其应归属的已有标签 ID
        for tag in missing_tags:
            if tag in resolved_tags:
                continue
            resolve_stmt = select(ArtworkTagOrm.id).where(ArtworkTagOrm.tag_name == tag).limit(1)
            resolved_tag_id = (await session.execute(resolve_stmt)).scalar_one_or_none()
            if resolved_tag_id is None:
                raise RuntimeError(f'Failed to resolve tag {tag!r} after insert, please check database')
            resolved_tags[tag] = resolved_tag_id

    # 3. 回填本批作品的索引 ID
    origin_aid_pairs = [(item.origin, item.aid) for item in batch]
    select_artwork_stmt = select(
        ArtworkCollectionOrm.id, ArtworkCollectionOrm.origin, ArtworkCollectionOrm.aid,
    ).where(tuple_(ArtworkCollectionOrm.origin, ArtworkCollectionOrm.aid).in_(origin_aid_pairs))
    artwork_id_map = {
        (origin, aid): row_id
        for row_id, origin, aid in (await session.execute(select_artwork_stmt)).all()
    }

    # 4. 关联行: 按作品去重, INSERT IGNORE 幂等 (重跑不会产生重复关联)
    available_tag_ids = tag_id_map | resolved_tags
    association_keys: dict[tuple[int, int], None] = {}
    for item, item_tags in zip(batch, per_item_tags, strict=True):
        artwork_index_id = artwork_id_map[(item.origin, item.aid)]
        for tag in item_tags:
            association_keys.setdefault((artwork_index_id, available_tag_ids[tag]))
    if association_keys:
        insert_assoc_stmt = mysql_insert(ArtworkWithTagsOrm).values([
            {'artwork_index_id': artwork_index_id, 'tag_index_id': tag_index_id}
            for artwork_index_id, tag_index_id in association_keys
        ])
        await session.execute(insert_assoc_stmt.prefix_with('IGNORE'))

    return resolved_tags


async def _import_via_bulk(output_file: TemporaryResource, error_counter: Counter[str]) -> None:
    """MySQL 批量导入: 单线程按批多行语句执行, 幂等可重跑"""
    from sqlalchemy import select

    from src.database.connector import get_session_factory
    from src.database.schema import ArtworkTagOrm

    session_maker = get_session_factory()

    async with session_maker() as session:
        result = await session.execute(select(ArtworkTagOrm.id, ArtworkTagOrm.tag_name))
        tag_id_map = {tag_name: tag_id for tag_id, tag_name in result.all()}
    logger.info(f'Loaded {len(tag_id_map)} existing tags into memory')

    imported_count = 0
    progress_mark = 0
    batch: list[ArtworkV1] = []

    async def _flush(records: list[ArtworkV1]) -> None:
        nonlocal imported_count, progress_mark
        last_exc: Exception | None = None
        resolved_tags: dict[str, int] = {}
        for attempt in range(_MAX_RETRY_TIMES):
            try:
                async with session_maker() as session:
                    resolved_tags = await _flush_bulk_batch(session, records, tag_id_map)
                    await session.commit()
            except Exception as e:
                last_exc = e
                if attempt + 1 < _MAX_RETRY_TIMES:
                    logger.warning(f'Bulk batch flush attempt {attempt + 1} failed, retrying: {e!r}')
                    await asyncio.sleep(_RETRY_BACKOFF_SECONDS * (2 ** attempt))
            else:
                # 事务提交成功后再合并新标签映射, 避免回滚后 map 残留幻影 id 污染后续批次
                tag_id_map.update(resolved_tags)
                break
        else:
            raise RuntimeError(f'Bulk batch flush failed after {_MAX_RETRY_TIMES} attempts: {last_exc!r}')

        imported_count += len(records)
        if imported_count - progress_mark >= _PROGRESS_INTERVAL:
            progress_mark = imported_count
            logger.info(f'Artwork data import progress: processed {imported_count} items')

    async for item in stream_load_artworks_from_file(output_file, error_counter):
        batch.append(item)
        if len(batch) >= _BULK_BATCH_SIZE:
            await _flush(batch)
            batch.clear()
    if batch:
        await _flush(batch)

    logger.info(
        f'Artwork data imported, total {imported_count} items, parse skipped {error_counter["parse"]} items'
    )


async def _import_via_dal_per_record(output_file: TemporaryResource, error_counter: Counter[str]) -> None:
    """DAL 逐条导入 (非 MySQL 后端路径): 并发 worker + 重试 + 顺序清扫残余失败"""
    from src.database.config import database_config
    from src.database.connector import get_session_factory

    concurrency = 1 if database_config.database == 'sqlite' else _IMPORT_CONCURRENCY
    result_counter: Counter[str] = Counter()
    progress_mark = 0

    logger.info(f'Artwork data import start, file={output_file}, concurrency={concurrency}')

    session_maker = get_session_factory()
    queue: asyncio.Queue[ArtworkV1 | None] = asyncio.Queue(maxsize=_CHUNK_SIZE * 2)
    failed_items: list[ArtworkV1] = []
    workers = [
        asyncio.create_task(_import_worker(queue, session_maker, result_counter, failed_items))
        for _ in range(concurrency)
    ]

    try:
        async for item in stream_load_artworks_from_file(output_file, error_counter):
            await queue.put(item)

            processed = result_counter['imported'] + result_counter['failed']
            if processed - progress_mark >= _PROGRESS_INTERVAL:
                progress_mark = processed
                logger.info(
                    f'Artwork data import progress: processed {processed} items, '
                    f'failed {result_counter["failed"]} items'
                )
    finally:
        for _ in workers:
            await queue.put(None)
        await asyncio.gather(*workers)

    if failed_items:
        # 并发瞬态竞争导致的残余失败: 顺序重导 (并发 1 下无竞争, 可稳定收敛)
        logger.warning(f'Artwork data import re-importing {len(failed_items)} failed items sequentially')
        for item in failed_items:
            try:
                await _import_one_artwork_with_retry(item, session_maker)
            except Exception as e:
                result_counter['failed_final'] += 1
                logger.error(f'Failed to re-import artwork (origin={item.origin}, aid={item.aid}): {e!r}')
            else:
                result_counter['recovered'] += 1

    logger.info(
        f'Artwork data imported, total {result_counter["imported"] + result_counter["recovered"]} items '
        f'(recovered {result_counter["recovered"]}), '
        f'failed {result_counter["failed_final"]} items, parse skipped {error_counter["parse"]} items'
    )


async def import_artwork_data() -> None:
    """导入 v1 artwork_collection 数据

    MySQL 后端使用批量导入 (多行语句, 分钟级完成); 其他后端使用 DAL 逐条导入
    """
    from src.database.config import database_config

    output_file = gene_output_json_file('artwork_collection')
    error_counter: Counter[str] = Counter()

    if database_config.database == 'mysql':
        await _import_via_bulk(output_file, error_counter)
    else:
        await _import_via_dal_per_record(output_file, error_counter)


async def artwork_main() -> None:
    """导入 v1 artwork_collection 数据入口"""
    await import_artwork_data()
    logger.info('All v1 artwork data import finished')


if __name__ == '__main__':
    nonebot.init(log_level='INFO')

    asyncio.run(artwork_main())
