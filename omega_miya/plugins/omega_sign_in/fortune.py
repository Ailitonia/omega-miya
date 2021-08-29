import datetime
import random
import hashlib


do_something = [
    {'name': '看直播', 'good': '喜欢的V开歌回啦', 'bad': '喜欢的V咕了一整天'},
    {'name': '打轴', 'good': '一次性过', 'bad': '"谁说话这么难懂"'},
    {'name': '剪辑', 'good': '灵感爆发', 'bad': '一团乱麻'},
    {'name': '校对', 'good': '变成无情的审轴机器', 'bad': '被闪轴闪瞎眼'},
    {'name': '浏览Pixiv', 'good': '发现符合xp的涩图', 'bad': '找不到想要的涩图'},
    {'name': '打SC', 'good': '享受石油佬的乐趣', 'bad': '吃土中'},
    {'name': '吃人', 'good': '你面前这位有成为神龙的潜质', 'bad': '这人会用Aegisub吗？'},
    {'name': '背单词', 'good': '这次六级肯定过', 'bad': '背完50个忘了45个'},
    {'name': '打DOTA', 'good': '天梯5000分不是梦', 'bad': '你会遇到猪一样的队友'},
    {'name': '翘课', 'good': '老师不会点名', 'bad': '老师准会抽到你来回答问题'},
    {'name': '做作业', 'good': '做的每个都对', 'bad': '做一个做错一个'},
    {'name': '锻炼一下身体', 'good': '身体健康, 更加性福', 'bad': '能量没消耗多少, 吃得却更多'},
    {'name': '浏览成人网站', 'good': '重拾对生活的信心', 'bad': '你会心神不宁'},
    {'name': '修复BUG', 'good': '你今天对BUG的嗅觉大大提高', 'bad': '新产生的BUG将比修复的更多'},
    {'name': '上AB站', 'good': '还需要理由吗?', 'bad': '满屏兄贵亮瞎你的眼'},
    {'name': '打LOL', 'good': '你将有如神助', 'bad': '你会被虐的很惨'},
    {'name': '穿女装', 'good': '你会得到很多炙热的目光', 'bad': '被父母看到'},
    {'name': '组模型', 'good': '今天的喷漆会很完美', 'bad': '精神不集中板件被剪断了'},
    {'name': '熬夜', 'good': '夜间的效率更高', 'bad': '明天有很重要的事'},
    {'name': '抚摸猫咪', 'good': '才不是特意蹭你的呢', 'bad': '死开! 愚蠢的人类'},
    {'name': '烹饪', 'good': '黑暗料理界就由我来打败', 'bad': '难道这就是……仰望星空派?'},
    {'name': '告白', 'good': '其实我也喜欢你好久了', 'bad': '对不起, 你是一个好人'},
    {'name': '追新番', 'good': '完结之前我绝不会死', 'bad': '会被剧透'},
    {'name': '日麻', 'good': '立直一发自摸！', 'bad': '碰喵吃喵杠喵荣喵！'},
    {'name': '音游', 'good': 'FCACFRPR不过如此', 'bad': '又双叒叕LOST了...'},
    {'name': '向大佬请教', 'good': '太棒了，学到许多', 'bad': '太棒了，什么都没学到'},
    {'name': '早起', 'good': '迎接第一缕阳光', 'bad': '才4点，再睡一会'},
    {'name': '早睡', 'good': '第二天精神饱满', 'bad': '失眠数羊画圈圈'},
    {'name': '入正版游戏', 'good': '买了痛三天，不买悔三年', 'bad': 'emmmm，汇率还是……'},
    {'name': '补旧作', 'good': '意外地对胃口', 'bad': '会踩雷'},
    {'name': '晾晒老婆（抱枕套）', 'good': '天気も晴れココロも晴れ', 'bad': '引发路人围观'},
    {'name': '不按攻略打', 'good': '居然是HAPPY END', 'bad': '碰到BAD END'},
    {'name': '观赏CG包', 'good': '社保。', 'bad': '还不去如看游戏剧情'},
    {'name': '研究黄油创作理论', 'good': '增进鉴赏水平', 'bad': '闲适玩家不需要这些'},
    {'name': '暴露性癖', 'good': '会引来很多趣味相同的变态', 'bad': '四斋蒸鹅心'},
    {'name': '施法', 'good': '传统手艺精进了', 'bad': '房间门关好了吗'},
    {'name': '刷新作动态', 'good': '喜欢的画师发了新图', 'bad': '发现游戏跳票'},
    {'name': '回味玩过的作品', 'good': '重温感动', 'bad': '还是先看看新作'},
    {'name': '出门走走', 'good': '宅久了要发霉', 'bad': '太陽が眩しすぎる'},
    {'name': '思考人生', 'good': '自己的幸福呢？', 'bad': '喵喵……喵？'},
    {'name': '撸猫', 'good': '啊……好爽', 'bad': '家里没有猫的洗洗睡吧'},
    {'name': '抽卡', 'good': '单抽出货', 'bad': '到井前一发出货'},
    {'name': '拼乐高', 'good': '顺利完工', 'bad': '发现少了一块零件'},
    {'name': '跳槽', 'good': '新工作待遇大幅提升', 'bad': '待遇还不如之前的'},
    {'name': '和女神聊天', 'good': '今天天气不错', 'bad': '我去洗澡了，呵呵'},
    {'name': '写开源库', 'good': '今天北斗七星汇聚，裤子造的又快又好', 'bad': '写好会发现github上已经有了更好的'},
    {'name': '给测试妹子埋个bug', 'good': '下辈子的幸福就靠这个bug了', 'bad': '妹子会认为你活和代码一样差'},
    {'name': '写单元测试', 'good': '写单元测试将减少出错', 'bad': '写单元测试会降低你的开发效率'},
    {'name': '洗澡', 'good': '你几天没洗澡了？', 'bad': '会把设计方面的灵感洗掉'},
    {'name': '白天上线', 'good': '今天白天上线是安全的', 'bad': '可能导致灾难性后果'},
    {'name': '重构', 'good': '代码质量得到提高', 'bad': '你很有可能会陷入泥潭'},
    {'name': '招人', 'good': '你面前这位有成为牛人的潜质', 'bad': '这人会写程序吗？'},
    {'name': '面试', 'good': '面试官今天心情很好', 'bad': '面试官不爽，会拿你出气'},
    {'name': '申请加薪', 'good': '老板今天心情很好', 'bad': '公司正在考虑裁员'},
    {'name': '提交代码', 'good': '遇到冲突的几率是最低的', 'bad': '会遇到的一大堆冲突'},
    {'name': '代码复审', 'good': '发现重要问题的几率大大增加', 'bad': '你什么问题都发现不了，白白浪费时间'},
    {'name': '晚上上线', 'good': '晚上是程序员精神最好的时候', 'bad': '你白天已经筋疲力尽了'},
    {'name': '乘电梯', 'good': '正好赶上打卡截止时间', 'bad': '电梯超载'},
    {'name': '复读', 'good': '有时候，人云亦云也是一种生存方式', 'bad': '你的对手是鸽子'},
    {'name': '肝爆', 'good': '努力使人进步，肝爆让人快乐', 'bad': '醒醒，限时活动没了'},
    {'name': '氪金', 'good': '早买早享受，晚买哭着求', 'bad': '第二天就 50% off'},
    {'name': '卖弱', 'good': '楚楚动人更容易打动群友', 'bad': 'Boy♂next♂door'},
    {'name': '唱脑力', 'good': '唱一次提升醒脑，唱两次精神百倍', 'bad': '会与复读机一起对群聊造成毁灭性打击'},
    {'name': '看手元', 'good': '从手元中获得一点音游经验', 'bad': '会被大佬闪瞎'},
    {'name': '录手元', 'good': '音游届的未来新星UP主就是你', 'bad': '打完歌才发现忘记开录像'},
    {'name': '挑战魔王曲', 'good': '一上来就是一个新纪录', 'bad': '有这点时间还不如干点别的'},
    {'name': '咕咕咕', 'good': '一时咕一时爽', 'bad': '会被抓起来，被群友强迫穿上女装'},
    {'name': '与群友水聊', 'good': '扶我起来我还能打字', 'bad': '一不小心就被大佬闪瞎'},
    {'name': '迫害大佬', 'good': '迫害是大佬进步的阶梯', 'bad': '亲爱的，你号没了'},
    {'name': '算命', 'good': '算啥都准', 'bad': '诸事不宜'},
    {'name': '成为魔法少女', 'good': '勇敢的烧酒啊快去拯救世界吧！', 'bad': '会掉头'}
]


def get_fortune(user_id: int) -> dict:
    # 用qq、日期生成随机种子
    random_seed_str = str([user_id, datetime.date.today()])
    md5 = hashlib.md5()
    md5.update(random_seed_str.encode('utf-8'))
    random_seed = md5.hexdigest()
    random.seed(random_seed)
    # 今日运势
    # 生成求签种子, 9分一级
    fortune_result = random.randint(1, 108)
    # 大吉・中吉・小吉・吉・半吉・末吉・末小吉・凶・小凶・半凶・末凶・大凶
    if fortune_result < 4:
        fortune_star = '☆' * 11
        fortune_text = '大凶'
    elif fortune_result < 9:
        fortune_star = '★' * 1 + '☆' * 10
        fortune_text = '末凶'
    elif fortune_result < 16:
        fortune_star = '★' * 2 + '☆' * 9
        fortune_text = '半凶'
    elif fortune_result < 25:
        fortune_star = '★' * 3 + '☆' * 8
        fortune_text = '小凶'
    elif fortune_result < 36:
        fortune_star = '★' * 4 + '☆' * 7
        fortune_text = '凶'
    elif fortune_result < 48:
        fortune_star = '★' * 5 + '☆' * 6
        fortune_text = '末小吉'
    elif fortune_result < 60:
        fortune_star = '★' * 6 + '☆' * 5
        fortune_text = '末吉'
    elif fortune_result < 72:
        fortune_star = '★' * 7 + '☆' * 4
        fortune_text = '半吉'
    elif fortune_result < 84:
        fortune_star = '★' * 8 + '☆' * 3
        fortune_text = '吉'
    elif fortune_result < 96:
        fortune_star = '★' * 9 + '☆' * 2
        fortune_text = '小吉'
    elif fortune_result < 102:
        fortune_star = '★' * 10 + '☆' * 1
        fortune_text = '中吉'
    else:
        fortune_star = '★' * 11
        fortune_text = '大吉'
    # 宜做和不宜做
    do_and_not = random.sample(do_something, k=4)

    result = {
        'fortune_star': fortune_star,
        'fortune_text': fortune_text,
        'do_1': f"{do_and_not[0]['name']} —— {do_and_not[0]['good']}",
        'do_2': f"{do_and_not[2]['name']} —— {do_and_not[2]['good']}",
        'not_do_1': f"{do_and_not[1]['name']} —— {do_and_not[1]['bad']}",
        'not_do_2': f"{do_and_not[3]['name']} —— {do_and_not[3]['bad']}"
    }
    return result
