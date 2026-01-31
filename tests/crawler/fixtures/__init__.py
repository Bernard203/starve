"""fixtures包初始化"""

from .mock_data import (
    MOCK_WIKI_CATEGORY_RESPONSE,
    MOCK_WIKI_PAGE_RESPONSE,
    MOCK_WIKI_BOSS_PAGE_RESPONSE,
    MOCK_TIEBA_LIST_HTML,
    MOCK_TIEBA_POST_HTML,
    MOCK_STEAM_LIST_HTML,
    MOCK_STEAM_GUIDE_HTML,
    get_mock_raw_page_wiki,
    get_mock_raw_page_tieba,
    get_mock_raw_page_steam,
)

__all__ = [
    'MOCK_WIKI_CATEGORY_RESPONSE',
    'MOCK_WIKI_PAGE_RESPONSE',
    'MOCK_WIKI_BOSS_PAGE_RESPONSE',
    'MOCK_TIEBA_LIST_HTML',
    'MOCK_TIEBA_POST_HTML',
    'MOCK_STEAM_LIST_HTML',
    'MOCK_STEAM_GUIDE_HTML',
    'get_mock_raw_page_wiki',
    'get_mock_raw_page_tieba',
    'get_mock_raw_page_steam',
]
