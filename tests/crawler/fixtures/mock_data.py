"""Mock数据 - 用于测试的模拟数据"""

from src.crawler.base import DataSource, RawPage

# Wiki API 模拟响应
MOCK_WIKI_CATEGORY_RESPONSE = {
    'query': {
        'categorymembers': [
            {'pageid': 1001, 'title': '肉丸'},
            {'pageid': 1002, 'title': '蜘蛛女皇'},
            {'pageid': 1003, 'title': '烹饪锅'},
        ]
    }
}

MOCK_WIKI_PAGE_RESPONSE = {
    'parse': {
        'pageid': 1001,
        'title': '肉丸',
        'displaytitle': '肉丸',
        'revid': 12345,
        'text': {
            '*': '''
            <div class="mw-parser-output">
                <aside class="portable-infobox">
                    <div class="pi-data">
                        <span class="pi-data-label">饥饿值</span>
                        <span class="pi-data-value">62.5</span>
                    </div>
                    <div class="pi-data">
                        <span class="pi-data-label">理智值</span>
                        <span class="pi-data-value">5</span>
                    </div>
                    <div class="pi-data">
                        <span class="pi-data-label">生命值</span>
                        <span class="pi-data-value">3</span>
                    </div>
                </aside>
                <p>肉丸是一种可以用烹饪锅制作的食物。</p>
                <h2>配方</h2>
                <p>材料: 肉度 >= 0.5, 填充物</p>
                <p>烹饪时间: 15秒</p>
                <h2>用法</h2>
                <p>肉丸是新手最常用的食物之一。</p>
            </div>
            '''
        },
        'categories': [
            {'*': '食物'},
            {'*': '烹饪锅食谱'},
        ],
    }
}

MOCK_WIKI_BOSS_PAGE_RESPONSE = {
    'parse': {
        'pageid': 1002,
        'title': '蜘蛛女皇',
        'displaytitle': '蜘蛛女皇',
        'revid': 12346,
        'text': {
            '*': '''
            <div class="mw-parser-output">
                <aside class="portable-infobox">
                    <div class="pi-data">
                        <span class="pi-data-label">生命值</span>
                        <span class="pi-data-value">2500</span>
                    </div>
                    <div class="pi-data">
                        <span class="pi-data-label">伤害</span>
                        <span class="pi-data-value">80</span>
                    </div>
                </aside>
                <p>蜘蛛女皇是一种Boss级别的生物。</p>
                <h2>战斗策略</h2>
                <p>蜘蛛女皇会召唤小蜘蛛，建议先清理小蜘蛛。</p>
            </div>
            '''
        },
        'categories': [
            {'*': 'Boss'},
            {'*': '生物'},
        ],
    }
}

# 贴吧模拟数据
MOCK_TIEBA_LIST_HTML = '''
<html>
<body>
<li class="j_thread_list" data-tid="12345">
    <a class="j_th_tit" href="/p/12345">新手攻略：肉丸配方详解</a>
    <span class="tb_icon_author">作者A</span>
    <span class="threadlist_rep_num">100</span>
</li>
<li class="j_thread_list" data-tid="12346">
    <a class="j_th_tit" href="/p/12346">Boss攻略：蜘蛛女皇</a>
    <span class="tb_icon_author">作者B</span>
    <span class="threadlist_rep_num">50</span>
</li>
</body>
</html>
'''

MOCK_TIEBA_POST_HTML = '''
<html>
<body>
<div class="l_post">
    <span class="louzhubiaoshi_wrap"></span>
    <div class="d_post_content">
        肉丸是新手必学的食谱之一。

        配方：怪物肉 × 1 + 浆果 × 3

        或者：怪物肉 × 1 + 冰块 × 3
    </div>
</div>
<div class="l_post">
    <div class="d_post_content">
        感谢分享！
    </div>
</div>
<div class="l_post">
    <span class="louzhubiaoshi_wrap"></span>
    <div class="d_post_content">
        补充一下，肉丸还可以用大肉做。
    </div>
</div>
</body>
</html>
'''

# Steam模拟数据
MOCK_STEAM_LIST_HTML = '''
<html>
<body>
<div class="workshopItem">
    <a class="ugc" href="https://steamcommunity.com/sharedfiles/filedetails/?id=123456">
        <div class="workshopItemTitle">饥荒新手完全指南</div>
    </a>
    <div class="workshopItemAuthorName">Author1</div>
</div>
<div class="workshopItem">
    <a class="ugc" href="https://steamcommunity.com/sharedfiles/filedetails/?id=123457">
        <div class="workshopItemTitle">Boss攻略合集</div>
    </a>
    <div class="workshopItemAuthorName">Author2</div>
</div>
</body>
</html>
'''

MOCK_STEAM_GUIDE_HTML = '''
<html>
<body>
<div class="workshopItemTitle">饥荒新手完全指南</div>
<div class="workshopItemAuthorName"><a>Author1</a></div>
<div class="guide subSections">
    <div class="subSection">
        <div class="subSectionTitle">基础介绍</div>
        <div class="subSectionDesc">
            饥荒是一款生存游戏，玩家需要收集资源、建造基地、对抗怪物。
        </div>
    </div>
    <div class="subSection">
        <div class="subSectionTitle">食物配方</div>
        <div class="subSectionDesc">
            肉丸: 怪物肉 × 1 + 填充物 × 3
            培根煎蛋: 蛋 × 2 + 肉 × 1 + 蔬菜 × 0.5
        </div>
    </div>
</div>
</body>
</html>
'''


# 预构建的RawPage对象
def get_mock_raw_page_wiki() -> RawPage:
    """获取模拟的Wiki原始页面"""
    return RawPage(
        source=DataSource.WIKI_GG,
        source_id='1001',
        title='肉丸',
        url='https://dontstarve.wiki.gg/zh/wiki/肉丸',
        content='肉丸是一种可以用烹饪锅制作的食物。配方：肉度 >= 0.5, 填充物。烹饪时间: 15秒。',
        html_content=MOCK_WIKI_PAGE_RESPONSE['parse']['text']['*'],
        categories=['食物', '烹饪锅食谱'],
        raw_data=MOCK_WIKI_PAGE_RESPONSE,
    )


def get_mock_raw_page_tieba() -> RawPage:
    """获取模拟的贴吧原始页面"""
    return RawPage(
        source=DataSource.TIEBA,
        source_id='12345',
        title='新手攻略：肉丸配方详解',
        url='https://tieba.baidu.com/p/12345',
        content='肉丸是新手必学的食谱之一。配方：怪物肉 × 1 + 浆果 × 3',
        html_content=MOCK_TIEBA_POST_HTML,
        categories=['贴吧攻略'],
        extra={'forum': '饥荒'},
    )


def get_mock_raw_page_steam() -> RawPage:
    """获取模拟的Steam原始页面"""
    return RawPage(
        source=DataSource.STEAM,
        source_id='123456',
        title='饥荒新手完全指南',
        url='https://steamcommunity.com/sharedfiles/filedetails/?id=123456',
        content='饥荒是一款生存游戏。肉丸: 怪物肉 × 1 + 填充物 × 3',
        html_content=MOCK_STEAM_GUIDE_HTML,
        categories=['Steam指南'],
    )
