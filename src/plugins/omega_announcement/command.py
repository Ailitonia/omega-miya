"""
@Author         : Ailitonia
@Date           : 2023/7/15 18:51
@FileName       : command.py
@Project        : nonebot2_miya
@Description    : 公告命令
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import Annotated

from nonebot.adapters import Message
from nonebot.log import logger
from nonebot.matcher import Matcher
from nonebot.params import Arg, Depends
from nonebot.permission import SUPERUSER
from nonebot.plugin import on_command
from nonebot.rule import to_me

from src.database import EntityDAL
from src.params.handler import get_command_message_arg_parser_handler
from src.service import OmegaEntity, OmegaInterface, enable_processor_state
from src.utils.process_utils import semaphore_gather


@on_command(
    'announce',
    rule=to_me(),
    aliases={'公告', 'ta'},
    permission=SUPERUSER,
    handlers=[get_command_message_arg_parser_handler('announcement_content')],
    priority=10,
    block=True,
    state=enable_processor_state(name='OmegaAnnouncement', enable_processor=False)
).got('announcement_content', prompt='请输入公告内容:')
async def handle_announce(
        matcher: Matcher,
        entity_dal: Annotated[EntityDAL, Depends(EntityDAL.dal_dependence)],
        announcement_content: Annotated[Message, Arg('announcement_content')]
) -> None:
    interface = OmegaInterface()
    announce_message = interface.get_msg_extractor()(message=announcement_content).message

    all_entity = await entity_dal.query_all()

    tasks = []
    for entity in all_entity:
        entity = await OmegaEntity.init_from_entity_index_id(session=entity_dal.db_session, index_id=entity.id)
        if not await entity.check_global_permission():
            continue

        tasks.append(OmegaInterface(entity=entity).send_msg(message=announce_message))

    announce_result = await semaphore_gather(tasks=tasks, semaphore_num=3)

    if any(isinstance(x, Exception) for x in announce_result):
        logger.warning(f'Announce | 公告批量发送完成, 部分公告发送失败')
        await matcher.finish('公告批量发送完成, 部分对象发送失败')
    else:
        logger.success(f'Announce | 公告批量发送完成')
        await matcher.finish('公告批量发送完成, 所有对象均已发送成功')


__all__ = []
