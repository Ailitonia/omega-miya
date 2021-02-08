import asyncio
from nonebot import logger, require, get_bots
from nonebot.adapters.cqhttp import MessageSegment
from omega_miya.utils.Omega_Base import DBSubscription, DBTable
from .utils import get_pixivsion_article, pixivsion_article_parse, fetch_image_b64
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
    hour='*/1',
    # minute='*/30',
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
    all_noitce_groups = []
    t = DBTable(table_name='Group')
    for item in t.list_col_with_condition('group_id', 'notice_permissions', 1).result:
        all_noitce_groups.append(int(item[0]))

    # 初始化tag黑名单
    block_tag_id = []
    block_tag_name = []
    for block_tag in TAG_BLOCK_LIST:
        block_tag_id.append(block_tag.get('id'))
        block_tag_name.append(block_tag.get('name'))

    # 提取数据库中已有article的id列表
    exist_article = []
    t = DBTable(table_name='Pixivision')
    for item in t.list_col('aid').result:
        exist_article.append(int(item[0]))

    # 获取最新一页pixivision的article
    new_article = []
    _res = await get_pixivsion_article()
    if _res.success() and not _res.result.get('error'):
        try:
            pixivsion_article = dict(_res.result)
            for article in pixivsion_article['body']['illustration']:
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
            return
    else:
        logger.error(f'pixivision_monitor: checking pixivision timeout or other error: {_res.info}')
        return

    if not new_article:
        logger.info(f'pixivision_monitor: checking completed, 没有新的article')
        return

    sub = DBSubscription(sub_type=8, sub_id=-1)
    # 获取订阅了该直播间的所有群
    sub_group = sub.sub_group_list().result
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
                tasks.append(fetch_image_b64(pid=pid))
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
