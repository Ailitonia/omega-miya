import asyncio
from nonebot import logger, require, get_bots
from nonebot.adapters.cqhttp import MessageSegment
from omega_miya.utils.Omega_Base import DBSubscription, DBTable
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
    bots = []
    for bot_id, bot in get_bots().items():
        bots.append(bot)

    # 获取所有有通知权限的群组
    t = DBTable(table_name='Group')
    group_res = await t.list_col_with_condition('group_id', 'notice_permissions', 1)
    all_noitce_groups = [int(x) for x in group_res.result]

    # 初始化tag黑名单
    block_tag_id = []
    block_tag_name = []
    for block_tag in TAG_BLOCK_LIST:
        block_tag_id.append(block_tag.get('id'))
        block_tag_name.append(block_tag.get('name'))

    # 提取数据库中已有article的id列表
    t = DBTable(table_name='Pixivision')
    pixivision_res = await t.list_col(col_name='aid')
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

    sub = DBSubscription(sub_type=8, sub_id=-1)
    # 获取订阅了该直播间的所有群
    sub_group_res = await sub.sub_group_list()
    sub_group = sub_group_res.result
    # 需通知的群
    notice_group = list(set(all_noitce_groups) & set(sub_group))

    # 处理新的aritcle
    for article in new_article:
        aid = int(article['aid'])
        tags = list(article['tags'])
        a_res = await pixivsion_article_parse(aid=aid, tags=tags)
        if a_res.success():
            if not notice_group:
                continue
            article_data = a_res.result
            msg = f"新的Pixivision特辑！\n\n" \
                  f"《{article_data['title']}》\n\n{article_data['description']}\n{article_data['url']}"
            for group_id in notice_group:
                for _bot in bots:
                    try:
                        await _bot.call_api(api='send_group_msg', group_id=group_id, message=msg)
                    except Exception as e:
                        logger.warning(f"向群组: {group_id} 发送article简介信息失败, error: {repr(e)}")
                        continue
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
                for group_id in notice_group:
                    for _bot in bots:
                        try:
                            await _bot.call_api(api='send_group_msg', group_id=group_id, message=img_seg)
                            # 避免风控控制推送间隔
                            await asyncio.sleep(1)
                        except Exception as e:
                            logger.warning(f"向群组: {group_id} 发送图片内容失败, error: {repr(e)}")
                            continue
            logger.info(f"article: {aid} 图片已发送完成, 失败: {image_error}")
        else:
            logger.error(f"article: {aid} 信息解析失败, info: {a_res.info}")
    logger.info(f'pixivision_monitor: checking completed, 已处理新的article: {repr(new_article)}')

__all__ = [
    'scheduler'
]
