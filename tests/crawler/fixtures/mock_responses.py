"""扩展Mock数据 - 用于边界情况测试"""

from src.crawler.base import DataSource, RawPage


# ============ 贴吧边界情况 ============

MOCK_TIEBA_EMPTY_LIST_HTML = '''
<html>
<body>
<!-- 空的帖子列表 -->
</body>
</html>
'''

MOCK_TIEBA_MALFORMED_HTML = '''
<html>
<body>
<li class="j_thread_list">
    <!-- 缺少data-tid属性 -->
    <a class="j_th_tit" href="/p/12345">标题</a>
</li>
<li class="j_thread_list" data-tid="">
    <!-- 空的data-tid -->
    <a class="j_th_tit" href="/p/12346">标题2</a>
</li>
<li class="j_thread_list" data-tid="12347">
    <!-- 缺少标题元素 -->
    <span class="tb_icon_author">作者</span>
</li>
</body>
</html>
'''

MOCK_TIEBA_POST_MULTI_PAGE_HTML_PAGE1 = '''
<html>
<body>
<div class="l_post">
    <span class="louzhubiaoshi_wrap"></span>
    <div class="d_post_content">
        第一页楼主内容
    </div>
</div>
<div class="l_post">
    <div class="d_post_content">
        第一页普通回复
    </div>
</div>
<a class="next" href="/p/12345?pn=2">下一页</a>
</body>
</html>
'''

MOCK_TIEBA_POST_MULTI_PAGE_HTML_PAGE2 = '''
<html>
<body>
<div class="l_post">
    <span class="louzhubiaoshi_wrap"></span>
    <div class="d_post_content">
        第二页楼主内容
    </div>
</div>
</body>
</html>
'''

MOCK_TIEBA_POST_EMPTY_HTML = '''
<html>
<body>
<!-- 没有任何楼层 -->
</body>
</html>
'''

MOCK_TIEBA_POST_LZ_ONLY_HTML = '''
<html>
<body>
<div class="l_post">
    <span class="louzhubiaoshi_wrap"></span>
    <div class="d_post_content">
        楼主发布的内容
    </div>
</div>
<div class="l_post">
    <div class="d_post_content">
        这是普通用户的回复
    </div>
</div>
<div class="l_post">
    <span class="louzhubiaoshi_wrap"></span>
    <div class="d_post_content">
        楼主的第二条回复
    </div>
</div>
</body>
</html>
'''


# ============ Steam边界情况 ============

MOCK_STEAM_EMPTY_LIST_HTML = '''
<html>
<body>
<!-- 空的指南列表 -->
</body>
</html>
'''

MOCK_STEAM_GUIDE_NO_SECTIONS_HTML = '''
<html>
<body>
<div class="workshopItemTitle">简单指南</div>
<div class="workshopItemDescription">
    这是一个没有章节结构的简单指南。
    只有一段纯文本描述。
</div>
</body>
</html>
'''

MOCK_STEAM_GUIDE_EMPTY_HTML = '''
<html>
<body>
<div class="workshopItemTitle">空内容指南</div>
<!-- 没有任何正文内容 -->
</body>
</html>
'''

MOCK_STEAM_GUIDE_WITH_TAGS_HTML = '''
<html>
<body>
<div class="workshopItemTitle">带标签的指南</div>
<div class="workshopItemDescription">指南简介</div>
<div class="guide subSections">
    <div class="subSection">
        <div class="subSectionTitle">章节1</div>
        <div class="subSectionDesc">内容1</div>
    </div>
</div>
<a class="workshopItemTag">攻略</a>
<a class="workshopItemTag">新手</a>
<a class="workshopItemTag">食物</a>
</body>
</html>
'''

MOCK_STEAM_LIST_WITH_RATING_HTML = '''
<html>
<body>
<div class="workshopItem">
    <a class="ugc" href="https://steamcommunity.com/sharedfiles/filedetails/?id=999999">
        <div class="workshopItemTitle">高评分指南</div>
    </a>
    <div class="workshopItemAuthorName">TopAuthor</div>
    <img class="fileRating" src="https://store.steampowered.com/5star.png">
</div>
</body>
</html>
'''


# ============ Wiki边界情况 ============

MOCK_WIKI_REDIRECT_RESPONSE = {
    'query': {
        'redirects': [
            {'from': '肉丸子', 'to': '肉丸'}
        ],
        'pages': {
            '1001': {
                'pageid': 1001,
                'title': '肉丸'
            }
        }
    }
}

MOCK_WIKI_MISSING_PAGE_RESPONSE = {
    'error': {
        'code': 'missingtitle',
        'info': '页面不存在'
    }
}

MOCK_WIKI_EMPTY_CATEGORY_RESPONSE = {
    'query': {
        'categorymembers': []
    }
}

MOCK_WIKI_CONTINUATION_RESPONSE = {
    'continue': {
        'cmcontinue': 'page|12345|继续标记',
        'continue': '-||'
    },
    'query': {
        'categorymembers': [
            {'pageid': 1001, 'title': '页面1'},
            {'pageid': 1002, 'title': '页面2'},
        ]
    }
}

MOCK_WIKI_PAGE_MALFORMED_INFOBOX = {
    'parse': {
        'pageid': 2001,
        'title': '畸形页面',
        'text': {
            '*': '''
            <div class="mw-parser-output">
                <aside class="portable-infobox">
                    <div class="pi-data">
                        <!-- 缺少label -->
                        <span class="pi-data-value">100</span>
                    </div>
                    <div class="pi-data">
                        <span class="pi-data-label"></span>
                        <!-- 空label -->
                        <span class="pi-data-value">50</span>
                    </div>
                </aside>
                <p>这是一个信息框畸形的页面。</p>
            </div>
            '''
        },
        'categories': []
    }
}

MOCK_WIKI_PAGE_NO_INFOBOX = {
    'parse': {
        'pageid': 2002,
        'title': '无信息框页面',
        'text': {
            '*': '''
            <div class="mw-parser-output">
                <p>这是一个没有信息框的普通页面。</p>
                <h2>章节1</h2>
                <p>章节1内容</p>
            </div>
            '''
        },
        'categories': [{'*': '游戏机制'}]
    }
}


# ============ 多种配方格式 ============

MOCK_RECIPE_FORMATS = {
    'format_chinese': '材料: 怪物肉 × 1 + 浆果 × 3',
    'format_chinese_x': '需要：怪物肉x1, 浆果x3',
    'format_english': 'Ingredients: Monster Meat x1, Berries x3',
    'format_template': '{{CookingRecipe|meat=1|filler=3|time=15}}',
    'format_table': '''
        <table class="recipe-table">
            <tr><td>怪物肉</td><td>1</td></tr>
            <tr><td>浆果</td><td>3</td></tr>
        </table>
    ''',
}


# ============ 畸形HTML测试数据 ============

MOCK_MALFORMED_HTML_UNCLOSED_TAGS = '''
<html>
<body>
<div class="content">
    <p>未闭合的段落
    <span>未闭合的span
    <div>未闭合的div
</body>
</html>
'''

MOCK_MALFORMED_HTML_UNICODE = '''
<html>
<body>
<div class="content">
    内容包含特殊字符：🎮 饥荒游戏 💀 死亡 ❤️ 生命
    还有乱码：\x00\x01\x02
</div>
</body>
</html>
'''

MOCK_MALFORMED_HTML_NESTED = '''
<html>
<body>
<div class="content">
    <table>
        <tr>
            <td>
                <div>
                    <p>
                        深度嵌套内容
                    </p>
                </div>
            </td>
        </tr>
    </table>
</div>
</body>
</html>
'''


# ============ 预构建的RawPage对象 ============

def get_mock_raw_page_tieba_empty() -> RawPage:
    """获取空内容的贴吧页面"""
    return RawPage(
        source=DataSource.TIEBA,
        source_id='99999',
        title='空帖子',
        url='https://tieba.baidu.com/p/99999',
        content='',
        html_content=MOCK_TIEBA_POST_EMPTY_HTML,
        categories=['贴吧攻略'],
        extra={'forum': '饥荒'},
    )


def get_mock_raw_page_steam_no_sections() -> RawPage:
    """获取无章节的Steam指南"""
    return RawPage(
        source=DataSource.STEAM,
        source_id='888888',
        title='简单指南',
        url='https://steamcommunity.com/sharedfiles/filedetails/?id=888888',
        content='这是一个没有章节结构的简单指南。',
        html_content=MOCK_STEAM_GUIDE_NO_SECTIONS_HTML,
        categories=['Steam指南'],
    )


def get_mock_raw_page_wiki_malformed() -> RawPage:
    """获取畸形信息框的Wiki页面"""
    return RawPage(
        source=DataSource.WIKI_GG,
        source_id='2001',
        title='畸形页面',
        url='https://dontstarve.wiki.gg/zh/wiki/畸形页面',
        content='这是一个信息框畸形的页面。',
        html_content=MOCK_WIKI_PAGE_MALFORMED_INFOBOX['parse']['text']['*'],
        categories=[],
        raw_data=MOCK_WIKI_PAGE_MALFORMED_INFOBOX,
    )


def get_mock_raw_page_wiki_no_infobox() -> RawPage:
    """获取无信息框的Wiki页面"""
    return RawPage(
        source=DataSource.WIKI_GG,
        source_id='2002',
        title='无信息框页面',
        url='https://dontstarve.wiki.gg/zh/wiki/无信息框页面',
        content='这是一个没有信息框的普通页面。章节1内容',
        html_content=MOCK_WIKI_PAGE_NO_INFOBOX['parse']['text']['*'],
        categories=['游戏机制'],
        raw_data=MOCK_WIKI_PAGE_NO_INFOBOX,
    )
