"""
@Author         : Ailitonia
@Date           : 2021/08/31 21:24
@FileName       : tarot_data.py
@Project        : nonebot2_miya 
@Description    : 塔罗卡牌及卡组数据 虽然这里看起来使用 json 会更好 但还是用 dataclass 硬编码了:(
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm 
"""

from typing import List
from dataclasses import dataclass, field, fields
from .tarot_typing import Element, Constellation, TarotCard, TarotPack


@dataclass
class Elements:
    earth: Element = field(default=Element(id=0, orig_name='Earth', name='土元素'), init=False)
    water: Element = field(default=Element(id=0, orig_name='Water', name='水元素'), init=False)
    air: Element = field(default=Element(id=0, orig_name='Air', name='风元素'), init=False)
    fire: Element = field(default=Element(id=0, orig_name='Fire', name='火元素'), init=False)
    aether: Element = field(default=Element(id=0, orig_name='Aether', name='以太'), init=False)


@dataclass
class Constellations:
    pluto: Constellation = field(default=Element(id=-9, orig_name='Pluto', name='冥王星'), init=False)
    neptunus: Constellation = field(default=Element(id=-8, orig_name='Neptunus', name='海王星'), init=False)
    uranus: Constellation = field(default=Element(id=-7, orig_name='Uranus', name='天王星'), init=False)
    saturn: Constellation = field(default=Element(id=-6, orig_name='Saturn', name='土星'), init=False)
    jupiter: Constellation = field(default=Element(id=-5, orig_name='Jupiter', name='木星'), init=False)
    mars: Constellation = field(default=Element(id=-4, orig_name='Mars', name='火星'), init=False)
    earth: Constellation = field(default=Element(id=-3, orig_name='Earth', name='地球'), init=False)
    moon: Constellation = field(default=Element(id=-10, orig_name='Moon', name='月亮'), init=False)
    venus: Constellation = field(default=Element(id=-2, orig_name='Venus', name='金星'), init=False)
    mercury: Constellation = field(default=Element(id=-1, orig_name='Mercury', name='水星'), init=False)
    sun: Constellation = field(default=Element(id=0, orig_name='Sun', name='太阳'), init=False)
    aries: Constellation = field(default=Element(id=1, orig_name='Aries', name='白羊座'), init=False)
    taurus: Constellation = field(default=Element(id=2, orig_name='Taurus', name='金牛座'), init=False)
    gemini: Constellation = field(default=Element(id=3, orig_name='Gemini', name='双子座'), init=False)
    cancer: Constellation = field(default=Element(id=4, orig_name='Cancer', name='巨蟹座'), init=False)
    leo: Constellation = field(default=Element(id=5, orig_name='Leo', name='狮子座'), init=False)
    virgo: Constellation = field(default=Element(id=6, orig_name='Virgo', name='室女座'), init=False)
    libra: Constellation = field(default=Element(id=7, orig_name='Libra', name='天秤座'), init=False)
    scorpio: Constellation = field(default=Element(id=8, orig_name='Scorpio', name='天蝎座'), init=False)
    sagittarius: Constellation = field(default=Element(id=9, orig_name='Sagittarius', name='人马座'), init=False)
    capricorn: Constellation = field(default=Element(id=10, orig_name='Capricorn', name='摩羯座'), init=False)
    aquarius: Constellation = field(default=Element(id=11, orig_name='Aquarius', name='宝瓶座'), init=False)
    pisces: Constellation = field(default=Element(id=12, orig_name='Pisces', name='双鱼座'), init=False)


@dataclass
class TarotCards:
    """
    所有卡牌
    每个属性都是一张牌
    """
    @classmethod
    def get_all_cards(cls) -> List[TarotCard]:
        """
        获取所有塔罗牌的列表
        :return: List[TarotCard]
        """
        return [field_.default for field_ in fields(cls) if field_.type == TarotCard]

    blank: TarotCard = field(default=TarotCard(
        id=-1, index='blank', type='special', orig_name='Blank', name='空白',
        intro='空白的卡面，似乎可以用来作为卡牌背面图案使用',
        words='',
        desc='', positive='', negative=''
    ), init=False)

    the_fool: TarotCard = field(default=TarotCard(
        id=0, index='the_fool', type='major_arcana', orig_name='The Fool', name='愚者',
        intro='愚人穿着色彩斑斓的服装，头上戴顶象征成功的桂冠，无视于前方的悬崖，昂首阔步向前行。他左手拿着一朵白玫瑰，白色象征纯洁，玫瑰象征热情。他的右手则轻轻握着一根杖，象征经验的包袱即系于其上。\n\n那根杖可不是普通的杖，它是一根权杖，象征力量。愚人脚边有只小白狗正狂吠着，似乎在提醒他要悬崖勒马，又好像随他一同起舞。无论如何，愚人仍旧保持着欢欣的神色，望向遥远的天空而非眼前的悬崖，好像悬崖下会有个天使扥住他似的，他就这样昂首阔步地向前走。远方的山脉象征他前方未知的旅程，白色的太阳自始至终都目睹着愚人的一举一动──他从哪里来？他往何处去？他又如何回来？',
        words='旅程',
        desc='',
        positive='盲目的、有勇气的、超越世俗的、展开新的阶段、有新的机会、追求自我的理想、展开一段旅行、超乎常人的勇气、漠视道德舆论的。',
        negative='过于盲目、不顾现实的、横冲直撞的、拒绝负担责任的、违背常理的、逃避的心态、一段危险的旅程、想法如孩童般天真幼稚的。'
    ), init=False)

    the_magician: TarotCard = field(default=TarotCard(
        id=1, index='the_magician', type='major_arcana', orig_name='The Magician (I)', name='魔术师',
        intro='魔法师高举拿着权杖的右手指向天，左手食指指向地，他本人就是沟通上天与地面的桥梁。他身前的桌上放着象征四要素的权杖、圣杯、宝剑与钱币，同时也代表塔罗牌的四个牌组。他身穿的大红袍子象征热情与主动，白色内衫表示纯洁与智慧的内在。缠绕他腰间的是一条青蛇，蛇虽然经常象征邪恶，但在这里代表的是智慧与启发。魔法师头顶上有个倒８符号，代表无限。画面前方和上方的红玫瑰象征热情，白百合象征智慧。此时，万事齐备，魔法师可以开始进行他的新计划了。和愚人牌同样鲜黄色的背景，预示未来成功的可能。\n\n魔法师桌上的工具，以前是装在愚人的行囊当中，象征正确的动机（圣杯）、清晰的计划（宝剑）、充沛的热情（权杖），以及确实的执行（五角星）的组合——对于达成目标而言，这是个相当强而有力的组合。红玫瑰象征热情或持久力，白色百合花则意味着纯洁的动机。作为皮带的这条蛇正吞食自己的尾巴，象征许多事情既无所谓开始，也无所谓结束。',
        words='创造',
        desc='',
        positive='成功的、有实力的、聪明能干的、擅长沟通的、机智过人的、唯我独尊的、企划能力强的、透过更好的沟通而获得智慧、运用智慧影响他人、学习能力强的、有教育和学术上的能力、表达技巧良好的。',
        negative='变魔术耍花招的、瞒骗的、失败的、狡猾的、善于谎言的、能力不足的、丧失信心的、以不正当手段获取认同的。'
    ), init=False)

    the_high_priestess: TarotCard = field(default=TarotCard(
        id=2, index='the_high_priestess', type='major_arcana', orig_name='The High Priestess (II)', name='女祭司',
        intro='女祭司端坐着，脚旁边有一轮弯月，手上握着一个卷轴，胸前挂着十字架，象征阴阳平衡、与神合一。 她头戴的帽子是由上弦月、下弦月和一轮满月所构成的，象征所有的处女神祇。手上拿着卷轴，象征深奥的智慧，上面很明显的有TORA这四个字母，另外还有一个H的字母被遮住了。Torah包含了犹太人的律法，以摩西之言五卷的形式呈现出来。Torah中有着很多的智慧及知识，但有部分被遮掩了，这暗示智慧和知识隐藏在原文中。\n\n相较于上一张魔术师纯粹阳性的力量，女祭司表现的则是纯粹阴性的力量。她身穿代表纯洁的白色内袍，与圣母的蓝色外袍，静默端坐。脚畔的月亮代表她的想象力，以及她超越眼前的东西看向远处的能力。',
        words='智慧',
        desc='',
        positive='纯真无邪的、拥有直觉判断能力的、揭发真相的、运用潜意识的力量、掌握知识的、正确的判断、理性的思考、单恋的、精神上的恋爱、对爱情严苛的、回避爱情的、对学业有助益的。',
        negative='冷酷无情的、无法正确思考的、错误的方向、迷信的、无理取闹的、情绪不安的、缺乏前瞻性的、严厉拒绝爱情的。'
    ), init=False)

    the_empress: TarotCard = field(default=TarotCard(
        id=3, index='the_empress', type='major_arcana', orig_name='The Empress (III)', name='女皇',
        intro='在明亮的天空下，这名王权在握体态丰腴的女皇坐在富丽堂皇的由几个自然方式敷设的坐垫上，后座椅上叠着多层的软垫，坐起来舒适柔软，代表她喜欢享受，过着舒适的生活。皇后所靠的软垫是红色的，下面还垫了一块红色椅枕，以及红色的布，这些布料的颜色都是代表热情的象征。这些安排也代表女皇轻松度日的人生，而不是繁忙庸碌的日子。覆盖在椅背上的一块褐色的布上，有连续的金星符号花纹。女皇的四周充满了生命力。她身穿的宽松袍子上面画满象征多产的石榴，手持象征地球的圆形手杖，戴着由九颗珍珠组成的项链，象征九颗行星，也代表金星维纳斯。\n\n她前方的麦田已经成熟，代表丰饶与多产；后方则是茂密的丝柏森林，与象征生命力的瀑布河流。附近的溪流平稳的流动着，流水为草地和树木带来生机，而那些饱满的麦穗也暗示着生产力。那些在女祭司牌中尚未成熟的种子，到了女皇牌里则已成熟了，这意味着计划已成熟。',
        words='丰收',
        desc='',
        positive='温柔顺从的、高贵美丽的、享受生活的、丰收的、生产的、温柔多情的、维护爱情的、充满女性魅力的、具有母爱的、有创造力的女性、沈浸爱情的、财运充裕的、快乐愉悦的。',
        negative='骄傲放纵的、过度享乐的、浪费的、充满嫉妒心的、母性的独裁、占有欲、败家的女人、挥霍无度的、骄纵的、纵欲的、为爱颓废的、不正当的爱情、不伦之恋、美丽的诱惑。'
    ), init=False)

    the_emperor: TarotCard = field(default=TarotCard(
        id=4, index='the_emperor', type='major_arcana', orig_name='The Emperor (IV)', name='皇帝',
        intro='一国之尊的皇帝头戴皇冠，身着红袍，自信满满的坐在石质王位上。脚穿象征严格纪律的盔甲，说明他总是处于备战状态。左手拿着一颗宝球，右手则拿着象征王室的权杖，这权杖被塑造成古埃及十字架的形状，这是古埃及在肉身死亡后灵魂的象征。它代表统合了男性与女性的能量，是最有权力的埃及象徽之一。\n\n王位上有四个白羊头作为装饰，出现在他的座位上方和手下面，皇帝牌正是代表白羊座的牌。白羊座是十二星座的头一个，具有勇敢、积极、有野心、有自信的特质。红袍加上橙色的背景，呈现红色的主色调，与白羊座（Aries）的特性不谋而合，白羊座的课题之一就是学习自律。在你能够有效的领导他人，以及赢得他们的尊敬之前，你需要能够自我训练，这包括训练脾气、精力、情感以及思想。\n\n背景严峻的山象征前方险峻的路途。我们可以比较皇帝与皇后的背景，一个是严峻山川，一个是丰饶大地，形成互补的局面。',
        words='支配',
        desc='',
        positive='事业成功、物质丰厚、掌控爱情运的、有手段的、有方法的、阳刚的、独立自主的、有男性魅力的、大男人主义的、有处理事情的能力、有点独断的、想要实现野心与梦想的。',
        negative='失败的、过于刚硬的、不利爱情运的、自以为是的、权威过度的、力量减弱的、丧失理智的、错误的判断、没有能力的、过于在乎世俗的、权力欲望过重的、权力使人腐败的、徒劳无功的。'
    ), init=False)

    the_hierophant: TarotCard = field(default=TarotCard(
        id=5, index='the_hierophant', type='major_arcana', orig_name='The Hierophant (V)', name='教皇',
        intro='教皇身穿大红袍子，端坐在信众前。他头戴象征权力的三层皇冠，分别代表身心灵三种层次的世界。他的右手食中指指向天，象征祝福并传导来自天空的能量﹔左手持着一根有三重十字架的宝杖，象征神圣与权力。他耳朵旁边垂挂的白色小物，代表内心的声音。\n\n教皇这张牌有很多的十字架出现，在白上衣外面罩了一件红色长袍，袍带上面有三个十字图案，连鞋子上面也有十字图形。地板上可以看见有四个以上的十字架被圆圈圈所包住，他手上及袍带上的三重十字也指圣父、圣子及圣灵，有些人则视之为灵魂、心智及肉体。',
        words='援助',
        desc='',
        positive='有智慧的、擅沟通的、适时的帮助、找到真理、有精神上的援助、得到贵人帮助、一个有影响力的导师、找到正确的方向、学业出现援助、爱情上出现长辈的干涉、媒人的帮助。',
        negative='过于依赖的、错误的指导、盲目的安慰、无效的帮助、独裁的、疲劳轰炸的、精神洗脑的、以不正当手段取得认同的、毫无能力的、爱情遭破坏、第三者的介入。'
    ), init=False)

    the_lovers: TarotCard = field(default=TarotCard(
        id=6, index='the_lovers', type='major_arcana', orig_name='The Lovers (VI)', name='恋人',
        intro='恋人牌背景在伊甸园，阳光普照，亚当与夏娃分站两边，两者皆裸身站立在彼此前面，代表他们没什么需要隐藏的。两人所踩的土地相当肥沃，生机盎然，在他们上方出现了一位天使。为了找寻满足，男人望向女人。女子则为了精神上的滋养而仰望天使（精神或内心）。天使代表在一个较高的层次上，他们曾经是而且也仍然是什么，但那必须两人共同仰望才看得见。如果你想更接近天使，或真实的自我，则应将理性（男性）及热情（女性）加以调和。\n\n夏娃的背后是知识之树，生有五颗苹果，象征五种感官，有条蛇缠绕树上。蛇在世界文化中的象征丰富多元，此处可能象征智慧，也象征欲望与诱惑。它由下往上缠绕在树上，暗示诱惑经常来自潜意识。亚当背后是生命之树，树上有十二团火焰，象征十二星座，也象征欲望之火。伟特说：「亚当与夏娃年轻诱人的躯体，象征未受有形物质污染之前的青春、童贞、纯真和爱」。',
        words='结合',
        desc='',
        positive='爱情甜蜜的、被祝福的关系、刚萌芽的爱情、顺利交往的、美满的结合、面临工作学业的选择、面对爱情的抉择、下决定的时刻、合作顺利的。',
        negative='遭遇分离、有第三者介入、感情不合、外力干涉、面临分手状况、爱情已远去、无法结合的、遭受破坏的关系、爱错了人、不被祝福的恋情、因一时的寂寞而结合。'
    ), init=False)

    the_chariot: TarotCard = field(default=TarotCard(
        id=7, index='the_chariot', type='major_arcana', orig_name='The Chariot (VII)', name='战车',
        intro='一位英勇的战士驾着一座由两只人面狮身兽拉着的战车，由他英武的姿态可知战斗力强烈。战士头戴象征统治的八芒星头冠和象征胜利的桂冠，身着战斗盔甲，手持象征意志与力量的矛形权杖，全身的盔甲好几层，每个部位都有防护之物：护肩、护肘和护胸甲。盔甲上的肩章呈现弦月形，显示战车牌与属月亮的巨蟹座之关联，并呈现出人脸的形貌，两边的脸表情并不一样，右肩是哭脸，左肩是笑脸。这组阴阳脸图形，是代表心中的两股不同的情绪，这是战士必须控制及调和的，不能因而左右为难。',
        words='胜利',
        desc='',
        positive='胜利的、凯旋而归的、不断的征服、有收获的、快速的解决、交通顺利的、充满信心的、不顾危险的、方向确定的、坚持向前的、冲劲十足的。',
        negative='不易驾驭的、严重失败、交通意外、遭遇挫折的、遇到障碍的、挣扎的、意外冲击的、失去方向的、丧失理智的、鲁莽冲撞的。'
    ), init=False)

    strength: TarotCard = field(default=TarotCard(
        id=8, index='strength', type='major_arcana', orig_name='Strength (VIII)', name='力量',
        intro='这位被称做「力量Strength」的女子，双手控制着狮子的嘴巴，面对强悍的猛兽，一点都没有畏惧，右手食指还弯曲着，显露出细致的一面，脸上呈现祥和的神情。这些动作表示她以一种「善意的坚毅」beneficent fortitude，驯服了狮子。女子的头顶之上有一个无限倒8大符号，这点则与「1号魔法师」相同，这一符号代表内在力量的无穷尽，说明循环与生生不息的力量正在运作。\n\n整体配色也是红色与白色的对比组合，纯净和热烈的调和。而女人以不动如山的姿态按捺着狮子，远景中还有一座高耸的山，山前有几株绿树。这座蓝色的山丘，与恋人牌上的山峰很相像，有热情澎湃的意味，然而更代表蕴藏着热烈的潜藏能量和爆发力，而此时正是蓄势待发却又按兵不动的时刻。',
        words='意志',
        desc='',
        positive='内在的力量使成功的、正确的信心、坦然的态度、以柔克刚的力量、有魅力的、精神力旺盛、有领导能力的、理性的处理态度、头脑清晰的。',
        negative='丧失信心的、失去生命力的、沮丧的、失败的、失去魅力的、无助的、情绪化的、任性而为的、退缩的、没有能力处理问题的、充满负面情绪的。'
    ), init=False)

    the_hermit: TarotCard = field(default=TarotCard(
        id=9, index='the_hermit', type='major_arcana', orig_name='The Hermit (IX)', name='隐者',
        intro='隐士牌中没有明亮的色彩，这反而能让他看见生命中幽微的事物。身穿灰色斗篷和帽子的老人站在冰天雪地的山巅上，低头沉思，四周杳无人烟。他右手高高举着一盏灯，这是真理之灯，灯里是颗发亮的六角星，这星星包含了朝上及朝下的三角形，意味结合火和水元素的需要，名称是所罗门的封印，散发出潜意识之光。老人左手拄着一根族长之杖，这跟杖在愚人、魔术师、战车都曾经出现过，隐士杖交左手，用以在启蒙之路上做前导。\n\n整个画面的色调灰暗，朦胧中显现的隐士站在冰封高原俯瞰全世界，提着灯笼包含着许多的真理，是特殊的光芒。他能够吸引有识之士，引导世界的改变、人心的改变。整体构图偏于一个方向，隐士背面的部位是空白的背景，所朝的前方，暗示着所向往的方向。',
        words='寻求',
        desc='',
        positive='有骨气的、清高的、有智慧的、有法力的、自我修养的，生命的智慧情境、用智慧排除困难的、给予正确的指导方向、有鉴赏力的、三思而后行的、谨慎行动的。',
        negative='假清高的、假道德的、没骨气、没有能力的、内心孤独寂寞的、缺乏支持的、错误的判断、被排挤的、没有足够智慧的、退缩的、自以为是的、与环境不合的。'
    ), init=False)

    wheel_of_fortune: TarotCard = field(default=TarotCard(
        id=10, index='wheel_of_fortune', type='major_arcana', orig_name='Wheel of Fortune (X)', name='命运之轮',
        intro='所有的大牌都有人物，命运之轮是唯一的例外，可见这张牌独树一格。深蓝色的天空悬着一个轮子，轮盘由三个圆圈构成（教宗的头冠也是），最里面的小圈代表创造力，中间是形成力，最外层是物质世界。\n\n小圈里头没有任何符号，因为创造力潜能无限；中间圆圈里有四个符号，从上方顺时针依序是链金术中的汞、硫、水、盐，分别与风火水土四要素相关联，是形成物质世界的基本要素，也分别代表超意识、自我意识觉醒、潜意识和分解，意味人类必须将身边的物质分解吸收并萃取精华，再运用创造力，造出新事物﹔最外层就是物质世界，上右下左四方位分别是TARO四个字母。\n\n轮盘从中心放射出八道直线，代表宇宙辐射能量。 在轮盘左方有一条往下行进的蛇，是埃及神话中的邪恶之神Typhon，它的向下沉沦带着轮子进入分崩离析的黑暗世界。相反的，背负轮盘的胡狼头动物渴求上升，它是埃及神话中的阿努比神(Anubis)。而上方的人面狮身兽是智慧的象征，均衡持中，在变动中保持不变。它拿着的宝剑代表风要素，表示心智能力、思考力和智慧。\n\n四个角落的四只动物，从右上方顺时针看分别是老鹰、狮子、牛、人，而且他们都有翅膀。这就是「四活物」Four Living Creatures，这四个动物出自圣经启示录第四章「宝座周围有四个活物（），前后遍体都满了眼睛。第一个活物像狮子，第二个像牛犊，第三个脸面像人，第四个像飞鹰」，耶路撒冷圣经提到四活物象征四位福音书的作者（马太、马可、路加和约翰）。在占卜上这四个动物与占星学产生关联，分别代表四个固定星座和四要素，老鹰是天蝎座（水），狮子是狮子座（火），牛是金牛座（土），人是水瓶座（风）。它们都在看书，汲取智慧，从各自的观点在学习有关人生的事情，而翅膀赋予它们在变动中保持稳定的能力。',
        words='轮回',
        desc='',
        positive='忽然而来的幸运、即将转变的局势、顺应局势带来成功、把握命运给予的机会、意外的发展、不可预测的未来、突如其来的爱情运变动。',
        negative='突如其来的厄运、无法抵抗局势的变化、事情的发展失去了掌控、错失良机、无法掌握命运的关键时刻而导致失败、不利的突发状况、没有答案、被人摆布、有人暗中操作。'
    ), init=False)

    justice: TarotCard = field(default=TarotCard(
        id=11, index='justice', type='major_arcana', orig_name='Justice (XI)', name='正义',
        intro='一个女人端坐在石凳上，背后两根石柱，右手持剑高高举起，左手在下拿着天秤，暗示她能够识破现实的假象，而理解时间的真正原因或共同的正义，正义牌的挑战即是做出公平而正当的决定。身穿红袍，头戴金冠，绿色披肩用一个方形扣子扣起。她的右脚微微往外踏出，似乎想站起来，而左脚仍隐藏在袍子里面。她高举宝剑，象征她的决心。\n\n宝剑不偏不倚，象征公正，且智慧可以戳破任何虚伪与幻象。宝剑两面都有刃，可行善可行恶，端看个人选择，也代表对生命的二元性的理解，以及你应该为目前的境遇负起应付的责任。左手的金色天秤和披肩的绿色都是天秤座的象征。手持天秤表示她正在评估，正要下某个决定，同时追求平衡。胸前的方形扣子中间是个圆形，象征四要素的调和。',
        words='均衡',
        desc='',
        positive='明智的决定、看清了真相、正确的判断与选择、得到公平的待遇、走向正确的道路、理智与正义战胜一切、维持平衡的、诉讼得到正义与公平、重新调整使之平衡、不留情面的。',
        negative='错误的决定、不公平的待遇、没有原则的、缺乏理想的、失去方向的、不合理的、存有偏见的、冥顽不灵的、小心眼、过于冷漠的、不懂感情的。'
    ), init=False)

    the_hanged_man: TarotCard = field(default=TarotCard(
        id=12, index='the_hanged_man', type='major_arcana', orig_name='The Hanged Man (XII)', name='倒吊人',
        intro='倒吊人图案简单，涵义却深远。我们看到一个男人在一棵Ｔ字形树上倒吊着，他平静的观察四周，散发出一种内在的平和与冷静，颇沉着、顺从而坚忍。两手背在背后，形成一个三角形。两腿交叉形成十字。十字和三角形结合在一起，就是一个炼金符号，象征伟大志业的完成，也象征低层次的欲望转化到高层次的灵魂（炼成黄金）。\n\n既然是倒着身子，那么身上的东西也都会掉落、抖落一地，没有办法留住什么东西。这代表世俗面的、物质性的东西无保留住，也代表失去，遗落和舍弃、割舍。甚至是一种主动的放弃或是遗弃，而倒吊并不是目的，只是为了帮助自己断舍离的一种方式，懂得舍得的道理。这时候的你，也不免在情感面和情绪面上，冷漠和单调，才能去忽略或不在意这些。',
        words='牺牲',
        desc='',
        positive='心甘情愿的牺牲奉献、以修练的方式来求道、不按常理的、反其道而行的、金钱上的损失、正专注于某个理想的、有坚定信仰的、长时间沈思的、需要沈淀的、成功之前的必经之道。',
        negative='精神上的虐待、心不甘情不愿的牺牲、损失惨重的、受到亏待的、严重漏财的、不满足的、冷淡的、自私自利的、要求回报的付出、逃离綑绑和束缚、以错误的方式看世界。'
    ), init=False)

    death: TarotCard = field(default=TarotCard(
        id=13, index='death', type='major_arcana', orig_name='Death (XIII)', name='死神',
        intro='传统的死神牌，通常是由骷髅人拿着镰刀来代表，而伟特将死神的意象提升到更深一层的境界。伟特牌的死神画面，模拟「启示录」场景的画面来表达死神的意涵，这里的骷髅骑在巨大的白马上，并且身着黑色的盔甲，只露出头脸部位。铁帽下可以清楚看见骷髅头，空洞的眼神似乎正朝你望着。全身裹着黑色的盔甲，连脚也穿着铁靴，重装备的骑士肯定是所向披靡。这犹如「启示录」中描述的死亡骑士，将带来如瘟疫般的无形利器。\n\n这张牌最显著的颜色是白色（纯洁的动机）和黄色（澄清的思想），这两种特质会让我们在进行变革的过程中更为温和。背景处的河流是在提醒我们，我们终将会走完这一生，一如所有的人和所有的机遇走过我们的生命。',
        words='结束',
        desc='',
        positive='必须结束旧有的现状、面临重新开始的时刻到了、将不好的过去清除掉、专注于心的开始、挥别过去的历史、展开心的旅程、在心里做个了结、激烈的变化。',
        negative='已经历经了重生阶段了、革命已经完成、挥别了过去、失去了、结束了、失败了、病了、走出阴霾的时刻到了、没有转圜余地了。'
    ), init=False)

    temperance: TarotCard = field(default=TarotCard(
        id=14, index='temperance', type='major_arcana', orig_name='Temperance (XIV)', name='节制',
        intro='大天使麦可手持两个金杯，把左手杯中的水倒入右手杯中，或把水在两个杯子之间倒来倒去，滴水不漏、泰然自若，神情专注而投入，头部散发着光芒，这个头部四周的光芒是在提醒，要记取对生命更宏观的看法。\n\n金发的天使身着白袍，透着温合的柔光，背长火红翅膀，表示热烈的性情和积极的行动，这对翅膀也显示出肉体和灵体的混合，要知道肉身和灵体有着不同的需求，而恰如其分的迎合这些不同的需求，会使得人生更加均衡。他心脏的气轮或能量中心，有一个白色的四方形，中间一个橘色的三角形。融合自己的精神和动物层面，是节制牌所意味的。四方形（土）中的橘色三角形（火），代表精神自有形的身体中升起。表示调和物质与精神，调和二种层面的世界。这符号位于心轮部位，代表心胸的开阔和容纳性，容纳这个符号的象征对象。',
        words='净化',
        desc='它表明被赋予了清晰的视野，你可以避免极端，并试着保持温和的生活。您可能还会遇到旧的和新的想法之间的冲突，因此对于该怎么做感到困惑。该卡建议您耐心评估当前情况，然后根据您面临的任何新情况进行调整。',
        positive='良好的疏导、希望与承诺、得到调和、有节制的、平衡的、沟通良好的、健康的、成熟与均衡的个性、以机智处理问题、从过去的错误中学习、避免重蹈覆辙、净化的、有技巧的、有艺术才能的。',
        negative='缺乏能力的、技术不佳的、不懂事的、需反省的、失去平衡状态、沟通不良的、缺乏自我控制力、不确定的、重复犯错的、挫败的、受阻碍的、暂时的分离、希望与承诺遥遥无期。'
    ), init=False)

    the_devil: TarotCard = field(default=TarotCard(
        id=15, index='the_devil', type='major_arcana', orig_name='The Devil (XV)', name='恶魔',
        intro='在恶魔牌上，我们看到和恋人相似的构图，只是恋人牌的天使在这里换成了恶魔，而亚当夏娃已然沉沦，上天的祝福变成了诅咒。\n\n魔鬼蹲坐着，脚爪紧抓住一座长形的黑色立方石，这就是魔鬼的祭坛。前方的亚当夏娃同样长出角和尾巴，显露出野兽本能，清楚的显示是受到引诱吃了禁果之后的堕落阶段。魔鬼的左手拿着火炬，是欲望之火。火炬下垂，这把火几乎接触到亚当的尾巴，使得他烧到而着了火，亚当的尾巴尖端是朵火焰，夏娃则是葡萄，都是恋人牌树上结的果实，表示她们误用了天赋。两个人被铁链锁住，乍看无处可逃，但仔细一看，其实系在她们脖子上的链子非常的松，只要愿意，随时可以挣脱，但她们却没有，表示这个枷锁是他们自己套在自己身上的。恶魔牌背景全黑，光芒不存，代表精神上的黑暗。\n\n从整体画面看来，生命力和活力仍然是旺盛的，甚至于热情更为炽热。只是精神趋向于黑暗面，能量专注于狭隘之处，或演出世人不认同之剧情。',
        words='诅咒',
        desc='',
        positive='不伦之恋、不正当的欲望、受诱惑的、违反世俗约定的、不道德的、有特殊的艺术才能、沉浸在消极里、沉溺在恐惧之中的、充满愤怒和怨恨、因恐惧而阻碍了自己、错误的方向、不忠诚的、秘密恋情。',
        negative='解脱了不伦之恋、挣脱了世俗的枷锁、不顾道德的、逃避的、伤害自己的、欲望的化解、被诅咒的、欲望强大的、不利的环境、盲目做判断、被唾弃的。'
    ), init=False)

    the_tower: TarotCard = field(default=TarotCard(
        id=16, index='the_tower', type='major_arcana', orig_name='The Tower (XVI)', name='塔',
        intro='一座位于山巅上耸立的高塔，山巅之塔深入云端，象征人类自我满足的心态、物质胜利的骄傲。整座塔是由石或砖所建造，外型呈灰暗的颜色，代表僵化和坚持。以皇冠来代替塔顶，表示这座建筑物是智慧的顶级，荣耀的冠冕，精神的指标。闪电直接击中皇冠，使它翻起掉落，是一种智识的失败，以及信仰的危机，也暗示闪电有目标选择性。皇冠象征精神面，被石砖等物质撑得高高在上的皇冠，如今仍不免栽落。整座塔楼崩毁瓦解，除了塔的顶端着了大火冒出烟雾，塔身的窗户也冒出了好几道火苗，而且到处烟雾弥漫。\n\n高塔被雷击中而毁坏燃烧起来，塔中两人头上脚下的坠落。塔顶的王冠受雷击而即将坠落。塔象征物质，王冠象征统治和成就，也代表物质与财富，受雷一击，便荡然无存。\n\n整个场景充满混乱，图案的构思如此，意义内涵也是如此。蓝黑色的背景，代表黑暗、空虚，沉重和压迫。暗蓝色部分是一种忧郁和理智的混乱。这张牌是一种失败，也是一种走火入魔。',
        words='毁灭',
        desc='',
        positive='双方关系破裂、难以挽救的局面、组织瓦解了、损失惨重的、惨烈的破坏、毁灭性的事件、混乱的影响力、意外的发展、震惊扰人的问题、悲伤的、离别的、失望的、需要协助的、生活需要重建的。',
        negative='全盘覆没、一切都已破坏殆尽、毫无转圜余地的、失去了、不安的、暴力的、已经遭逢厄运了、急需重建的。'
    ), init=False)

    the_star: TarotCard = field(default=TarotCard(
        id=17, index='the_star', type='major_arcana', orig_name='The Star (XVII)', name='星星',
        intro='这张牌是塔罗牌当中，祥和宁静、温馨美丽的一张牌。画面的营造点出星空的美丽、景致的美丽以及星星女神的美丽。有一汪清澈的池塘或湖泊，这个水源引人无限遐思，透露着这里是一片绿洲。绿洲代表着美好的愿景，一切的希望，让你如愿以偿。光明的前景，充满信心和乐观，感到满足和愉悦。对人生充满憧憬。这是属于你的应许之地，愿望之泉，喜乐之源。绿洲内一定有湖泊，带给你实质的滋养滋润，湖边绵密的绿茵，让你安然憩息，体会温馨的感受。',
        words='希望',
        desc='它表明你正在经历一个充满活力，精神稳定，冷静和对自己更深刻理解的积极阶段。您过去所经历的艰难挑战正在帮助您进行彻底的转型并拥抱新的机遇。根据卡片的建议，您需要对自己的个性进行重大改变，并从新的角度看待生活。',
        positive='未来充满希望的、新的诞生、无限的希望、情感面精神面的希望、达成目标的、健康纯洁的、美好的未来、好运即将到来、美丽的身心、光明的时机、平静的生活、和平的处境。',
        negative='希望遥遥无期的、失去信心的、没有寄托的未来、失去目标的、感伤的、放弃希望的、好运远离的、毫无进展的、过于虚幻、假想的爱情运、偏执于理想、希望破灭的。'
    ), init=False)

    the_moon: TarotCard = field(default=TarotCard(
        id=18, index='the_moon', type='major_arcana', orig_name='The Moon (XVIII)', name='月亮',
        intro='月亮这张牌，表达的是黯淡的夜晚，那股阴森恐怖的气氛，相较于其他的牌，月亮整体呈现的图面经常令人感到诡异。一轮月亮高挂空中，总共有三个层次，最右边的是新月，最左边的是满月，而中间的女人脸孔则是伟特所谓的「慈悲面」，从新月渐渐延伸向满月，越来越大。月亮的外围则有十六道大光芒，和十六道小光芒，其下有十五滴象征思想之露珠。 把新月满月结合在一起，是刻意表达月亮本身的阴晴圆缺的变化。人形的脸，显露出闭眼抿嘴向下望，是一种凝重的表情，我们也可领受到祂的慈悲，因为这个面容就是月亮慈悲的一面。',
        words='不安',
        desc='',
        positive='负面的情绪、不安和恐惧、充满恐惧感、阴森恐怖的感觉、黑暗的环境、景气低落、白日梦、忽略现实的、未知的危险、无法预料的威胁、胡思乱想的、不脚踏实地的、沉溺的、固执的。',
        negative='度过低潮阶段、心情平复、黑暗即将过去、曙光乍现、景气复甦、挥别恐惧、从忧伤中甦醒、恢复理智的、看清现实的、摆脱欲望的、脚踏实地的、走出谎言欺骗。'
    ), init=False)

    the_sun: TarotCard = field(default=TarotCard(
        id=19, index='the_sun', type='major_arcana', orig_name='The Sun (XIX)', name='太阳',
        intro='黄金色的阳光，在蓝色的天空下，几乎布满了画面，太阳光芒已经都延伸到地面，有滋养生命的寓意。可爱的裸体孩童骑在马背上，跨越灰色的围墙，脸上带着微笑。小孩左手握着旗杆，高揭着红色旗帜来加强太阳的特性，旗面是长条状的红布，向下波浪状延伸展开，并卷过细长的旗杆。红色本身代表热情和旺盛的生命力，而红色的旗帜也代表欢乐的庆典。太阳本已经有生命力和热力，红旗是特别要强调，存在于人类之间炽烈的情感和爱。',
        words='生命',
        desc='',
        positive='前景看好的、运势如日中天的、成功的未来、光明正大的恋情、热恋的、美满的婚姻、丰收的、事件进行顺畅的、物质上的快乐、有成就的、满足的生活、旺盛。',
        negative='热情消退的、逐渐黯淡的、遭遇失败的、分离的、傲慢的、失去目标的、没有远景的、失去活力的、没有未来的、物质的贫乏、不快乐的人生阶段。'
    ), init=False)

    judgement: TarotCard = field(default=TarotCard(
        id=20, index='judgement', type='major_arcana', orig_name='Judgement (XX)', name='审判',
        intro='这张牌取材自圣经中末世审判的故事，也是西方传统而根深蒂固的宗教观念，几乎所有塔罗中的这张牌主旨和图案都很一致。天使吹号角是圣经中描述的情节，宣示末日到来，神的审判已经降临。人们重新复活，就是「启示录」Revelation中的画面。\n\n在最后的审判中，大天使加百列(Gabriel)在空中居高临下吹号角，人们受到感召而得救复活，从他们的墓穴中站起来欢庆。一面白底有红十字图形的旗子在飘扬着。每个男人、女人和小孩都向上仰望着精神，因为这是他们返回上帝或造物主家园的道路。',
        words='复活',
        desc='',
        positive='死而复生、调整心态重新来过、内心的觉醒、观念的翻新、超脱了束缚的、满意的结果、苦难的结束、重新检视过去而得到新的启发、一个新的开始、一段新的关系。',
        negative='不公平的审判、无法度过考验的、旧事重演的、固执不改变的、自以为是的、对生命的看法狭隘的、后悔莫及的、自责的、不满意的结果、被击垮的。'
    ), init=False)

    the_world: TarotCard = field(default=TarotCard(
        id=21, index='the_world', type='major_arcana', orig_name='The World (XXI)', name='世界',
        intro='巨大的椭圆型桂冠花环，环绕着最中央的裸身女子，这位赤裸的舞者自由地在空中跳舞，呼应着四周云端中的神兽。她是一个完美的整合，它是一个理想，人类最终的盼望，一种完美形态，是人类所向往形貌的原型呈现。她外貌看起来虽是女的，但在许多版本的塔罗牌中，她是雌雄同体，象征愚人终于成功将阴阳两股力量融合。\n\n世界牌的画面设计，有许多要件都是为了与前面的每一张牌做出呼应、连结和统整。因为身为最后一张大阿尔卡纳，内容主旨有许多与「最终」相关，这一点是无法忽略的，必须表现尽善尽美以及宇宙体系的终点。',
        words='达成',
        desc='',
        positive='完美的结局、重新开始的、生活上的完美境界、获得成功的、心理上的自由、完成成功的旅程、心灵的融合、自信十足带来成功、生活将有重大改变、获得完满的结果。',
        negative='无法完美的、一段过往的结束、缺乏自尊的、感觉难受的、态度悲观的、丑恶的感情、无法挽回的局势、不完美的结局、无法再继续的、残缺的。'
    ), init=False)

    ace_of_wands: TarotCard = field(default=TarotCard(
        id=22, index='ace_of_wands', type='minor_arcana', orig_name='Ace of Wands', name='权杖首牌',
        intro='',
        words='',
        desc='', positive='', negative=''
    ), init=False)

    two_of_wands: TarotCard = field(default=TarotCard(
        id=23, index='two_of_wands', type='minor_arcana', orig_name='Two of Wands', name='权杖二',
        intro='',
        words='',
        desc='', positive='', negative=''
    ), init=False)

    three_of_wands: TarotCard = field(default=TarotCard(
        id=24, index='three_of_wands', type='minor_arcana', orig_name='Three of Wands', name='权杖三',
        intro='',
        words='',
        desc='', positive='', negative=''
    ), init=False)

    four_of_wands: TarotCard = field(default=TarotCard(
        id=25, index='four_of_wands', type='minor_arcana', orig_name='Four of Wands', name='权杖四',
        intro='',
        words='',
        desc='', positive='', negative=''
    ), init=False)

    five_of_wands: TarotCard = field(default=TarotCard(
        id=26, index='five_of_wands', type='minor_arcana', orig_name='Five of Wands', name='权杖五',
        intro='',
        words='',
        desc='', positive='', negative=''
    ), init=False)

    six_of_wands: TarotCard = field(default=TarotCard(
        id=27, index='six_of_wands', type='minor_arcana', orig_name='Six of Wands', name='权杖六',
        intro='',
        words='',
        desc='', positive='', negative=''
    ), init=False)

    seven_of_wands: TarotCard = field(default=TarotCard(
        id=28, index='seven_of_wands', type='minor_arcana', orig_name='Seven of Wands', name='权杖七',
        intro='',
        words='',
        desc='', positive='', negative=''
    ), init=False)

    eight_of_wands: TarotCard = field(default=TarotCard(
        id=29, index='eight_of_wands', type='minor_arcana', orig_name='Eight of Wands', name='权杖八',
        intro='',
        words='',
        desc='', positive='', negative=''
    ), init=False)

    nine_of_wands: TarotCard = field(default=TarotCard(
        id=30, index='nine_of_wands', type='minor_arcana', orig_name='Nine of Wands', name='权杖九',
        intro='',
        words='',
        desc='', positive='', negative=''
    ), init=False)

    ten_of_wands: TarotCard = field(default=TarotCard(
        id=31, index='ten_of_wands', type='minor_arcana', orig_name='Ten of Wands', name='权杖十',
        intro='',
        words='',
        desc='', positive='', negative=''
    ), init=False)

    page_of_wands: TarotCard = field(default=TarotCard(
        id=32, index='page_of_wands', type='minor_arcana', orig_name='Page of Wands', name='权杖侍从',
        intro='',
        words='',
        desc='', positive='', negative=''
    ), init=False)

    knight_of_wands: TarotCard = field(default=TarotCard(
        id=33, index='knight_of_wands', type='minor_arcana', orig_name='Knight of Wands', name='权杖骑士',
        intro='',
        words='',
        desc='', positive='', negative=''
    ), init=False)

    queen_of_wands: TarotCard = field(default=TarotCard(
        id=34, index='queen_of_wands', type='minor_arcana', orig_name='Queen of Wands', name='权杖皇后',
        intro='',
        words='',
        desc='', positive='', negative=''
    ), init=False)

    king_of_wands: TarotCard = field(default=TarotCard(
        id=35, index='king_of_wands', type='minor_arcana', orig_name='King of Wands', name='权杖国王',
        intro='',
        words='',
        desc='', positive='', negative=''
    ), init=False)

    ace_of_cups: TarotCard = field(default=TarotCard(
        id=36, index='ace_of_cups', type='minor_arcana', orig_name='Ace of Cups', name='圣杯首牌',
        intro='圣杯一是所有小牌的一号牌中最富象征意义的。图中的圣杯就是耶稣在最后晚餐中使用的杯子，杯上有个倒立的Ｍ字母。据说，在耶稣死后，他的鲜血就是由这个圣杯所承装着。',
        words='',
        desc='', positive='', negative=''
    ), init=False)

    two_of_cups: TarotCard = field(default=TarotCard(
        id=37, index='two_of_cups', type='minor_arcana', orig_name='Two of Cups', name='圣杯二',
        intro='一男一女面对彼此，向对方持杯致意。两人把杯子举在同一个高度，意味着平等互信，在暗示一种平等的爱或生意关系，或任何密切的团队努力或有利的合作关系。两人头上都戴著花环，男人身躯微微向前，左脚踏出，右手也伸向女人，而女人站姿端凝如山。他们中间浮著一根两条蛇缠绕的杖，称为「赫密士之杖」，是治疗的象征。杖上的狮子头象征沟通，而两片翅膀象征圣灵，使人联想到恋人牌中的天使。',
        words='',
        desc='', positive='', negative=''
    ), init=False)

    three_of_cups: TarotCard = field(default=TarotCard(
        id=38, index='three_of_cups', type='minor_arcana', orig_name='Three of Cups', name='圣杯三',
        intro='三个女子紧靠彼此正以舞蹈欢庆丰收，围成圆圈，高举圣杯互相庆贺。她们头上都戴着象征丰收的花圈，穿着色彩艳丽的袍子，脸上幸福洋溢。四周有藤蔓、葫芦及南瓜，一位女子手上提着一串葡萄，这些植物很容易让人联想到丰收的时节。\n\n这三位女子分别有不同颜色的头发与眼珠，穿戴的衣服花环也都各有不同，代表她们都是独立的个体，有独立的个性，但是，在这个团体中，她们都能尊重彼此，敬爱彼此。三人围成圆圈的型态，表示她们之间没有尊卑之分，在这个欢庆的场合里，每个人都是如此平等。',
        words='',
        desc='', positive='', negative=''
    ), init=False)

    four_of_cups: TarotCard = field(default=TarotCard(
        id=39, index='four_of_cups', type='minor_arcana', orig_name='Four of Cups', name='圣杯四',
        intro='一个男人百无聊赖地在树荫下盘腿而坐，双眼紧闭，双手双脚合在一起，形成防御的姿态。他前方三个杯子象征他过去的经验。云中伸出一只手给他第四个杯子，他却视而不见，独自沉浸在自己的世界中。',
        words='',
        desc='', positive='', negative=''
    ), init=False)

    five_of_cups: TarotCard = field(default=TarotCard(
        id=40, index='five_of_cups', type='minor_arcana', orig_name='Five of Cups', name='圣杯五',
        intro='圣杯五是一张代表悲伤、失落与失望的牌。在灰暗的天空底下，有一个人身着黑色斗篷，意志消沉的低头哀悼地上三个倾倒的杯子，里头五颜六色的酒流了出来。他的前方是一条河，象征悲伤之流，代表情感的河流将这个人和位于远处代表安定的城堡分开了，但河上有座象征意识与决心的桥，通往远处的房子。\n\n这座横跨河流通往城堡的桥梁，却因为这个人更专注于他/她所失去的，而忽略了这条通往安定的道路。灰暗的天色反映牌中人的沮丧的内心世界。从图面上无法分辨出这人是男是女，显示悲伤的情绪无论男女皆能体验。',
        words='',
        desc='', positive='', negative=''
    ), init=False)

    six_of_cups: TarotCard = field(default=TarotCard(
        id=41, index='six_of_cups', type='minor_arcana', orig_name='Six of Cups', name='圣杯六',
        intro='在淡蓝的天空下，一座宁静安详的庄园里，有六个盛装五角星花朵的圣杯。一个小男孩捧着圣杯，似乎在嗅着花香，又好像把圣杯献给小女孩，圣杯当中所绽放的花朵照亮了围绕着他们的花园。他们看起来是安全的，而且他们被外在世界及领地巡守队保护着。背景充斥代表快乐的鲜黄色，而天气晴和，让人仿佛有置身童话世界的感受。',
        words='',
        desc='', positive='', negative=''
    ), init=False)

    seven_of_cups: TarotCard = field(default=TarotCard(
        id=42, index='seven_of_cups', type='minor_arcana', orig_name='Seven of Cups', name='圣杯七',
        intro='七个圣杯飘浮在云雾弥漫的半空中，杯中分别装着城堡（象征冒险或家庭）、珠宝（物质与财富）、桂冠（胜利）、恶龙（恐惧，另一说是诱惑或渴望）、人头（面具）、盖着布发光的人（自己）以及蛇（智慧，另一说是嫉妒或创造）。',
        words='',
        desc='', positive='', negative=''
    ), init=False)

    eight_of_cups: TarotCard = field(default=TarotCard(
        id=43, index='eight_of_cups', type='minor_arcana', orig_name='Eight of Cups', name='圣杯八',
        intro='身穿红衣红鞋的男子在暮色中，手持长杖，离开他先前辛苦建立的的八个杯子，越过河川，转身而去。四周沼泽密布，象征淤塞的情感，如同一滩死水。\n\n要搭起那八个杯子，起码需要一阵辛劳，他却发现八个圣杯中间的一个缺口，所以毅然转身离去前往寻找第九个圣杯，朝向更高处行走，而将这八个圣杯留在身后，这八个杯子代表快乐的机会，还可以容纳过去欢乐的事物。他的红色衣鞋以及长杖象征他的行动力，而现在他把这些精力从他过去构筑起的欢乐与成就，也就是那八个圣杯里移开，转而寻找失落的那一个圣杯，此时月亮遮盖了太阳，催促着更彻底的搜寻。',
        words='',
        desc='', positive='', negative=''
    ), init=False)

    nine_of_cups: TarotCard = field(default=TarotCard(
        id=44, index='nine_of_cups', type='minor_arcana', orig_name='Nine of Cups', name='圣杯九',
        intro='一个财主装扮的的男子坐在小凳上，双手抱胸，神情怡然自得。他身后的高桌上，覆盖蓝色桌布，九个圣杯排排站，放在比他还高的位置。背景则是一片光明的鲜黄色，代表思路清晰，而他帽子，羽毛和袜子鲜艳的深红色则显示出他对生命的热情。在这生命的热情之下的是蓝色的衣服，意味着他对于真实价值的精神层面的认知。',
        words='',
        desc='', positive='', negative=''
    ), init=False)

    ten_of_cups: TarotCard = field(default=TarotCard(
        id=45, index='ten_of_cups', type='minor_arcana', orig_name='Ten of Cups', name='圣杯十',
        intro='在图中我们看到一家四口和乐融融，父母亲搂抱对方，各举一只手迎向圣杯彩虹，又仿佛要拥抱周围，两个孩子快乐的手牵手跳舞，背景是清翠的树木河流和一栋房屋。\n\n一条河流温柔的流过房子，穿过已建立起来的花园，我们还可以看到十个圣杯就在他们头上形成一道彩虹。圣杯十可说是圣杯六当中爱的关系的成熟版。差异在于圣杯十地满足来自于内心世界以及彼此。现在孩子，大自然，他们的家以及生命本身，都在情感面和精神面滋养了周遭的每个人。',
        words='',
        desc='', positive='', negative=''
    ), init=False)

    page_of_cups: TarotCard = field(default=TarotCard(
        id=46, index='page_of_cups', type='minor_arcana', orig_name='Page of Cups', name='圣杯侍从',
        intro='圣杯侍从穿着花朵图案的衣服，用好奇的眼光，没有任何压力地看着杯中蹦出的一条鱼，鱼象征想像力，从杯中探出头来，代表圣杯侍从拥有过人的想象力。\n\n圣杯侍从身体很轻松地站着，左手叉腰，面带微笑，不难让人发现他个性友善。背景是波浪起伏的海面。',
        words='',
        desc='', positive='', negative=''
    ), init=False)

    knight_of_cups: TarotCard = field(default=TarotCard(
        id=47, index='knight_of_cups', type='minor_arcana', orig_name='Knight of Cups', name='圣杯骑士',
        intro='不同于令牌骑士或宝剑骑士的迅捷骑马姿态，圣杯骑士的白马很有绅士风度，优雅地行进，跟主人一样。圣杯骑士平举着圣杯，他的眼光有些梦幻，深深注视着圣杯。他的衣服上有红鱼图案，鱼象征想像力、创意和精神，红色则指出骑士的热忱。他的头盔和鞋子上都有翅膀图案，象征想像力。这一人一马就这样朝着河流前进。',
        words='',
        desc='', positive='', negative=''
    ), init=False)

    queen_of_cups: TarotCard = field(default=TarotCard(
        id=48, index='queen_of_cups', type='minor_arcana', orig_name='Queen of Cups', name='圣杯皇后',
        intro='圣杯皇后双手捧着圣杯，眼神直直的注视着圣杯。那圣杯是教堂形状，两臂各有一位天使，顶端是十字架，象征圣杯皇后的虔诚。她坐在海边的宝座上，宝座基部有个小美人鱼抓鱼的图案，顶部是两个小美人鱼共同抱着一个大蚌壳。相较于坐在海面与世隔绝的圣杯国王，有三只美人鱼陪伴的圣杯皇后，坐在陆地上，象征她更常与人接触。',
        words='',
        desc='', positive='', negative=''
    ), init=False)

    king_of_cups: TarotCard = field(default=TarotCard(
        id=49, index='king_of_cups', type='minor_arcana', orig_name='King of Cups', name='圣杯国王',
        intro='国王坐在波涛汹涌海中央的宝座上，左边有条鱼跳出海面，右边有一艘帆船。象征潜意识浮出。他的内袍是代表水要素的蓝色，胸前还挂著鱼形项链，象征想象力或创意。\n\n他左手拿著象征权力的杖，右手持圣杯，他却是圣杯家族中唯一不注视圣杯的人，暗示他不能完全沉浸在圣杯物质中。而且，他虽然身处海中央，却没有碰到水，也象征在某些程度上他必须跟他充满感情和创意的本性划清界线，以符合领导形象。',
        words='',
        desc='', positive='', negative=''
    ), init=False)

    ace_of_swords: TarotCard = field(default=TarotCard(
        id=50, index='ace_of_swords', type='minor_arcana', orig_name='Ace of Swords', name='宝剑首牌',
        intro='',
        words='',
        desc='', positive='', negative=''
    ), init=False)

    two_of_swords: TarotCard = field(default=TarotCard(
        id=51, index='two_of_swords', type='minor_arcana', orig_name='Two of Swords', name='宝剑二',
        intro='',
        words='',
        desc='', positive='', negative=''
    ), init=False)

    three_of_swords: TarotCard = field(default=TarotCard(
        id=52, index='three_of_swords', type='minor_arcana', orig_name='Three of Swords', name='宝剑三',
        intro='',
        words='',
        desc='', positive='', negative=''
    ), init=False)

    four_of_swords: TarotCard = field(default=TarotCard(
        id=53, index='four_of_swords', type='minor_arcana', orig_name='Four of Swords', name='宝剑四',
        intro='',
        words='',
        desc='', positive='', negative=''
    ), init=False)

    five_of_swords: TarotCard = field(default=TarotCard(
        id=54, index='five_of_swords', type='minor_arcana', orig_name='Five of Swords', name='宝剑五',
        intro='',
        words='',
        desc='', positive='', negative=''
    ), init=False)

    six_of_swords: TarotCard = field(default=TarotCard(
        id=55, index='six_of_swords', type='minor_arcana', orig_name='Six of Swords', name='宝剑六',
        intro='',
        words='',
        desc='', positive='', negative=''
    ), init=False)

    seven_of_swords: TarotCard = field(default=TarotCard(
        id=56, index='seven_of_swords', type='minor_arcana', orig_name='Seven of Swords', name='宝剑七',
        intro='',
        words='',
        desc='', positive='', negative=''
    ), init=False)

    eight_of_swords: TarotCard = field(default=TarotCard(
        id=57, index='eight_of_swords', type='minor_arcana', orig_name='Eight of Swords', name='宝剑八',
        intro='',
        words='',
        desc='', positive='', negative=''
    ), init=False)

    nine_of_swords: TarotCard = field(default=TarotCard(
        id=58, index='nine_of_swords', type='minor_arcana', orig_name='Nine of Swords', name='宝剑九',
        intro='',
        words='',
        desc='', positive='', negative=''
    ), init=False)

    ten_of_swords: TarotCard = field(default=TarotCard(
        id=59, index='ten_of_swords', type='minor_arcana', orig_name='Ten of Swords', name='宝剑十',
        intro='',
        words='',
        desc='', positive='', negative=''
    ), init=False)

    page_of_swords: TarotCard = field(default=TarotCard(
        id=60, index='page_of_swords', type='minor_arcana', orig_name='Page of Swords', name='宝剑侍从',
        intro='',
        words='',
        desc='', positive='', negative=''
    ), init=False)

    knight_of_swords: TarotCard = field(default=TarotCard(
        id=61, index='knight_of_swords', type='minor_arcana', orig_name='Knight of Swords', name='宝剑骑士',
        intro='',
        words='',
        desc='', positive='', negative=''
    ), init=False)

    queen_of_swords: TarotCard = field(default=TarotCard(
        id=62, index='queen_of_swords', type='minor_arcana', orig_name='Queen of Swords', name='宝剑皇后',
        intro='',
        words='',
        desc='', positive='', negative=''
    ), init=False)

    king_of_swords: TarotCard = field(default=TarotCard(
        id=63, index='king_of_swords', type='minor_arcana', orig_name='King of Swords', name='宝剑国王',
        intro='',
        words='',
        desc='', positive='', negative=''
    ), init=False)

    ace_of_pentacles: TarotCard = field(default=TarotCard(
        id=64, index='ace_of_pentacles', type='minor_arcana', orig_name='Ace of Pentacles', name='星币首牌',
        intro='',
        words='',
        desc='', positive='', negative=''
    ), init=False)

    two_of_pentacles: TarotCard = field(default=TarotCard(
        id=65, index='two_of_pentacles', type='minor_arcana', orig_name='Two of Pentacles', name='星币二',
        intro='',
        words='',
        desc='', positive='', negative=''
    ), init=False)

    three_of_pentacles: TarotCard = field(default=TarotCard(
        id=66, index='three_of_pentacles', type='minor_arcana', orig_name='Three of Pentacles', name='星币三',
        intro='',
        words='',
        desc='', positive='', negative=''
    ), init=False)

    four_of_pentacles: TarotCard = field(default=TarotCard(
        id=67, index='four_of_pentacles', type='minor_arcana', orig_name='Four of Pentacles', name='星币四',
        intro='',
        words='',
        desc='', positive='', negative=''
    ), init=False)

    five_of_pentacles: TarotCard = field(default=TarotCard(
        id=68, index='five_of_pentacles', type='minor_arcana', orig_name='Five of Pentacles', name='星币五',
        intro='',
        words='',
        desc='', positive='', negative=''
    ), init=False)

    six_of_pentacles: TarotCard = field(default=TarotCard(
        id=69, index='six_of_pentacles', type='minor_arcana', orig_name='Six of Pentacles', name='星币六',
        intro='',
        words='',
        desc='', positive='', negative=''
    ), init=False)

    seven_of_pentacles: TarotCard = field(default=TarotCard(
        id=70, index='seven_of_pentacles', type='minor_arcana', orig_name='Seven of Pentacles', name='星币七',
        intro='',
        words='',
        desc='', positive='', negative=''
    ), init=False)

    eight_of_pentacles: TarotCard = field(default=TarotCard(
        id=71, index='eight_of_pentacles', type='minor_arcana', orig_name='Eight of Pentacles', name='星币八',
        intro='',
        words='',
        desc='', positive='', negative=''
    ), init=False)

    nine_of_pentacles: TarotCard = field(default=TarotCard(
        id=72, index='nine_of_pentacles', type='minor_arcana', orig_name='Nine of Pentacles', name='星币九',
        intro='',
        words='',
        desc='', positive='', negative=''
    ), init=False)

    ten_of_pentacles: TarotCard = field(default=TarotCard(
        id=73, index='ten_of_pentacles', type='minor_arcana', orig_name='Ten of Pentacles', name='星币十',
        intro='',
        words='',
        desc='', positive='', negative=''
    ), init=False)

    page_of_pentacles: TarotCard = field(default=TarotCard(
        id=74, index='page_of_pentacles', type='minor_arcana', orig_name='Page of Pentacles', name='星币侍从',
        intro='',
        words='',
        desc='', positive='', negative=''
    ), init=False)

    knight_of_pentacles: TarotCard = field(default=TarotCard(
        id=75, index='knight_of_pentacles', type='minor_arcana', orig_name='Knight of Pentacles', name='星币骑士',
        intro='',
        words='',
        desc='', positive='', negative=''
    ), init=False)

    queen_of_pentacles: TarotCard = field(default=TarotCard(
        id=76, index='queen_of_pentacles', type='minor_arcana', orig_name='Queen of Pentacles', name='星币皇后',
        intro='',
        words='',
        desc='', positive='', negative=''
    ), init=False)

    king_of_pentacles: TarotCard = field(default=TarotCard(
        id=77, index='king_of_pentacles', type='minor_arcana', orig_name='King of Pentacles', name='星币国王',
        intro='',
        words='',
        desc='', positive='', negative=''
    ), init=False)


class TarotPacks(object):
    """
    定义套牌
    """
    SpecialCard: TarotPack = TarotPack(
        name='special',
        cards=[card for card in TarotCards.get_all_cards() if card.type == 'special'])

    MajorArcana: TarotPack = TarotPack(
        name='major_arcana',
        cards=[card for card in TarotCards.get_all_cards() if card.type == 'major_arcana'])

    MinorArcana: TarotPack = TarotPack(
        name='minor_arcana',
        cards=[card for card in TarotCards.get_all_cards() if card.type == 'minor_arcana'])

    RiderWaite: TarotPack = TarotPack(
        name='rider_waite',
        cards=[card for card in TarotCards.get_all_cards() if (
                card.type == 'major_arcana' or card.type == 'minor_arcana')])


__all__ = [
    'TarotCards',
    'TarotPacks'
]
