from typing import List
from omega_miya.utils.Omega_Base.database import NBdb, DBResult
from omega_miya.utils.Omega_Base.tables import Pixiv, PixivTag, PixivT2I
from .pixivtag import DBPixivtag
from datetime import datetime
from sqlalchemy.future import select
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from sqlalchemy.sql.expression import func
from sqlalchemy import or_


class DBPixivillust(object):
    def __init__(self, pid: int):
        self.pid = pid

    async def id(self) -> DBResult:
        async_session = NBdb().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    session_result = await session.execute(
                        select(Pixiv.id).where(Pixiv.pid == self.pid)
                    )
                    pixiv_table_id = session_result.scalar_one()
                    result = DBResult(error=False, info='Success', result=pixiv_table_id)
                except NoResultFound:
                    result = DBResult(error=True, info='NoResultFound', result=-1)
                except MultipleResultsFound:
                    result = DBResult(error=True, info='MultipleResultsFound', result=-1)
                except Exception as e:
                    result = DBResult(error=True, info=repr(e), result=-1)
        return result

    async def exist(self) -> bool:
        result = await self.id()
        return result.success()

    async def add(self, uid: int, title: str, uname: str, nsfw_tag: int, tags: List[str], url: str) -> DBResult:
        # 将tag写入pixiv_tag表
        for tag in tags:
            _tag = DBPixivtag(tagname=tag)
            await _tag.add()

        tag_text = ','.join(tags)
        # 将作品信息写入pixiv_illust表
        async_session = NBdb().get_async_session()
        async with async_session() as session:
            try:
                need_upgrade_pixivt2i = False
                async with session.begin():
                    try:
                        session_result = await session.execute(
                            select(Pixiv).where(Pixiv.pid == self.pid)
                        )
                        exist_illust = session_result.scalar_one()
                        exist_illust.title = title
                        exist_illust.uname = uname
                        if nsfw_tag > exist_illust.nsfw_tag:
                            exist_illust.nsfw_tag = nsfw_tag
                        exist_illust.tags = tag_text
                        exist_illust.updated_at = datetime.now()
                        result = DBResult(error=False, info='Exist illust updated', result=0)
                    except NoResultFound:
                        new_illust = Pixiv(pid=self.pid, uid=uid, title=title, uname=uname, url=url, nsfw_tag=nsfw_tag,
                                           tags=tag_text, created_at=datetime.now())
                        session.add(new_illust)
                        need_upgrade_pixivt2i = True
                        result = DBResult(error=False, info='Success added', result=0)
                await session.commit()

                # 写入tag_pixiv关联表
                # 获取本作品在illust表中的id
                id_result = await self.id()
                if id_result.success() and need_upgrade_pixivt2i:
                    _illust_id = id_result.result
                    # 根据作品tag依次写入tag_illust表
                    async with session.begin():
                        for tag in tags:
                            _tag = DBPixivtag(tagname=tag)
                            _tag_id_res = await _tag.id()
                            if not _tag_id_res.success():
                                continue
                            _tag_id = _tag_id_res.result
                            try:
                                new_tag_illust = PixivT2I(illust_id=_illust_id, tag_id=_tag_id,
                                                          created_at=datetime.now())
                                session.add(new_tag_illust)
                            except Exception as e:
                                continue
                    await session.commit()
                    result = DBResult(error=False, info='Success added with tags', result=0)
            except MultipleResultsFound:
                await session.rollback()
                result = DBResult(error=True, info='MultipleResultsFound', result=-1)
            except Exception as e:
                await session.rollback()
                result = DBResult(error=True, info=repr(e), result=-1)
        return result

    @classmethod
    async def rand_illust(cls, num: int, nsfw_tag: int) -> DBResult:
        async_session = NBdb().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    session_result = await session.execute(
                        select(Pixiv.pid).
                        where(Pixiv.nsfw_tag == nsfw_tag).
                        order_by(func.random()).limit(num)
                    )
                    res = [x for x in session_result.scalars().all()]
                    result = DBResult(error=False, info='Success', result=res)
                except Exception as e:
                    result = DBResult(error=True, info=repr(e), result=[])
        return result

    @classmethod
    async def status(cls) -> DBResult:
        async_session = NBdb().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    session_result = await session.execute(select(func.count(Pixiv.id)))
                    all_count = session_result.scalar()
                    session_result = await session.execute(select(func.count(Pixiv.id)).where(Pixiv.nsfw_tag == 0))
                    moe_count = session_result.scalar()
                    session_result = await session.execute(select(func.count(Pixiv.id)).where(Pixiv.nsfw_tag == 1))
                    setu_count = session_result.scalar()
                    session_result = await session.execute(select(func.count(Pixiv.id)).where(Pixiv.nsfw_tag == 2))
                    r18_count = session_result.scalar()
                    res = {'total': int(all_count), 'moe': int(moe_count),
                           'setu': int(setu_count), 'r18': int(r18_count)}
                    result = DBResult(error=False, info='Success', result=res)
                except Exception as e:
                    result = DBResult(error=True, info=repr(e), result={})
        return result

    @classmethod
    async def list_illust(cls, *keywords: str, nsfw_tag: int, acc_mode: bool) -> DBResult:
        async_session = NBdb().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    if acc_mode:
                        # 构造查询, 精确搜索标题, 用户和tag
                        query = select(Pixiv.pid).where(Pixiv.nsfw_tag == nsfw_tag)
                        for keyword in keywords:
                            query = query.where(or_(
                                func.find_in_set(keyword, Pixiv.tags),
                                func.find_in_set(keyword, Pixiv.uname),
                                func.find_in_set(keyword, Pixiv.title)
                            ))
                        query = query.order_by(func.random())
                        session_result = await session.execute(query)
                        res = [x for x in session_result.scalars().all()]

                    if not acc_mode or (acc_mode and not res):
                        # 构造查询, 模糊搜索标题, 用户和tag
                        query = select(Pixiv.pid).where(Pixiv.nsfw_tag == nsfw_tag)
                        for keyword in keywords:
                            query = query.where(or_(
                                Pixiv.tags.ilike(f'%{keyword}%'),
                                Pixiv.uname.ilike(f'%{keyword}%'),
                                Pixiv.title.ilike(f'%{keyword}%')
                            ))
                        query = query.order_by(func.random())
                        session_result = await session.execute(query)
                        res = [x for x in session_result.scalars().all()]

                    result = DBResult(error=False, info='Success', result=res)
                except Exception as e:
                    result = DBResult(error=True, info=repr(e), result=[])
        return result
