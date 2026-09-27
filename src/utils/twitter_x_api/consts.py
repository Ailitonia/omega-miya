"""
@Author         : Ailitonia
@Date           : 2026/9/27 23:30
@FileName       : consts
@Project        : omega-miya
@Description    : Twitter API 常量(端点/公共 Token/GraphQL Features)
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

DOMAIN = 'x.com'
"""X(Twitter) 主站域名"""

TOKEN = 'AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA'
"""X(Twitter) 网页端公共 Bearer Token, 所有客户端共用, 无需修改"""

DEFAULT_LANGUAGE = 'en-US'
"""API 请求默认语言"""

GUEST_ACTIVATE_URL = f'https://api.{DOMAIN}/1.1/guest/activate.json'
"""访客令牌激活端点(v1.1)"""

USER_BY_SCREEN_NAME_URL = f'https://{DOMAIN}/i/api/graphql/NimuplG1OB7Fd2btCLdBOw/UserByScreenName'
"""GraphQL: 通过 screen_name 获取用户"""
USER_BY_REST_ID_URL = f'https://{DOMAIN}/i/api/graphql/tD8zKvQzwY3kdx5yz6YmOw/UserByRestId'
"""GraphQL: 通过用户 ID 获取用户"""
USER_TWEETS_URL = f'https://{DOMAIN}/i/api/graphql/QWF3SzpHmykQHsQMixG0cg/UserTweets'
"""GraphQL: 获取用户推文时间线"""
USER_HIGHLIGHTS_TWEETS_URL = f'https://{DOMAIN}/i/api/graphql/tHFm_XZc_NNi-CfUThwbNw/UserHighlightsTweets'
"""GraphQL: 获取用户高光推文"""
TWEET_RESULT_BY_REST_ID_URL = f'https://{DOMAIN}/i/api/graphql/Xl5pC_lBk_gcO2ItU39DQw/TweetResultByRestId'
"""GraphQL: 通过推文 ID 获取推文"""

FEATURES: dict[str, bool] = {
    'creator_subscriptions_tweet_preview_api_enabled': True,
    'c9s_tweet_anatomy_moderator_badge_enabled': True,
    'tweetypie_unmention_optimization_enabled': True,
    'responsive_web_edit_tweet_api_enabled': True,
    'graphql_is_translatable_rweb_tweet_is_translatable_enabled': True,
    'view_counts_everywhere_api_enabled': True,
    'longform_notetweets_consumption_enabled': True,
    'responsive_web_twitter_article_tweet_consumption_enabled': True,
    'tweet_awards_web_tipping_enabled': False,
    'longform_notetweets_rich_text_read_enabled': True,
    'longform_notetweets_inline_media_enabled': True,
    'rweb_video_timestamps_enabled': True,
    'responsive_web_graphql_exclude_directive_enabled': True,
    'verified_phone_label_enabled': False,
    'freedom_of_speech_not_reach_fetch_enabled': True,
    'standardized_nudges_misinfo': True,
    'tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled': True,
    'responsive_web_media_download_video_enabled': False,
    'responsive_web_graphql_skip_user_profile_image_extensions_enabled': False,
    'responsive_web_graphql_timeline_navigation_enabled': True,
    'responsive_web_enhance_cards_enabled': False,
}
"""通用 GraphQL Features(用户推文时间线等接口使用)"""

USER_FEATURES: dict[str, bool] = {
    'hidden_profile_likes_enabled': True,
    'hidden_profile_subscriptions_enabled': True,
    'responsive_web_graphql_exclude_directive_enabled': True,
    'verified_phone_label_enabled': False,
    'subscriptions_verification_info_is_identity_verified_enabled': True,
    'subscriptions_verification_info_verified_since_enabled': True,
    'highlights_tweets_tab_ui_enabled': True,
    'responsive_web_twitter_article_notes_tab_enabled': False,
    'creator_subscriptions_tweet_preview_api_enabled': True,
    'responsive_web_graphql_skip_user_profile_image_extensions_enabled': False,
    'responsive_web_graphql_timeline_navigation_enabled': True,
}
"""用户查询接口 GraphQL Features"""

USER_HIGHLIGHTS_TWEETS_FEATURES: dict[str, bool] = {
    'rweb_tipjar_consumption_enabled': True,
    'responsive_web_graphql_exclude_directive_enabled': True,
    'verified_phone_label_enabled': False,
    'creator_subscriptions_tweet_preview_api_enabled': True,
    'responsive_web_graphql_timeline_navigation_enabled': True,
    'responsive_web_graphql_skip_user_profile_image_extensions_enabled': False,
    'communities_web_enable_tweet_community_results_fetch': True,
    'c9s_tweet_anatomy_moderator_badge_enabled': True,
    'articles_preview_enabled': True,
    'tweetypie_unmention_optimization_enabled': True,
    'responsive_web_edit_tweet_api_enabled': True,
    'graphql_is_translatable_rweb_tweet_is_translatable_enabled': True,
    'view_counts_everywhere_api_enabled': True,
    'longform_notetweets_consumption_enabled': True,
    'responsive_web_twitter_article_tweet_consumption_enabled': True,
    'tweet_awards_web_tipping_enabled': False,
    'creator_subscriptions_quote_tweet_preview_enabled': False,
    'freedom_of_speech_not_reach_fetch_enabled': True,
    'standardized_nudges_misinfo': True,
    'tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled': True,
    'rweb_video_timestamps_enabled': True,
    'longform_notetweets_rich_text_read_enabled': True,
    'longform_notetweets_inline_media_enabled': True,
    'responsive_web_enhance_cards_enabled': False,
}
"""用户高光推文接口 GraphQL Features"""

TWEET_RESULT_BY_REST_ID_FEATURES: dict[str, bool] = {
    'creator_subscriptions_tweet_preview_api_enabled': True,
    'communities_web_enable_tweet_community_results_fetch': True,
    'c9s_tweet_anatomy_moderator_badge_enabled': True,
    'articles_preview_enabled': True,
    'tweetypie_unmention_optimization_enabled': True,
    'responsive_web_edit_tweet_api_enabled': True,
    'graphql_is_translatable_rweb_tweet_is_translatable_enabled': True,
    'view_counts_everywhere_api_enabled': True,
    'longform_notetweets_consumption_enabled': True,
    'responsive_web_twitter_article_tweet_consumption_enabled': True,
    'tweet_awards_web_tipping_enabled': False,
    'creator_subscriptions_quote_tweet_preview_enabled': False,
    'freedom_of_speech_not_reach_fetch_enabled': True,
    'standardized_nudges_misinfo': True,
    'tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled': True,
    'rweb_video_timestamps_enabled': True,
    'longform_notetweets_rich_text_read_enabled': True,
    'longform_notetweets_inline_media_enabled': True,
    'rweb_tipjar_consumption_enabled': True,
    'responsive_web_graphql_exclude_directive_enabled': True,
    'verified_phone_label_enabled': False,
    'responsive_web_graphql_skip_user_profile_image_extensions_enabled': False,
    'responsive_web_graphql_timeline_navigation_enabled': True,
    'responsive_web_enhance_cards_enabled': False,
}
"""单条推文查询接口 GraphQL Features"""

__all__ = [
    'DEFAULT_LANGUAGE',
    'DOMAIN',
    'FEATURES',
    'GUEST_ACTIVATE_URL',
    'TOKEN',
    'TWEET_RESULT_BY_REST_ID_FEATURES',
    'TWEET_RESULT_BY_REST_ID_URL',
    'USER_BY_REST_ID_URL',
    'USER_BY_SCREEN_NAME_URL',
    'USER_FEATURES',
    'USER_HIGHLIGHTS_TWEETS_FEATURES',
    'USER_HIGHLIGHTS_TWEETS_URL',
    'USER_TWEETS_URL',
]
