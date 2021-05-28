import json
from nonebot import logger
from omega_miya.utils.Omega_plugin_utils import HttpFetcher
from omega_miya.utils.Omega_Base import Result
from .request_utils import BiliRequestUtils
from .data_classes import BiliInfo, BiliResult


class BiliDynamic(object):
    __DYNAMIC_DETAIL_API_URL = 'https://api.vc.bilibili.com/dynamic_svr/v1/dynamic_svr/get_dynamic_detail'
    __DYNAMIC_ROOT_URL = 'https://t.bilibili.com/'

    __HEADERS = BiliRequestUtils.HEADERS.copy()
    __HEADERS.update({'origin': 'https://t.bilibili.com',
                      'referer': 'https://t.bilibili.com/'})

    def __init__(self, dynamic_id: int):
        self.dynamic_id = dynamic_id

    @property
    def dy_id(self):
        return str(self.dynamic_id)

    async def get_info(self) -> Result.DictResult:
        cookies = None
        # 检查cookies
        cookies_res = BiliRequestUtils.get_cookies()
        if cookies_res.success():
            cookies = cookies_res.result

        paras = {'dynamic_id': self.dy_id}
        fetcher = HttpFetcher(
            timeout=10, flag='bilibili_dynamic', headers=self.__HEADERS, cookies=cookies)
        result = await fetcher.get_json(url=self.__DYNAMIC_DETAIL_API_URL, params=paras)

        if result.error:
            return result

        if result.result.get('code') != 0:
            return Result.DictResult(error=True, info=result.result.get('message'), result={})

        try:
            data_dict = dict(result.result['data']['card'])
            return Result.DictResult(error=False, info='Success', result=data_dict)
        except Exception as e:
            return Result.DictResult(error=True, info=repr(e), result={})

    @classmethod
    def data_parser(cls, dynamic_data: dict) -> BiliResult.DynamicInfoResult:
        """
        解析 get_info 或 get_dynamic_history 获取的动态数据
        :param dynamic_data: BiliDynamic.get_info 或 BiliUser.get_dynamic_history 获取的数据类型, 参考 Bilibili api
        :return: DynamicInfo
        """

        # 解析描述部分
        try:
            dynamic_desc = dynamic_data['desc']
            dynamic_id = dynamic_desc['dynamic_id']
            type_ = dynamic_desc['type']
            url = f"{cls.__DYNAMIC_ROOT_URL}{dynamic_id}"

            # 处理一些特殊情况
            if type_ == 1:
                # type=1, 这是一条转发的动态
                orig_dy_id = dynamic_desc['origin']['dynamic_id']
                orig_type = dynamic_desc['origin']['type']
                # 备用
                # orig_dy_id = dynamic_desc['orig_dy_id']
                # orig_type = dynamic_desc['orig_type']
            else:
                orig_dy_id = 0
                orig_type = 0

            if type_ == 512:
                # 番剧特殊动态类型, 无用户信息
                user_id = 0
                user_name = '哔哩哔哩番剧'
            else:
                user_id = dynamic_desc['user_profile']['info']['uid']
                user_name = dynamic_desc['user_profile']['info']['uname']

        except Exception as e:
            logger.error(f'BiliDynamic: Parse dynamic desc failed, error info: {repr(e)}')
            return BiliResult.DynamicInfoResult(
                error=True, info=f'Parse dynamic desc failed, error: {repr(e)}', result=None)

        # 解析内容部分
        try:
            dynamic_card_data = dynamic_data['card']
            dynamic_card = json.loads(dynamic_card_data)
            """
            动态type对应如下: 
            1 转发
            2 消息(有图片)
            4 消息(无图片)
            8 视频投稿
            16 小视频(含playurl地址)
            32 番剧更新
            64 专栏
            256 音频
            512 番剧更新(含详细信息)
            1024 未知(没遇见过)
            2048 B站活动相关(直播日历, 草图?计划?之内的)(大概是了)
            """
            pictures = []
            # type=1, 这是一条转发的动态
            if type_ == 1:
                origin_user = dynamic_card.get('origin_user')
                if origin_user and origin_user['info'].get('uname'):
                    origin_user_name = origin_user['info'].get('uname')
                    desc = f'转发了{origin_user_name}的动态'
                else:
                    desc = f'转发了一条动态'
                content = dynamic_card['item']['content']
                title = None
                description = None
            # type=2, 这是一条原创的动态(有图片)
            elif type_ == 2:
                desc = '发布了新动态'
                content = dynamic_card['item']['description']
                pictures.extend([pic_info['img_src'] for pic_info in dynamic_card['item']['pictures']])
                title = None
                description = None
            # type=4, 这是一条原创的动态(无图片)
            elif type_ == 4:
                desc = '发布了新动态'
                content = dynamic_card['item']['content']
                title = None
                description = None
            # type=8, 这是发布视频
            elif type_ == 8:
                desc = '发布了新的视频'
                content = dynamic_card['dynamic']
                pictures.append(dynamic_card['pic'])
                title = dynamic_card['title']
                description = dynamic_card['desc']
            # type=16, 这是小视频(现在似乎已经失效？)
            elif type_ == 16:
                desc = '发布了新的小视频动态'
                content = dynamic_card['item']['description']
                title = None
                description = None
            # type=32, 这是番剧更新
            elif type_ == 32:
                desc = '发布了新的番剧'
                content = dynamic_card['dynamic']
                pictures.append(dynamic_card['pic'])
                title = dynamic_card['title']
                description = None
            # type=64, 这是文章动态
            elif type_ == 64:
                desc = '发布了新的文章'
                content = dynamic_card['summary']
                pictures.extend(dynamic_card['origin_image_urls'])
                title = dynamic_card['title']
                description = None
            # type=256, 这是音频
            elif type_ == 256:
                desc = '发布了新的音乐'
                content = dynamic_card['intro']
                pictures.append(dynamic_card['cover'])
                title = dynamic_card['title']
                description = None
            # type=512, 番剧更新（详情）
            elif type_ == 512:
                desc = '发布了新的番剧'
                content = dynamic_card['index_title']
                pictures.append(dynamic_card['cover'])
                title = dynamic_card['apiSeasonInfo']['title']
                description = None
            # type=2048, B站活动相关
            elif type_ == 2048:
                desc = '发布了一条活动相关动态'
                content = dynamic_card['vest']['content']
                title = dynamic_card['sketch']['title']
                description = dynamic_card['sketch']['desc_text']
            # 其他未知类型
            else:
                desc = 'Unknown'
                content = 'Unknown'
                title = None
                description = None

            data = BiliInfo.DynamicInfo.DynamicCard(
                content=content,
                pictures=pictures,
                title=title,
                description=description
            )
        except Exception as e:
            logger.error(f'BiliDynamic: Parse dynamic card failed, dynamic id: {dynamic_id}, error info: {repr(e)}')
            return BiliResult.DynamicInfoResult(
                error=True, info=f'Parse dynamic card failed, error: {repr(e)}', result=None)

        dynamic_info = BiliInfo.DynamicInfo(
            dynamic_id=dynamic_id,
            user_id=user_id,
            user_name=user_name,
            type=type_,
            desc=desc,
            url=url,
            orig_dy_id=orig_dy_id,
            orig_type=orig_type,
            data=data
        )
        return BiliResult.DynamicInfoResult(error=False, info='Success', result=dynamic_info)


__all__ = [
    'BiliDynamic'
]
