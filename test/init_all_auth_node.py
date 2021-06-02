from omega_miya.plugins.Omega_manager import init_group_auth_node, init_user_auth_node
from omega_miya.utils.Omega_Base import DBBot, DBFriend, DBBotGroup
from nonebot.adapters.cqhttp.bot import Bot
import nonebot

driver = nonebot.get_driver()


@driver.on_bot_connect
async def init_all_auth_node(bot: Bot):
    self_bot = DBBot(self_qq=int(bot.self_id))
    all_friends = await DBFriend.list_exist_friends(self_bot=self_bot)
    for user_id in all_friends.result:
        if user_id in [123456789]:
            continue
        await init_user_auth_node(user_id=int(user_id))
        print(f'Init_user_auth_node completed, user: {user_id}')

    group_res = await DBBotGroup.list_exist_bot_groups(self_bot=self_bot)
    all_groups = [int(x) for x in group_res.result]
    for group_id in all_groups:
        if group_id in [987654321]:
            continue
        await init_group_auth_node(group_id=int(group_id))
        print(f'Init_group_auth_node completed, group: {group_id}')

