"""
@Author         : Ailitonia
@Date           : 2025/8/23 13:49:20
@FileName       : scenario_app.py
@Project        : omega-miya
@Description    : 内置场景应用
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from .image_description import ImageDescriptionApp
from .translate import TranslateApp
from .web_page_description import WebPageDescriptionApp


__all__ = [
    'ImageDescriptionApp',
    'TranslateApp',
    'WebPageDescriptionApp',
]
