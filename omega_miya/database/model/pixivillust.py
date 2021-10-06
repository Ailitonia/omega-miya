from typing import List, Optional
from omega_miya.database.database import BaseDB
from omega_miya.database.class_result import Result
from omega_miya.database.tables import Pixiv, PixivPage
from datetime import datetime
from sqlalchemy.future import select
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from sqlalchemy.sql.expression import func
from sqlalchemy import or_


class DBPixivillust(object):
    def __init__(self, pid: int):
        self.pid = pid

    async def id(self) -> Result.IntResult:
        async_session = BaseDB().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    session_result = await session.execute(
                        select(Pixiv.id).where(Pixiv.pid == self.pid)
                    )
                    pixiv_table_id = session_result.scalar_one()
                    result = Result.IntResult(error=False, info='Success', result=pixiv_table_id)
                except NoResultFound:
                    result = Result.IntResult(error=True, info='NoResultFound', result=-1)
                except MultipleResultsFound:
                    result = Result.IntResult(error=True, info='MultipleResultsFound', result=-1)
                except Exception as e:
                    result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result

    async def exist(self) -> bool:
        result = await self.id()
        return result.success()

    async def add(
            self,
            uid: int, title: str, uname: str, nsfw_tag: int, width: int, height: int, tags: List[str], url: str,
            *,
            force_tag: bool = False
    ) -> Result.IntResult:
        tag_text = ','.join(tags)
        # 将作品信息写入pixiv_illust表
        async_session = BaseDB().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    try:
                        session_result = await session.execute(
                            select(Pixiv).where(Pixiv.pid == self.pid)
                        )
                        exist_illust = session_result.scalar_one()
                        exist_illust.title = title
                        exist_illust.uname = uname
                        if force_tag:
                            exist_illust.nsfw_tag = nsfw_tag
                        elif nsfw_tag > exist_illust.nsfw_tag:
                            exist_illust.nsfw_tag = nsfw_tag
                        exist_illust.width = width
                        exist_illust.height = height
                        exist_illust.tags = tag_text
                        exist_illust.updated_at = datetime.now()
                        result = Result.IntResult(error=False, info='Exist illust updated', result=0)
                    except NoResultFound:
                        new_illust = Pixiv(pid=self.pid, uid=uid, title=title, uname=uname, url=url, nsfw_tag=nsfw_tag,
                                           width=width, height=height, tags=tag_text, created_at=datetime.now())
                        session.add(new_illust)
                        result = Result.IntResult(error=False, info='Success added', result=0)
                await session.commit()
            except MultipleResultsFound:
                await session.rollback()
                result = Result.IntResult(error=True, info='MultipleResultsFound', result=-1)
            except Exception as e:
                await session.rollback()
                result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result

    async def upgrade_page(
            self,
            page: int,
            original: str,
            regular: str,
            small: str,
            thumb_mini: str
    ) -> Result.IntResult:
        pixiv_id_result = await self.id()
        if pixiv_id_result.error:
            return Result.IntResult(error=True, info='PixivIllust not exist', result=-1)

        async_session = BaseDB().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    try:
                        session_result = await session.execute(
                            select(PixivPage).
                            where(PixivPage.page == page).
                            where(PixivPage.illust_id == pixiv_id_result.result)
                        )
                        # 已存在, 更新信息
                        exist_page = session_result.scalar_one()
                        exist_page.original = original
                        exist_page.regular = regular
                        exist_page.small = small
                        exist_page.thumb_mini = thumb_mini
                        exist_page.updated_at = datetime.now()
                        result = Result.IntResult(error=False, info='Success upgraded', result=0)
                    except NoResultFound:
                        new_page = PixivPage(illust_id=pixiv_id_result.result, page=page,
                                             original=original, regular=regular, small=small, thumb_mini=thumb_mini,
                                             created_at=datetime.now())
                        session.add(new_page)
                        result = Result.IntResult(error=False, info='Success added', result=0)
                await session.commit()
            except MultipleResultsFound:
                await session.rollback()
                result = Result.IntResult(error=True, info='MultipleResultsFound', result=-1)
            except Exception as e:
                await session.rollback()
                result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result

    async def get_page(self, page: int = 0) -> Result.TextTupleResult:
        """
        :param page: 页码
        :return: Result: Tuple[original, regular, small, thumb_mini]
        """
        pixiv_id_result = await self.id()
        if pixiv_id_result.error:
            return Result.TextTupleResult(error=True, info='PixivIllust not exist', result=('', '', '', ''))

        async_session = BaseDB().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    session_result = await session.execute(
                        select(PixivPage.original, PixivPage.regular, PixivPage.small, PixivPage.thumb_mini).
                        where(PixivPage.page == page).
                        where(PixivPage.illust_id == pixiv_id_result.result)
                    )
                    original, regular, small, thumb_mini = session_result.one()
                    result = Result.TextTupleResult(error=False, info='Success',
                                                    result=(original, regular, small, thumb_mini))
                except NoResultFound:
                    result = Result.TextTupleResult(error=True, info='NoResultFound', result=('', '', '', ''))
                except MultipleResultsFound:
                    result = Result.TextTupleResult(error=True, info='MultipleResultsFound', result=('', '', '', ''))
                except Exception as e:
                    result = Result.TextTupleResult(error=True, info=repr(e), result=('', '', '', ''))
        return result

    async def get_all_page(self) -> Result.ListResult:
        """
        :return: Result: List[Tuple[page, original, regular, small, thumb_mini]]
        """
        pixiv_id_result = await self.id()
        if pixiv_id_result.error:
            return Result.ListResult(error=True, info='PixivIllust not exist', result=[])

        async_session = BaseDB().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    session_result = await session.execute(
                        select(PixivPage.page,
                               PixivPage.original, PixivPage.regular, PixivPage.small, PixivPage.thumb_mini).
                        where(PixivPage.illust_id == pixiv_id_result.result)
                    )
                    res = [(x[0], x[1], x[2], x[3], x[4]) for x in session_result.all()]
                    result = Result.ListResult(error=False, info='Success', result=res)
                except Exception as e:
                    result = Result.ListResult(error=True, info=repr(e), result=[])
        return result

    @classmethod
    async def rand_illust(cls, num: int, nsfw_tag: int, *, ratio: Optional[int] = None) -> Result.ListResult:
        """
        随机抽取图库中的作品
        :param num: 抽取数量
        :param nsfw_tag: nsfw标签
        :param ratio: 图片长宽, 1: 横图, -1: 纵图, 0: 正方形图
        :return: ListResult, pid列表
        """
        async_session = BaseDB().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    if ratio is None:
                        query = select(Pixiv.pid).where(Pixiv.nsfw_tag == nsfw_tag).order_by(func.random()).limit(num)
                    elif ratio < 0:
                        query = (select(Pixiv.pid).
                                 where(Pixiv.nsfw_tag == nsfw_tag).
                                 where(Pixiv.width < Pixiv.height).
                                 order_by(func.random()).limit(num))
                    elif ratio > 0:
                        query = (select(Pixiv.pid).
                                 where(Pixiv.nsfw_tag == nsfw_tag).
                                 where(Pixiv.width > Pixiv.height).
                                 order_by(func.random()).limit(num))
                    else:
                        query = (select(Pixiv.pid).
                                 where(Pixiv.nsfw_tag == nsfw_tag).
                                 where(Pixiv.width == Pixiv.height).
                                 order_by(func.random()).limit(num))
                    session_result = await session.execute(query)
                    res = [x for x in session_result.scalars().all()]
                    result = Result.ListResult(error=False, info='Success', result=res)
                except Exception as e:
                    result = Result.ListResult(error=True, info=repr(e), result=[])
        return result

    @classmethod
    async def status(cls) -> Result.DictResult:
        async_session = BaseDB().get_async_session()
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
                    result = Result.DictResult(error=False, info='Success', result=res)
                except Exception as e:
                    result = Result.DictResult(error=True, info=repr(e), result={})
        return result

    @classmethod
    async def count_keywords(cls, keywords: List[str]) -> Result.DictResult:
        async_session = BaseDB().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    # 构造查询, 模糊搜索标题, 用户和tag
                    query = select(func.count(Pixiv.id))
                    for keyword in keywords:
                        query = query.where(or_(
                            Pixiv.tags.ilike(f'%{keyword}%'),
                            Pixiv.uname.ilike(f'%{keyword}%'),
                            Pixiv.title.ilike(f'%{keyword}%')
                        ))
                    session_all_result = await session.execute(query)
                    all_count = session_all_result.scalar()

                    session_moe_result = await session.execute(query.where(Pixiv.nsfw_tag == 0))
                    moe_count = session_moe_result.scalar()

                    session_setu_result = await session.execute(query.where(Pixiv.nsfw_tag == 1))
                    setu_count = session_setu_result.scalar()

                    session_r18_result = await session.execute(query.where(Pixiv.nsfw_tag == 2))
                    r18_count = session_r18_result.scalar()

                    res = {'total': int(all_count), 'moe': int(moe_count),
                           'setu': int(setu_count), 'r18': int(r18_count)}
                    result = Result.DictResult(error=False, info='Success', result=res)
                except Exception as e:
                    result = Result.DictResult(error=True, info=repr(e), result={})
        return result

    @classmethod
    async def list_illust(
            cls, keywords: List[str], num: int, nsfw_tag: int, acc_mode: bool = False) -> Result.ListResult:
        async_session = BaseDB().get_async_session()
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
                        query = query.order_by(func.random()).limit(num)
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
                        query = query.order_by(func.random()).limit(num)
                        session_result = await session.execute(query)
                        res = [x for x in session_result.scalars().all()]

                    result = Result.ListResult(error=False, info='Success', result=res)
                except Exception as e:
                    result = Result.ListResult(error=True, info=repr(e), result=[])
        return result

    @classmethod
    async def list_all_illust(cls) -> Result.IntListResult:
        async_session = BaseDB().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    session_result = await session.execute(select(Pixiv.pid))
                    res = [x for x in session_result.scalars().all()]
                    result = Result.IntListResult(error=False, info='Success', result=res)
                except Exception as e:
                    result = Result.IntListResult(error=True, info=repr(e), result=[])
        return result

    @classmethod
    async def list_all_illust_by_nsfw_tag(cls, nsfw_tag: int) -> Result.IntListResult:
        async_session = BaseDB().get_async_session()
        async with async_session() as session:
            async with session.begin():
                try:
                    session_result = await session.execute(select(Pixiv.pid).where(Pixiv.nsfw_tag == nsfw_tag))
                    res = [x for x in session_result.scalars().all()]
                    result = Result.IntListResult(error=False, info='Success', result=res)
                except Exception as e:
                    result = Result.IntListResult(error=True, info=repr(e), result=[])
        return result

    @classmethod
    async def reset_all_nsfw_tag(cls) -> Result.IntResult:
        async_session = BaseDB().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    session_result = await session.execute(select(Pixiv.pid))
                    res = [x for x in session_result.scalars().all()]
                    for pid in res:
                        # print(f'reset nsfw tag: {pid}')
                        session_result = await session.execute(
                            select(Pixiv).where(Pixiv.pid == pid)
                        )
                        exist_illust = session_result.scalar_one()
                        exist_illust.nsfw_tag = 0
                    result = Result.IntResult(error=False, info='Exist illust updated', result=0)
                await session.commit()
            except Exception as e:
                await session.rollback()
                result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result

    @classmethod
    async def set_nsfw_tag(cls, tags: dict) -> Result.IntResult:
        """
        :param tags: Dict[pid: int, nsfw_tag: int]
        :return:
        """
        async_session = BaseDB().get_async_session()
        async with async_session() as session:
            try:
                async with session.begin():
                    for pid, nsfw_tag in tags.items():
                        # print(f'set nsfw tag: {pid}, {nsfw_tag}')
                        nsfw_tag = str(nsfw_tag)
                        session_result = await session.execute(
                            select(Pixiv).where(Pixiv.pid == pid)
                        )
                        exist_illust = session_result.scalar_one()
                        exist_illust.nsfw_tag = nsfw_tag
                    result = Result.IntResult(error=False, info='Exist illust updated', result=0)
                await session.commit()
            except Exception as e:
                await session.rollback()
                result = Result.IntResult(error=True, info=repr(e), result=-1)
        return result
