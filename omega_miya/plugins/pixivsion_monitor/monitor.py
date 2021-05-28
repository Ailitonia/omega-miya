import asyncio
from nonebot import logger, require, get_bots
from nonebot.adapters.cqhttp import MessageSegment
from omega_miya.utils.Omega_Base import DBSubscription, DBPixivision
from omega_miya.utils.Omega_plugin_utils import MsgSender
from omega_miya.utils.pixiv_utils import PixivIllust, PixivisionArticle
from .utils import pixivsion_article_parse
from .block_tag import TAG_BLOCK_LIST


# 启用检查动态状态的定时任务
scheduler = require("nonebot_plugin_apscheduler").scheduler


@scheduler.scheduled_job(
    'cron',
    # year=None,
    # month=None,
    # day='*/1',
    # week=None,
    # day_of_week=None,
    # hour='*/1',
    minute='*/30',
    # second='*/30',
    # start_date=None,
    # end_date=None,
    # timezone=None,
    id='pixivision_monitor',
    coalesce=True,
    misfire_grace_time=45
)
async def pixivision_monitor():
    logger.debug(f"pixivision_monitor: checking started")

    # 获取当前bot列表
    bots = [bot for bot_id, bot in get_bots().items()]

    # 初始化tag黑名单
    block_tag_id = []
    block_tag_name = []
    for block_tag in TAG_BLOCK_LIST:
        block_tag_id.append(block_tag.get('id'))
        block_tag_name.append(block_tag.get('name'))

    # 提取数据库中已有article的id列表
    pixivision_res = await DBPixivision.list_article_id()
    exist_article = [int(x) for x in pixivision_res.result]

    # 获取最新一页pixivision的article
    new_article = []
    articles_result = await PixivisionArticle.get_illustration_list()
    if articles_result.error:
        logger.error(f'pixivision_monitor: checking pixivision failed: {articles_result.info}')
        return

    for article in articles_result.result:
        try:
            article = dict(article)
            article_tags_id = []
            article_tags_name = []
            for tag in article['tags']:
                article_tags_id.append(int(tag['tag_id']))
                article_tags_name.append(str(tag['tag_name']))
            # 跳过黑名单tag的article
            if list(set(article_tags_id) & set(block_tag_id)) or list(set(article_tags_name) & set(block_tag_name)):
                continue
            # 获取新的article内容
            if int(article['id']) not in exist_article:
                logger.info(f"pixivision_monitor: 检查到新的Pixivision article: {article['id']}")
                new_article.append({'aid': int(article['id']), 'tags': article_tags_name})
        except Exception as e:
            logger.error(f'pixivision_monitor: an error occured in checking pixivision: {repr(e)}')
            continue

    if not new_article:
        logger.info(f'pixivision_monitor: checking completed, 没有新的article')
        return

    subscription = DBSubscription(sub_type=8, sub_id=-1)

    # 处理新的aritcle
    for article in new_article:
        aid = int(article['aid'])
        tags = list(article['tags'])
        a_res = await pixivsion_article_parse(aid=aid, tags=tags)
        if a_res.success():
            article_data = a_res.result
            msg = f"新的Pixivision特辑！\n\n" \
                  f"《{article_data['title']}》\n\n{article_data['description']}\n{article_data['url']}"

            for _bot in bots:
                msg_sender = MsgSender(bot=_bot, log_flag='NewPixivisionArticle')
                await msg_sender.safe_broadcast_groups_subscription(subscription=subscription, message=msg)

            # 处理article中图片内容
            tasks = []
            for pid in article_data['illusts_list']:
                tasks.append(PixivIllust(pid=pid).pic_2_base64())
            p_res = await asyncio.gather(*tasks)
            image_error = 0
            for image_res in p_res:
                if not image_res.success():
                    image_error += 1
                    continue
                else:
                    img_seg = MessageSegment.image(image_res.result)
                # 发送图片
                for _bot in bots:
                    msg_sender = MsgSender(bot=_bot, log_flag='NewPixivisionImage')
                    await msg_sender.safe_broadcast_groups_subscription(subscription=subscription, message=img_seg)

            logger.info(f"article: {aid} 图片已发送完成, 失败: {image_error}")
        else:
            logger.error(f"article: {aid} 信息解析失败, info: {a_res.info}")
    logger.info(f'pixivision_monitor: checking completed, 已处理新的article: {repr(new_article)}')

__all__ = [
    'scheduler'
]
