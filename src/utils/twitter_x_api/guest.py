"""
@Author         : Ailitonia
@Date           : 2026/9/27 23:03
@FileName       : guest
@Project        : omega-miya
@Description    : Twitter 访客 API
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from typing import Any

from pydantic import ValidationError

from src.exception import WebSourceException
from .api_base import BaseTwitterAPI
from .consts import (
    FEATURES,
    TWEET_RESULT_BY_REST_ID_FEATURES,
    TWEET_RESULT_BY_REST_ID_URL,
    USER_BY_REST_ID_URL,
    USER_BY_SCREEN_NAME_URL,
    USER_FEATURES,
    USER_HIGHLIGHTS_TWEETS_FEATURES,
    USER_HIGHLIGHTS_TWEETS_URL,
    USER_TWEETS_URL,
)
from .helper import parse_tweet_from_data
from .misc import find_dict, find_entry_by_type
from .model import TwitterHighlightTweetsResult, TwitterTweet, TwitterUser


class TwitterGuest(BaseTwitterAPI):
    """Twitter 访客接口"""

    @classmethod
    async def activate(cls) -> str:
        """激活访客会话, 生成新的访客令牌"""
        return await cls._activate_guest()

    @staticmethod
    def _extract_user_result(response: Any, usage: str) -> dict[str, Any]:
        """从用户查询接口返回中提取用户数据, 数据缺失时抛出异常"""
        user_data = None
        if isinstance(response, dict) and isinstance(response.get('data'), dict):
            user = response['data'].get('user')
            if isinstance(user, dict) and isinstance(user.get('result'), dict):
                user_data = user['result']
        if user_data is None:
            raise WebSourceException(400, f'{usage} failed, user data not found in response, {repr(response)[:500]}')
        return user_data

    @staticmethod
    def _parse_user_result(user_data: dict[str, Any], usage: str) -> TwitterUser:
        """将用户数据解析为 TwitterUser, 数据残缺(如用户不可用)时抛出异常"""
        try:
            return TwitterUser.model_validate(user_data)
        except ValidationError as e:
            raise WebSourceException(400, f'{usage} failed, user data parse error, {e}') from e

    @classmethod
    async def get_user_by_screen_name(cls, screen_name: str) -> TwitterUser:
        """通过 screen_name 获取用户数据"""
        variables = {
            'screen_name': screen_name,
            'withSafetyModeUserFields': False,
        }
        extra_params = {
            'fieldToggles': {'withAuxiliaryUserLabels': False},
        }
        response = await cls._request_gql_api(
            url=USER_BY_SCREEN_NAME_URL,
            variables=variables,
            features=USER_FEATURES,
            extra_params=extra_params,
        )
        user_data = cls._extract_user_result(response, f'Query user(screen_name={screen_name})')
        return cls._parse_user_result(user_data, f'Query user(screen_name={screen_name})')

    @classmethod
    async def get_user_by_id(cls, user_id: str) -> TwitterUser:
        """通过用户 ID 获取用户数据"""
        variables = {
            'userId': str(user_id),
            'withSafetyModeUserFields': True,
        }
        response = await cls._request_gql_api(
            url=USER_BY_REST_ID_URL,
            variables=variables,
            features=USER_FEATURES,
        )
        user_data = cls._extract_user_result(response, f'Query user(id={user_id})')
        return cls._parse_user_result(user_data, f'Query user(id={user_id})')

    @classmethod
    async def get_user_tweets(cls, user_id: str, count: int = 40) -> list[TwitterTweet]:
        """获取用户推文时间线

        :param user_id: 用户 ID(可通过 get_user_by_screen_name 获取)
        :param count: 获取推文数量
        """
        variables = {
            'userId': str(user_id),
            'count': count,
            'includePromotedContent': True,
            'withQuickPromoteEligibilityTweetFields': True,
            'withVoice': True,
            'withV2Timeline': True,
        }
        response = await cls._request_gql_api(
            url=USER_TWEETS_URL,
            variables=variables,
            features=FEATURES,
        )

        instructions_ = find_dict(response, 'instructions', True)
        if not instructions_ or not isinstance(instructions_[0], list):
            return []
        instruction = find_entry_by_type(instructions_[0], 'TimelineAddEntries')
        if instruction is None or not isinstance(instruction.get('entries'), list):
            return []

        results = []
        for item in instruction['entries']:
            if not isinstance(item, dict):
                continue
            entry_id = item.get('entryId')
            if not isinstance(entry_id, str):
                continue
            if not entry_id.startswith(('tweet', 'profile-conversation', 'profile-grid')):
                continue
            tweet = parse_tweet_from_data(item)
            if tweet is None:
                continue
            results.append(tweet)

        return results

    @classmethod
    async def get_tweet_by_id(cls, tweet_id: str) -> TwitterTweet:
        """通过推文 ID 获取推文数据"""
        variables = {
            'tweetId': str(tweet_id),
            'withCommunity': False,
            'includePromotedContent': False,
            'withVoice': False,
        }
        extra_params = {
            'fieldToggles': {
                'withArticleRichContentState': True,
                'withArticlePlainText': False,
                'withGrokAnalyze': False,
            },
        }
        response = await cls._request_gql_api(
            url=TWEET_RESULT_BY_REST_ID_URL,
            variables=variables,
            features=TWEET_RESULT_BY_REST_ID_FEATURES,
            extra_params=extra_params,
        )
        tweet = parse_tweet_from_data(response)
        if tweet is None:
            raise WebSourceException(404, f'Query tweet(id={tweet_id}) failed, tweet data not found in response')
        return tweet

    @classmethod
    async def get_user_highlights_tweets(
            cls,
            user_id: str,
            count: int = 20,
            cursor: str | None = None,
    ) -> TwitterHighlightTweetsResult:
        """获取用户高光推文

        :param user_id: 用户 ID(可通过 get_user_by_screen_name 获取)
        :param count: 获取推文数量
        :param cursor: 翻页游标
        """
        variables = {
            'userId': str(user_id),
            'count': count,
            'includePromotedContent': True,
            'withVoice': True,
        }
        if cursor is not None:
            variables['cursor'] = cursor
        response = await cls._request_gql_api(
            url=USER_HIGHLIGHTS_TWEETS_URL,
            variables=variables,
            features=USER_HIGHLIGHTS_TWEETS_FEATURES,
        )

        instructions = None
        if isinstance(response, dict) and isinstance(response.get('data'), dict):
            instructions = find_dict(response['data'], 'instructions', True)
        instruction = (
            find_entry_by_type(instructions[0], 'TimelineAddEntries')
            if instructions and isinstance(instructions[0], list)
            else None
        )
        if instruction is None or not isinstance(instruction.get('entries'), list):
            return TwitterHighlightTweetsResult()

        tweets = []
        previous_cursor = None
        next_cursor = None
        for entry in instruction['entries']:
            if not isinstance(entry, dict):
                continue
            entry_id = entry.get('entryId')
            if not isinstance(entry_id, str):
                continue
            if entry_id.startswith('tweet'):
                tweet = parse_tweet_from_data(entry)
                if tweet is not None:
                    tweets.append(tweet)
            elif entry_id.startswith('cursor-top'):
                content = entry.get('content')
                previous_cursor = content.get('value') if isinstance(content, dict) else None
            elif entry_id.startswith('cursor-bottom'):
                content = entry.get('content')
                next_cursor = content.get('value') if isinstance(content, dict) else None

        return TwitterHighlightTweetsResult(
            tweets=tweets,
            next_cursor=next_cursor,
            previous_cursor=previous_cursor,
        )


__all__ = [
    'TwitterGuest',
]
