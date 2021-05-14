import asyncio
import time
from dataclasses import dataclass
from typing import List, Union
from nonebot import logger
from nonebot.adapters import Bot
from nonebot.adapters.cqhttp import MessageSegment
from omega_miya.utils.Omega_Base import DBSubscription, DBHistory, DBTable, Result
from omega_miya.utils.bilibili_utils import BiliLiveRoom, BiliUser, BiliRequestUtils, BiliInfo


# 初始化直播间标题, 状态
live_title = {}
live_status = {}
live_up_name = {}
live_uid_by_rid = {}


class BiliLiveChecker(object):
    def __init__(self, room_id: int):
        self.room_id = room_id

    # 针对直播间单独进行初始化
    async def init_live_info(self):
        global live_title
        global live_status
        global live_up_name
        global live_uid_by_rid

        try:
            # 获取直播间信息
            live_info_result = await BiliLiveRoom(room_id=self.room_id).get_info()
            if live_info_result.error:
                logger.opt(colors=True).error(
                    f'init_live_info: <r>获取直播间信息失败</r>, room_id: {self.room_id}, error: {live_info_result.info}')
                return
            live_info = live_info_result.result
            up_uid = live_info.uid

            user_info_result = await BiliUser(user_id=up_uid).get_info()
            if user_info_result.error:
                logger.opt(colors=True).error(
                    f'init_live_info: <r>获取直播间用户信息失败</r>, room_id: {self.room_id}, error: {user_info_result.info}')
                return
            up_name = user_info_result.result.name

            # 直播状态放入live_status全局变量中
            live_status[self.room_id] = int(live_info.status)

            # 直播间标题放入live_title全局变量中
            live_title[self.room_id] = str(live_info.title)

            # 直播间用户uid放入live_uid_by_rid全局变量中
            live_uid_by_rid[self.room_id] = int(live_info.uid)

            # 直播间up名称放入live_up_name全局变量中
            live_up_name[self.room_id] = str(up_name)

            logger.opt(colors=True).info(f"init_live_info: <lc>初始化直播间 {self.room_id}/{up_name} ... </lc>"
                                         f"<g>status: {live_info.status}</g>")
        except Exception as e:
            logger.opt(colors=True).error(f'init_live_info: <r>初始化直播间 {self.room_id} 失败</r>, <y>error: {repr(e)}</y>')
            return

    @classmethod
    # 启动时执行的全全部直播间初始化
    async def init_global_live_info(cls):
        cookies_result = await BiliRequestUtils().verify_cookies()
        if cookies_result.success():
            logger.opt(colors=True).info(f'<g>Bilibili 已登录!</g> 当前用户: {cookies_result.result}')
        else:
            logger.opt(colors=True).warning(f'<r>Bilibili 登录状态异常: {cookies_result.info}!</r> 建议在配置中正确设置cookies!')

        logger.opt(colors=True).info('init_live_info: <y>初始化B站直播间监控列表...</y>')
        t = DBTable(table_name='Subscription')
        tasks = []
        sub_res = await t.list_col_with_condition('sub_id', 'sub_type', 1)
        for sub_id in sub_res.result:
            tasks.append(BiliLiveChecker(room_id=sub_id).init_live_info())
        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            logger.error(f'bilibili_live_monitor: init live info failed, error: {repr(e)}')
        logger.opt(colors=True).info('init_live_info: <g>B站直播间监控列表初始化完成.</g>')

    @classmethod
    def live_title(cls) -> dict:
        return live_title

    @classmethod
    def live_status(cls) -> dict:
        return live_status

    @classmethod
    def live_up_name(cls) -> dict:
        return live_up_name

    @classmethod
    def live_uid_by_rid(cls) -> dict:
        return live_uid_by_rid

    @dataclass
    class LiveRoomCheckerResult(Result.AnyResult):
        changed: bool
        action: bool
        original: Union[int, str]
        new: Union[int, str]
        result: Union[int, str]

        def __repr__(self):
            return f'<LiveRoomCheckerResult(error={self.error}, info={self.info}, action={self.action}, ' \
                   f'changed={self.changed}, original={self.original}, new={self.new}, result={self.result})>'

    async def check_global_status(self) -> Result.IntResult:
        global live_title
        global live_status
        global live_up_name

        try:
            up_name = live_up_name[self.room_id]
            status = live_status[self.room_id]
            title = live_title[self.room_id]
        except (KeyError, TypeError):
            await self.init_live_info()
            try:
                up_name = live_up_name[self.room_id]
                status = live_status[self.room_id]
                title = live_title[self.room_id]
            except (KeyError, TypeError):
                logger.error(f'直播间: {self.room_id} 状态失效且获取失败!')
                return Result.IntResult(error=True, info=f'直播间 {self.room_id} 状态失效且获取失败', result=-1)

        return Result.IntResult(error=False, info='Success', result=status)

    async def title_change_checker(self, live_info: BiliInfo.LiveRoomInfo) -> LiveRoomCheckerResult:
        global live_title
        global live_status
        global live_up_name

        up_name = live_up_name[self.room_id]
        old_title = live_title[self.room_id]

        # 检查是否是已开播状态, 若已开播则监测直播间标题变动
        # 为避免开播时同时出现标题变更通知和开播通知, 在检测到直播状态变化时更新标题, 且仅在直播状态为直播中时发送标题变更通知
        # 刚开播时标题更新
        if live_info.status != live_status[self.room_id] \
                and live_info.status == 1 \
                and live_info.title != live_title[self.room_id]:
            # 更新标题
            live_title[self.room_id] = live_info.title
            logger.info(f"直播间: {self.room_id}/{up_name} 标题变更为: {live_info.title}")
            return self.LiveRoomCheckerResult(error=False, changed=True, action=False, info='Success',
                                              original=old_title, new=live_info.title, result='')

        # 直播过程中标题更新
        elif live_info.status == 1 and live_info.title != live_title[self.room_id]:
            if live_info.cover_img:
                cover_pic_result = await BiliRequestUtils.pic_2_base64(url=live_info.cover_img)
                if cover_pic_result.success():
                    # 发送的消息
                    msg = f"{up_name}的直播间换标题啦！\n\n【{live_info.title}】\n" \
                          f"{MessageSegment.image(cover_pic_result.result)}"
                else:
                    msg = f"{up_name}的直播间换标题啦！\n\n【{live_info.title}】"
            else:
                msg = f"{up_name}的直播间换标题啦！\n\n【{live_info.title}】"
            # 更新标题
            live_title[self.room_id] = live_info.title
            logger.info(f"直播间: {self.room_id}/{up_name} 标题变更为: {live_info.title}")
            return self.LiveRoomCheckerResult(error=False, changed=True, action=True, info='Success',
                                              original=old_title, new=live_info.title, result=msg)

        # 其他情况忽略
        else:
            return self.LiveRoomCheckerResult(error=False, changed=False, action=False, info='Success',
                                              original=old_title, new=live_info.title, result='')

    async def status_change_checker(self, live_info: BiliInfo.LiveRoomInfo) -> LiveRoomCheckerResult:
        global live_title
        global live_status
        global live_up_name

        up_name = live_up_name[self.room_id]
        old_status = live_status[self.room_id]

        # 检测开播/下播
        # 检查直播间状态与原状态是否一致
        if live_info.status != live_status[self.room_id]:
            # 现在状态为未开播
            if live_info.status == 0:
                # 事件记录写入数据库
                live_end_info = f"LiveEnd! Room: {self.room_id}/{up_name}"
                new_event = DBHistory(time=int(time.time()), self_id=-1, post_type='bilibili',
                                      detail_type='live')
                await new_event.add(sub_type='live_end', user_id=self.room_id, user_name=up_name,
                                    raw_data=repr(live_info), msg_data=live_end_info)

                # 更新直播间状态
                live_status[self.room_id] = live_info.status
                logger.info(f"直播间: {self.room_id}/{up_name} 下播了")

                # 发送的消息
                msg = f'{up_name}下播了'

                return self.LiveRoomCheckerResult(error=False, changed=True, action=True, info='Success',
                                                  original=old_status, new=live_info.status, result=msg)

            # 现在状态为直播中
            elif live_info.status == 1:
                # 事件记录写入数据库
                live_start_info = f"LiveStart! Room: {self.room_id}/{up_name}, Title: {live_info.title}, " \
                                  f"TrueTime: {live_info.live_time}"
                new_event = DBHistory(time=int(time.time()), self_id=-1, post_type='bilibili',
                                      detail_type='live')
                await new_event.add(sub_type='live_start', user_id=self.room_id, user_name=up_name,
                                    raw_data=repr(live_info), msg_data=live_start_info)

                # 更新直播间状态
                live_status[self.room_id] = live_info.status
                logger.info(f"直播间: {self.room_id}/{up_name} 开播了")

                # 发送的消息
                if live_info.cover_img:
                    cover_pic_result = await BiliRequestUtils.pic_2_base64(url=live_info.cover_img)
                    if cover_pic_result.success():
                        msg = f"{live_info.live_time}\n{up_name}开播啦！\n\n【{live_info.title}】" \
                              f"\n{MessageSegment.image(cover_pic_result.result)}"
                    else:
                        msg = f"{live_info.live_time}\n{up_name}开播啦！\n\n【{live_info.title}】"
                else:
                    msg = f"{live_info.live_time}\n{up_name}开播啦！\n\n【{live_info.title}】"

                return self.LiveRoomCheckerResult(error=False, changed=True, action=True, info='Success',
                                                  original=old_status, new=live_info.status, result=msg)

            # 现在状态为未开播（轮播中）
            elif live_info.status == 2:
                # 事件记录写入数据库
                live_end_info = f"LiveEnd! Room: {self.room_id}/{up_name}"
                new_event = DBHistory(time=int(time.time()), self_id=-1, post_type='bilibili',
                                      detail_type='live')
                await new_event.add(sub_type='live_end_with_playlist', user_id=self.room_id, user_name=up_name,
                                    raw_data=repr(live_info), msg_data=live_end_info)

                # 更新直播间状态
                live_status[self.room_id] = live_info.status
                logger.info(f"直播间: {self.room_id}/{up_name} 下播了（轮播中）")

                # 发送的消息
                msg = f'{up_name}下播了（轮播中）'

                return self.LiveRoomCheckerResult(error=False, changed=True, action=True, info='Success',
                                                  original=old_status, new=live_info.status, result=msg)

            # 遇到的奇怪的状态
            else:
                # 事件记录写入数据库
                live_unknown_info = f"Unknown live status: {live_info.status}, Room: {self.room_id}/{up_name}"
                new_event = DBHistory(time=int(time.time()), self_id=-1, post_type='bilibili',
                                      detail_type='live')
                await new_event.add(sub_type='unknown live status', user_id=self.room_id, user_name=up_name,
                                    raw_data=repr(live_info), msg_data=live_unknown_info)

                # 更新直播间状态
                live_status[self.room_id] = live_info.status
                logger.warning(f"直播间: {self.room_id}/{up_name}, 未知的直播间状态: {live_info.status}")

                return self.LiveRoomCheckerResult(error=True, changed=True, action=False, info=live_unknown_info,
                                                  original=old_status, new=live_info.status, result='')
        else:
            return self.LiveRoomCheckerResult(error=False, changed=False, action=False, info='Success',
                                              original=old_status, new=live_info.status, result='')

    async def broadcaster(
            self, live_info: BiliInfo.LiveRoomInfo, bots: List[Bot], all_groups: List[int], all_friends: List[int]):
        """
        检查直播间状态并向群组发送消息
        :param live_info: 由 get_live_info 或 get_live_info_by_uid_list 获取的直播间信息
        :param bots: bots 列表
        :param all_groups: 所有可能需要通知的群组列表
        :param all_friends: 所有可能需要通知的好友列表
        """
        global_check_result = await self.check_global_status()
        if global_check_result.error:
            return

        sub = DBSubscription(sub_type=1, sub_id=self.room_id)

        # 获取订阅了该直播间的所有群
        sub_group_res = await sub.sub_group_list()
        sub_group = sub_group_res.result
        # 需通知的群
        notice_group = list(set(all_groups) & set(sub_group))

        # 获取订阅了该直播间的所有好友
        sub_friend_res = await sub.sub_user_list()
        sub_friend = sub_friend_res.result
        # 需通知的好友
        notice_friends = list(set(all_friends) & set(sub_friend))

        # 标题变更检测
        title_checker_result = await self.title_change_checker(live_info=live_info)
        if title_checker_result.success() and title_checker_result.action:
            # 通知有通知权限且订阅了该直播间的群
            for group_id in notice_group:
                for _bot in bots:
                    try:
                        await _bot.call_api(
                            api='send_group_msg', group_id=group_id, message=title_checker_result.result)
                        logger.info(f"向群组: {group_id} 发送直播间: {self.room_id} 标题变更通知")
                    except Exception as e:
                        logger.warning(f"向群组: {group_id} 发送直播间: {self.room_id} 标题变更通知失败, error: {repr(e)}")
                        continue
            # 通知有通知权限且订阅了该直播间的好友
            for user_id in notice_friends:
                for _bot in bots:
                    try:
                        await _bot.call_api(
                            api='send_private_msg', user_id=user_id, message=title_checker_result.result)
                        logger.info(f"向好友: {user_id} 发送直播间: {self.room_id} 标题变更通知")
                    except Exception as e:
                        logger.warning(f"向好友: {user_id} 发送直播间: {self.room_id} 标题变更通知失败, error: {repr(e)}")
                        continue

        # 状态变更检测
        status_checker_result = await self.status_change_checker(live_info=live_info)
        if status_checker_result.success() and status_checker_result.action:
            # 通知有通知权限且订阅了该直播间的群
            up_name = live_up_name[self.room_id]
            status = live_status[self.room_id]
            for group_id in notice_group:
                for _bot in bots:
                    try:
                        await _bot.call_api(
                            api='send_group_msg', group_id=group_id, message=status_checker_result.result)
                        logger.info(
                            f"向群组: {group_id} 发送直播间: {self.room_id}/{up_name} 直播通知, status: {status}")
                    except Exception as e:
                        logger.warning(f"向群组: {group_id} 发送直播间: {self.room_id}/{up_name} 直播通知失败, error: {repr(e)}")
                        continue
            # 通知有通知权限且订阅了该直播间的好友
            for user_id in notice_friends:
                for _bot in bots:
                    try:
                        await _bot.call_api(
                            api='send_private_msg', user_id=user_id, message=status_checker_result.result)
                        logger.info(
                            f"向好友: {user_id} 发送直播间: {self.room_id}/{up_name} 直播通知, status: {status}")
                    except Exception as e:
                        logger.warning(f"向好友: {user_id} 发送直播间: {self.room_id}/{up_name} 直播通知失败, error: {repr(e)}")
                        continue


__all__ = [
    'BiliLiveChecker'
]
