"""
@Author         : Ailitonia
@Date           : 2026/9/27 23:30
@FileName       : helper
@Project        : omega-miya
@Description    : Twitter API 数据解析辅助
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import Any

from pydantic import ValidationError

from .misc import find_dict
from .model import TwitterTweet


def parse_tweet_from_data(data: dict[str, Any]) -> TwitterTweet | None:
    """从时间线条目/推文结果中解析推文数据

    无法解析时(墓碑推文/数据缺失/数据校验失败)返回 None
    """
    tweet_data_ = find_dict(data, 'result', True)
    if not tweet_data_:
        return None
    tweet_data = tweet_data_[0]
    if not isinstance(tweet_data, dict):
        return None
    if tweet_data.get('__typename') == 'TweetTombstone':
        return None
    if 'tweet' in tweet_data:
        tweet_data = tweet_data['tweet']
    if not isinstance(tweet_data, dict) or 'core' not in tweet_data:
        return None
    user_results = tweet_data['core'].get('user_results')
    if not isinstance(user_results, dict) or 'result' not in user_results:
        return None
    if 'legacy' not in tweet_data:
        return None

    try:
        return TwitterTweet.model_validate(tweet_data)
    except ValidationError:
        return None


__all__ = [
    'parse_tweet_from_data',
]
