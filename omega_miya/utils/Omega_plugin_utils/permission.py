from omega_miya.database import DBBot, DBFriend, DBBotGroup, DBAuth


class PermissionChecker(object):
    def __init__(self, self_bot: DBBot):
        self.self_bot = self_bot

    async def check_notice_permission(self, group_id: int) -> bool:
        res = await DBBotGroup(group_id=group_id, self_bot=self.self_bot).permission_notice()
        if res.result == 1:
            return True
        else:
            return False

    async def check_command_permission(self, group_id: int) -> bool:
        res = await DBBotGroup(group_id=group_id, self_bot=self.self_bot).permission_command()
        if res.result == 1:
            return True
        else:
            return False

    async def check_permission_level(self, group_id: int, level: int) -> bool:
        res = await DBBotGroup(group_id=group_id, self_bot=self.self_bot).permission_level()
        if res.result >= level:
            return True
        else:
            return False

    async def check_auth_node(self, auth_id: int, auth_type: str, auth_node: str) -> int:
        auth = DBAuth(self_bot=self.self_bot, auth_id=auth_id, auth_type=auth_type, auth_node=auth_node)
        tag_res = await auth.tags_info()
        allow_tag = tag_res.result[0]
        deny_tag = tag_res.result[1]

        if allow_tag == 1 and deny_tag == 0:
            return 1
        elif allow_tag == -2 and deny_tag == -2:
            return 0
        else:
            return -1

    async def check_friend_private_permission(self, user_id: int) -> bool:
        res = await DBFriend(user_id=user_id, self_bot=self.self_bot).get_private_permission()
        if res.error:
            return False
        elif res.result == 1:
            return True
        else:
            return False


__all__ = [
    'PermissionChecker'
]
