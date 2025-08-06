"""
@Author         : Ailitonia
@Date           : 2025/6/3 16:08:32
@FileName       : manager.py
@Project        : omega-miya
@Description    : 订阅源管理类
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import abc
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, ClassVar, Literal, Self

from nonebot.exception import ActionFailed
from nonebot.log import logger
from sqlalchemy.exc import NoResultFound

from src.database import EntityDAL, SocialMediaContentDAL, SubscriptionSourceDAL, begin_db_session
from src.service import OmegaEntity, OmegaMessage, OmegaMessageSegment
from src.service import OmegaEntityInterface as OmEI
from src.service import OmegaMatcherInterface as OmMI
from src.utils import semaphore_gather

if TYPE_CHECKING:
    from src.database.internal.entity import Entity
    from src.database.internal.social_media_content import SocialMediaContent
    from src.database.internal.subscription_source import SubscriptionSource
    from src.service.omega_base.middlewares.models import SentMessageResponse


class BaseSubscriptionManager[SMC_T: Any](abc.ABC):
    """订阅服务管理基类(SMC: SubscriptionMainContent 订阅源内容)"""

    _SETTING_NODE_NOTICE_AT_ALL: ClassVar[Literal['notice_at_all']] = 'notice_at_all'
    """添加插件配置时的通知@全体的节点名称"""
    _LIMIT_SMC_PROCESSING_NUMBER: ClassVar[int] = 8
    """限制异步同时处理订阅源内容的数量, 避免订阅源端流控限制"""
    _LIMIT_SMC_SEND_ENTITY: ClassVar[int] = 2
    """限制异步同时发送订阅源内容的对象数量, 避免机器人平台端流控限制"""

    __slots__ = ('sub_id',)
    sub_id: str

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(sub_id={self.sub_id})'

    def __str__(self) -> str:
        return f'SubscriptionManager | {self.sub_type.upper()} | {self.sub_id}'

    @classmethod
    @abc.abstractmethod
    def init_from_sub_id(cls, sub_id: str | int) -> Self:
        """通用实例化方法, 由 sub_id 实例化"""
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def get_sub_type(cls) -> str:
        """获取订阅源类型"""
        raise NotImplementedError

    @property
    def sub_type(self) -> str:
        """获取订阅源类型"""
        return self.get_sub_type()

    """数据库读写管理部分"""

    @classmethod
    async def _query_type_all_subscription_sources(cls) -> list['SubscriptionSource']:
        """从数据库查询 sub_type 对应的全部订阅源"""
        async with begin_db_session() as session:
            result = await SubscriptionSourceDAL(session=session).query_type_all(sub_type=cls.get_sub_type())
        return result

    async def _query_subscription_source(self) -> 'SubscriptionSource':
        """从数据库查询订阅源"""
        async with begin_db_session() as session:
            result = await SubscriptionSourceDAL(session=session).query_unique(
                sub_type=self.get_sub_type(),
                sub_id=self.sub_id,
            )
        return result

    async def _add_upgrade_subscription_source(self, sub_user_name: str, sub_info: str | None = None) -> None:
        """在数据库新增订阅源, 若已存在则更新"""
        async with begin_db_session() as session:
            source_dal = SubscriptionSourceDAL(session=session)
            try:
                source = await source_dal.query_unique(sub_type=self.get_sub_type(), sub_id=self.sub_id)
                await source_dal.update(id_=source.id, sub_user_name=sub_user_name, sub_info=sub_info)
            except NoResultFound:
                await source_dal.add(
                    sub_type=self.get_sub_type(),
                    sub_id=self.sub_id,
                    sub_user_name=sub_user_name,
                    sub_info=sub_info,
                )

    async def _delete_subscription_source(self) -> None:
        """在数据库删除订阅源"""
        async with begin_db_session() as session:
            source_dal = SubscriptionSourceDAL(session=session)
            source = await source_dal.query_unique(
                sub_type=self.get_sub_type(),
                sub_id=self.sub_id,
            )
            await source_dal.delete(id_=source.id)

    async def _query_all_entity_subscribed(self, entity_type: str | None = None) -> list['Entity']:
        """从数据库查询订阅了该订阅源的所有 Entity 对象"""
        async with begin_db_session() as session:
            source_dal = SubscriptionSourceDAL(session=session)
            source = await source_dal.query_unique(
                sub_type=self.get_sub_type(),
                sub_id=self.sub_id,
            )
            entity_dal = EntityDAL(session=session)
            entity_list = await entity_dal.query_all_entity_subscribed_source(
                sub_source_index_id=source.id,
                entity_type=entity_type,
            )
        return entity_list

    """订阅源内容管理部分"""

    @staticmethod
    @abc.abstractmethod
    def _get_smc_item_mid(smc_item: 'SMC_T') -> str:
        """获取订阅源内容对应的唯一索引 ID"""
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def _parse_smc_item(cls, smc_item: 'SMC_T') -> 'SocialMediaContent':
        """将订阅源内容转换为 SocialMediaContent 数据"""
        raise NotImplementedError

    @classmethod
    async def _check_new_smc_item(cls, smc_items: 'Sequence[SMC_T]') -> 'list[SMC_T]':
        """根据内容对应的唯一索引 ID 检查新的订阅源内容(数据库中没有的)"""
        async with begin_db_session() as session:
            all_mids = [cls._get_smc_item_mid(x) for x in smc_items]
            new_mids = await SocialMediaContentDAL(session=session).query_source_not_exists_mids(
                source=cls.get_sub_type(),
                mids=all_mids,
            )
        return [x for x in smc_items if cls._get_smc_item_mid(x) in new_mids]

    @classmethod
    async def _filter_new_smc_item(cls, smc_items: 'Sequence[SMC_T]') -> 'list[SMC_T]':
        """对新的订阅源内容进行过滤, 对本方法进行重载以自定义需要更新和通知的内容"""
        return list(smc_items)

    @abc.abstractmethod
    async def _query_sub_source_smc_items(self) -> 'list[SMC_T]':
        """获取订阅源现有的所有内容"""
        raise NotImplementedError

    async def _query_sub_source_new_smc_items(self) -> 'list[SMC_T]':
        """获取订阅源现有的更新内容"""
        all_smc_items = await self._query_sub_source_smc_items()
        new_smc_items = await self._check_new_smc_item(smc_items=all_smc_items)
        return await self._filter_new_smc_item(smc_items=new_smc_items)

    @classmethod
    async def _add_upgrade_smc_item(cls, smc_item: 'SMC_T') -> None:
        """在数据库中写入订阅源内容"""
        parsed_smc_item = cls._parse_smc_item(smc_item)
        async with begin_db_session() as session:
            await SocialMediaContentDAL(session=session).upsert(
                source=cls.get_sub_type(),
                m_id=parsed_smc_item.m_id,
                m_type=parsed_smc_item.m_type,
                m_uid=parsed_smc_item.m_uid,
                title=parsed_smc_item.title,
                content=parsed_smc_item.content,
                ref_content=parsed_smc_item.ref_content,
            )

    async def _add_sub_source_new_smc_content(self) -> None:
        """在数据库中更新订阅源的所有新内容(仅新增不更新)"""
        new_smc_items = await self._query_sub_source_new_smc_items()
        tasks = [self._add_upgrade_smc_item(smc_item=smc_item) for smc_item in new_smc_items]
        await semaphore_gather(tasks=tasks, semaphore_num=self._LIMIT_SMC_PROCESSING_NUMBER, return_exceptions=False)

    """Entity 对象订阅管理部分"""

    @abc.abstractmethod
    async def query_sub_source_data(self) -> 'SubscriptionSource':
        """从订阅源站点或 API 获取订阅源信息(注意: 本方法返回的订阅源信息索引 ID 为缺省值 -1)"""
        raise NotImplementedError

    async def _add_upgrade_sub_source(self) -> 'SubscriptionSource':
        """在数据库中新更新订阅源"""
        sub_source_data = await self.query_sub_source_data()

        # 提前添加订阅源内容到数据库避免后续检查时将添加时已存在的的内容一并带出
        await self._add_sub_source_new_smc_content()

        # 将订阅源信息写入数据库
        await self._add_upgrade_subscription_source(
            sub_user_name=sub_source_data.sub_user_name,
            sub_info=sub_source_data.sub_info,
        )

        # `self._query_sub_source_data()` 提供的订阅源信息索引 ID 为缺省值, 这里需要反查获取真实的索引 ID
        return await self._query_subscription_source()

    async def add_entity_sub(self, interface: 'OmMI') -> None:
        """为目标 Entity 添加订阅源的对应订阅"""
        source_res = await self._add_upgrade_sub_source()
        await interface.entity.add_subscription(
            subscription_source=source_res,
            sub_info=f'订阅类型: {source_res.sub_type}, 订阅ID: {source_res.sub_id}',
        )

    async def delete_entity_sub(self, interface: 'OmMI') -> None:
        """为目标 Entity 删除订阅源的对应订阅"""
        source_res = await self._query_subscription_source()
        await interface.entity.delete_subscription(subscription_source=source_res)

    @classmethod
    async def query_entity_subscribed_sub_source(cls, interface: 'OmMI') -> dict[str, str]:
        """获取目标对象已订阅的订阅源

        :return: {sub_id: sub_user_name} 的字典"""
        subscribed_source = await interface.entity.query_subscribed_source(sub_type=cls.get_sub_type())
        return {x.sub_id: x.sub_user_name for x in subscribed_source}

    @classmethod
    async def query_all_subscribed_sub_source_ids(cls) -> list[str]:
        """获取所有已被订阅的订阅源的订阅 ID 列表

        :return: sub_id 列表
        """
        source_res = await cls._query_type_all_subscription_sources()
        return [x.sub_id for x in source_res]

    async def query_subscribed_entity_by_sub_source(self) -> list['Entity']:
        """根据订阅源查询已经订阅了该订阅源的 Entity 对象"""
        return await self._query_all_entity_subscribed()

    """消息处理和发送管理部分"""

    @classmethod
    @abc.abstractmethod
    async def _format_smc_item_message(cls, smc_item: 'SMC_T') -> str | OmegaMessage | None:
        """处理订阅源内容为消息"""
        raise NotImplementedError

    @classmethod
    async def enable_entity_notice_at_all_node(cls, entity: 'OmegaEntity') -> None:
        """启用目标 Entity 通知@所有人的权限"""
        await entity.set_auth_setting(
            module=f'Omega.{cls.__name__}',
            plugin=cls.get_sub_type(),
            node=cls._SETTING_NODE_NOTICE_AT_ALL,
            available=1,
        )

    @classmethod
    async def disable_entity_notice_at_all_node(cls, entity: 'OmegaEntity') -> None:
        """禁用目标 Entity 通知@所有人的权限"""
        await entity.set_auth_setting(
            module=f'Omega.{cls.__name__}',
            plugin=cls.get_sub_type(),
            node=cls._SETTING_NODE_NOTICE_AT_ALL,
            available=0,
        )

    @classmethod
    async def _check_entity_has_notice_at_all_node(cls, entity: 'OmegaEntity') -> bool:
        """检查目标 Entity 是否具有通知@所有人的权限"""
        try:
            return await entity.check_auth_setting(
                module=f'Omega.{cls.__name__}',
                plugin=cls.get_sub_type(),
                node=cls._SETTING_NODE_NOTICE_AT_ALL,
            )
        except Exception as e:
            logger.warning(f'{cls.__name__} | Checking {entity} notice at all node failed, {e!r}')
            return False

    async def _entity_message_send_postprocessor(self, response: 'SentMessageResponse', smc_item: 'SMC_T') -> None:
        """向 Entity 发送消息的后处理"""

    async def _send_entity_message(self, entity: 'Entity', message: str | OmegaMessage, smc_item: 'SMC_T') -> None:
        """向 Entity 发送消息"""
        try:
            async with begin_db_session() as session:
                # 根据获取到的 Entity 信息实例化对象接口
                internal_entity = await OmegaEntity.init_from_entity_index_id(session=session, index_id=entity.id)

                # 预处理@全息消息
                if await self._check_entity_has_notice_at_all_node(entity=internal_entity):
                    message = OmegaMessageSegment.at_all() + message

                # 向对应 Entity 发送消息
                response = await OmEI(entity=internal_entity).send_entity_message(message=message)

                # 执行消息发送后处理
                await self._entity_message_send_postprocessor(response=response, smc_item=smc_item)
        except ActionFailed as e:
            logger.warning(f'{self} | Sending message to {entity} failed with ActionFailed, {e!r}')
        except Exception as e:
            logger.error(f'{self} | Sending message to {entity} failed, {e!r}')

    async def _send_subscribed_entity_smc_message(self, smc_item: 'SMC_T') -> None:
        """向所有订阅了该订阅源的 Entity 订阅者发送新订阅内容信息"""
        send_message = await self._format_smc_item_message(smc_item=smc_item)
        if send_message is None:
            logger.debug(f'{self} | Sending message is None, {smc_item!r}, ignored')
            return

        subscribed_entity = await self.query_subscribed_entity_by_sub_source()
        send_tasks = [
            self._send_entity_message(entity=entity, message=send_message, smc_item=smc_item)
            for entity in subscribed_entity
        ]
        await semaphore_gather(tasks=send_tasks, semaphore_num=self._LIMIT_SMC_SEND_ENTITY)

    async def check_subscription_source_update_and_send_entity_message(self) -> None:
        """检查订阅源更新并向已订阅的对象发送新订阅内容信息"""
        logger.debug(f'{self} | Start checking updated content')

        new_smc_items = await self._query_sub_source_new_smc_items()
        if new_smc_items:
            logger.info(
                f'{self} | Confirmed new content(s): '
                f'{", ".join(self._get_smc_item_mid(smc_item=smc_item) for smc_item in new_smc_items)}'
            )
        else:
            logger.debug(f'{self} | No new content found')
            return

        # 更新内容先插入数据库避免发送失败后重复发送
        add_artwork_tasks = [self._add_upgrade_smc_item(smc_item=smc_item) for smc_item in new_smc_items]
        await semaphore_gather(
            tasks=add_artwork_tasks,
            semaphore_num=self._LIMIT_SMC_PROCESSING_NUMBER,
            return_exceptions=False,
        )

        # 向订阅者发送订阅更新信息
        send_tasks = [
            self._send_subscribed_entity_smc_message(smc_item=smc_item)
            for smc_item in new_smc_items
        ]
        await semaphore_gather(tasks=send_tasks, semaphore_num=self._LIMIT_SMC_SEND_ENTITY)


__all__ = [
    'BaseSubscriptionManager',
]
