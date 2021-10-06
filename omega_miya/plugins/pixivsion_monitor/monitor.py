import asyncio
from nonebot import logger, require, get_bots, get_driver
from nonebot.adapters.cqhttp import MessageSegment
from omega_miya.database import DBSubscription, DBPixivision
from omega_miya.utils.omega_plugin_utils import MsgSender
from omega_miya.utils.pixiv_utils import PixivIllust, PixivisionArticle
from .utils import pixivsion_article_parse
from .config import Config


__global_config = get_driver().config
plugin_config = Config(**__global_config.dict())
ENABLE_NODE_CUSTOM = plugin_config.enable_node_custom
PIXIVISION_SUB_ID = plugin_config.sub_id
TAG_BLOCK_LIST = plugin_config.tag_block_list


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
    misfire_grace_time=120
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

    subscription = DBSubscription(sub_type=8, sub_id=PIXIVISION_SUB_ID)

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
                tasks.append(PixivIllust(pid=pid).get_file())
            p_res = await asyncio.gather(*tasks)
            image_error = 0

            if ENABLE_NODE_CUSTOM:
                node_messages = []
                for image_res in p_res:
                    if not image_res.success():
                        image_error += 1
                        continue
                    # 构造自定义消息节点
                    node_messages.append(MessageSegment.image(image_res.result))
                # 发送消息
                for _bot in bots:
                    msg_sender = MsgSender(bot=_bot, log_flag='NewPixivisionImage')
                    await msg_sender.safe_broadcast_groups_subscription_node_custom(
                        subscription=subscription, message_list=node_messages)
            else:
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


# 用于首次订阅时刷新数据库信息
async def init_pixivsion_article():
    # 暂停计划任务避免中途检查更新
    scheduler.pause()
    try:
        # 获取最新一页pixivision的article
        new_article = []
        articles_result = await PixivisionArticle.get_illustration_list()
        if articles_result.error:
            return
        for article in articles_result.result:
            try:
                article = dict(article)
                article_tags_id = []
                article_tags_name = []
                for tag in article['tags']:
                    article_tags_id.append(int(tag['tag_id']))
                    article_tags_name.append(str(tag['tag_name']))
                new_article.append({'aid': int(article['id']), 'tags': article_tags_name})
            except Exception as e:
                logger.debug(f'解析pixivsion article失败, error: {repr(e)}, article data: {article}')
                continue
        # 处理新的aritcle
        for article in new_article:
            aid = int(article['aid'])
            tags = list(article['tags'])
            await pixivsion_article_parse(aid=aid, tags=tags)
    except Exception as e:
        logger.info(f'初始化pixivsion article错误, error: {repr(e)}.')

    scheduler.resume()
    logger.info(f'初始化pixivsion article完成, 已将作品信息写入数据库.')


__all__ = [
    'scheduler',
    'init_pixivsion_article',
    'PIXIVISION_SUB_ID'
]
