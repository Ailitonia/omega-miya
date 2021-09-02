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
        intro='',
        words='旅程',
        desc='它表明您希望寻求未来的机会，但缺乏明确的具体计划。由于你没有什么顾虑，有时这些特质反而会给你带来意想不到的成功。然而没有远见，使你容易产生动摇，当遇到太多障碍的时候往往会失去原有的目标。当你想要开始诸如学习，搬家或签署商业协议之类的，追随你的直觉并付出行动是不错的方式。',
        positive='盲目的、有勇气的、超越世俗的、展开新的阶段、有新的机会、追求自我的理想、展开一段旅行、超乎常人的勇气、漠视道德舆论的。',
        negative='过于盲目、不顾现实的、横冲直撞的、拒绝负担责任的、违背常理的、逃避的心态、一段危险的旅程、想法如孩童般天真幼稚的。'
    ), init=False)

    the_magician: TarotCard = field(default=TarotCard(
        id=1, index='the_magician', type='major_arcana', orig_name='The Magician (I)', name='魔术师',
        intro='',
        words='创造',
        desc='它意味着当你集中注意力并意识到你的需要，你就拥有了掌握宇宙力量的能力，以满足你的欲望，无论是情感，身体还是社交。但是，您需要充分利用自己的技能，并根据自己的看法让事情发生。渐渐地，创造性的方式会在你面前展开，从而帮助你快速获得成功。不久将来，一切都在你的掌握之中。',
        positive='成功的、有实力的、聪明能干的、擅长沟通的、机智过人的、唯我独尊的、企划能力强的、透过更好的沟通而获得智慧、运用智慧影响他人、学习能力强的、有教育和学术上的能力、表达技巧良好的。',
        negative='变魔术耍花招的、瞒骗的、失败的、狡猾的、善于谎言的、能力不足的、丧失信心的、以不正当手段获取认同的。'
    ), init=False)

    the_high_priestess: TarotCard = field(default=TarotCard(
        id=2, index='the_high_priestess', type='major_arcana', orig_name='The High Priestess (II)', name='女祭司',
        intro='',
        words='智慧',
        desc='此卡表明能够正确使用你的智慧，你通常会做出很好的判断。但是，可能会有一些领域需要更高的远见– 某些未知的变化可能是您最不期望的。因此，倾听你的内心声音，注意你的梦想，以获得精神启蒙，需要完美平衡你的生活。很快，随着你的精神力量的增加，你会看到你的创造性的一面展开。从长远来看，你也可以帮助别人坚持他们的希望，从而实现他们的梦想。',
        positive='纯真无邪的、拥有直觉判断能力的、揭发真相的、运用潜意识的力量、掌握知识的、正确的判断、理性的思考、单恋的、精神上的恋爱、对爱情严苛的、回避爱情的、对学业有助益的。',
        negative='冷酷无情的、无法正确思考的、错误的方向、迷信的、无理取闹的、情绪不安的、缺乏前瞻性的、严厉拒绝爱情的。'
    ), init=False)

    the_empress: TarotCard = field(default=TarotCard(
        id=3, index='the_empress', type='major_arcana', orig_name='The Empress (III)', name='女皇',
        intro='',
        words='丰收',
        desc='它表示你强大，充满活力和智慧的本性。你需要花更多的时间来理解自然，以便培养一种宽容的态度，让你能够理解别人的问题。反思他人对你的爱，并在执行职责时释出善意。最终，你将能够找到充实自己和其他人的生活方式。',
        positive='温柔顺从的、高贵美丽的、享受生活的、丰收的、生产的、温柔多情的、维护爱情的、充满女性魅力的、具有母爱的、有创造力的女性、沈浸爱情的、财运充裕的、快乐愉悦的。',
        negative='骄傲放纵的、过度享乐的、浪费的、充满嫉妒心的、母性的独裁、占有欲、败家的女人、挥霍无度的、骄纵的、纵欲的、为爱颓废的、不正当的爱情、不伦之恋、美丽的诱惑。'
    ), init=False)

    the_emperor: TarotCard = field(default=TarotCard(
        id=4, index='the_emperor', type='major_arcana', orig_name='The Emperor (IV)', name='皇帝',
        intro='',
        words='支配',
        desc='表示明智，稳定和保护，您随时准备为您身边的人提供指导。你也坚持你的计划，并倾向于以有组织的方式执行它们。事实上，你是一个天生的领导者，并且在获得正确的位置时，你会努力实现完美。你倾听别人的意见，但只做你认为正确的事，即使这意味着你必须面对反对。最后，你成功并获得你应得的认可。但是，过多遵守规则可能会使你看起来不灵活，从而剥夺了你对自发性和快乐的主张。所以，坚持规则也要保持平衡。',
        positive='事业成功、物质丰厚、掌控爱情运的、有手段的、有方法的、阳刚的、独立自主的、有男性魅力的、大男人主义的、有处理事情的能力、有点独断的、想要实现野心与梦想的。',
        negative='失败的、过于刚硬的、不利爱情运的、自以为是的、权威过度的、力量减弱的、丧失理智的、错误的判断、没有能力的、过于在乎世俗的、权力欲望过重的、权力使人腐败的、徒劳无功的。'
    ), init=False)

    the_hierophant: TarotCard = field(default=TarotCard(
        id=5, index='the_hierophant', type='major_arcana', orig_name='The Hierophant (V)', name='教皇',
        intro='',
        words='援助',
        desc='它反映了你希望坚持保守而不是创新。它也可能反映出你加入神圣团体或机构的倾向，以便符合他们有益的思维方式，从而进一步学习。该卡建议您从明智的导师那里寻求智慧和知识，以获得更高的意识。',
        positive='有智慧的、擅沟通的、适时的帮助、找到真理、有精神上的援助、得到贵人帮助、一个有影响力的导师、找到正确的方向、学业出现援助、爱情上出现长辈的干涉、媒人的帮助。',
        negative='过于依赖的、错误的指导、盲目的安慰、无效的帮助、独裁的、疲劳轰炸的、精神洗脑的、以不正当手段取得认同的、毫无能力的、爱情遭破坏、第三者的介入。'
    ), init=False)

    the_lovers: TarotCard = field(default=TarotCard(
        id=6, index='the_lovers', type='major_arcana', orig_name='The Lovers (VI)', name='恋人',
        intro='',
        words='结合',
        desc='它表明你在相互信任和吸引力的基础上分享强大而亲密的联系。该卡建议您在选择方向之前深入分析您的感受，动机以及可用选项。',
        positive='爱情甜蜜的、被祝福的关系、刚萌芽的爱情、顺利交往的、美满的结合、面临工作学业的选择、面对爱情的抉择、下决定的时刻、合作顺利的。',
        negative='遭遇分离、有第三者介入、感情不合、外力干涉、面临分手状况、爱情已远去、无法结合的、遭受破坏的关系、爱错了人、不被祝福的恋情、因一时的寂寞而结合。'
    ), init=False)

    the_chariot: TarotCard = field(default=TarotCard(
        id=7, index='the_chariot', type='major_arcana', orig_name='The Chariot (VII)', name='战车',
        intro='',
        words='胜利',
        desc='它表明通过适当地运用意志力，信心和纪律，你将能够克服所有的反对意见。卡片劝告你要大胆，但强调要控制你的冲动，这样你才能把它们引导到更有创意的事情上。',
        positive='胜利的、凯旋而归的、不断的征服、有收获的、快速的解决、交通顺利的、充满信心的、不顾危险的、方向确定的、坚持向前的、冲劲十足的。',
        negative='不易驾驭的、严重失败、交通意外、遭遇挫折的、遇到障碍的、挣扎的、意外冲击的、失去方向的、丧失理智的、鲁莽冲撞的。'
    ), init=False)

    strength: TarotCard = field(default=TarotCard(
        id=8, index='strength', type='major_arcana', orig_name='Strength (VIII)', name='力量',
        intro='',
        words='意志',
        desc='力量可能意味着你相信自己。你可以用温和的行为和成熟来控制一种不愉快的情况。您卓越的耐力和毅力可以帮助您忍受生活中的障碍并成为赢家。您可以忽略不完美之处，并为其他人提供改进空间。力量卡建议你实现自己的内在优势，放下目前笼罩着你的负面情绪。',
        positive='内在的力量使成功的、正确的信心、坦然的态度、以柔克刚的力量、有魅力的、精神力旺盛、有领导能力的、理性的处理态度、头脑清晰的。',
        negative='丧失信心的、失去生命力的、沮丧的、失败的、失去魅力的、无助的、情绪化的、任性而为的、退缩的、没有能力处理问题的、充满负面情绪的。'
    ), init=False)

    the_hermit: TarotCard = field(default=TarotCard(
        id=9, index='the_hermit', type='major_arcana', orig_name='The Hermit (IX)', name='隐者',
        intro='',
        words='寻求',
        desc='你正在从所有世俗的事物中退出，并转向内心，以实现神圣的真理。时机适合您找到生活中的最终目标并努力实现目标。您有限的物质欲望可以帮助你关注重要方面，并提出可行的解决方案。你有很强的领导能力，可以引导他人到达正确的目的地。不要过于习惯孤独，因为到后来你发现很难找到表达情感的人。',
        positive='有骨气的、清高的、有智慧的、有法力的、自我修养的，生命的智慧情境、用智慧排除困难的、给予正确的指导方向、有鉴赏力的、三思而后行的、谨慎行动的。',
        negative='假清高的、假道德的、没骨气、没有能力的、内心孤独寂寞的、缺乏支持的、错误的判断、被排挤的、没有足够智慧的、退缩的、自以为是的、与环境不合的。'
    ), init=False)

    wheel_of_fortune: TarotCard = field(default=TarotCard(
        id=10, index='wheel_of_fortune', type='major_arcana', orig_name='Wheel of Fortune (X)', name='命运之轮',
        intro='',
        words='轮回',
        desc='这表明积极的变化即将来临。您的自信随和将帮助您在不降低自尊的情况下度过生活的起伏。你必须更专注于你的意图，因为它会让你实现你的真正目标。生活已经为你制定了一个计划，保持乐观将带来繁荣和幸福。最重要的是，你的善行会带给你预期的结果。然而，不要自满，因为宇宙中没有任何东西是永恒的。',
        positive='忽然而来的幸运、即将转变的局势、顺应局势带来成功、把握命运给予的机会、意外的发展、不可预测的未来、突如其来的爱情运变动。',
        negative='突如其来的厄运、无法抵抗局势的变化、事情的发展失去了掌控、错失良机、无法掌握命运的关键时刻而导致失败、不利的突发状况、没有答案、被人摆布、有人暗中操作。'
    ), init=False)

    justice: TarotCard = field(default=TarotCard(
        id=11, index='justice', type='major_arcana', orig_name='Justice (XI)', name='正义',
        intro='',
        words='均衡',
        desc='表明您对自己的行为负责并做出相应判断。正如正义手中掌握的一样，你生活中的事件也会以平衡的方式解决，给你努力的成果。虽然你相信公平竞争，但没有必要总是说实话特别是在需要一点外交的情况下。此外，在对某人或某事作出判断时，最好在你的脑海中有一个目标，因为你必须在某些时候负责。',
        positive='明智的决定、看清了真相、正确的判断与选择、得到公平的待遇、走向正确的道路、理智与正义战胜一切、维持平衡的、诉讼得到正义与公平、重新调整使之平衡、不留情面的。',
        negative='错误的决定、不公平的待遇、没有原则的、缺乏理想的、失去方向的、不合理的、存有偏见的、冥顽不灵的、小心眼、过于冷漠的、不懂感情的。'
    ), init=False)

    the_hanged_man: TarotCard = field(default=TarotCard(
        id=12, index='the_hanged_man', type='major_arcana', orig_name='The Hanged Man (XII)', name='倒吊人',
        intro='',
        words='牺牲',
        desc='现在是时候采取一些旧的信念、态度或友谊。学会自己承担责任。然而这并不意味着你会责怪自己并阻止你继续前进。',
        positive='心甘情愿的牺牲奉献、以修练的方式来求道、不按常理的、反其道而行的、金钱上的损失、正专注于某个理想的、有坚定信仰的、长时间沈思的、需要沈淀的、成功之前的必经之道。',
        negative='精神上的虐待、心不甘情不愿的牺牲、损失惨重的、受到亏待的、严重漏财的、不满足的、冷淡的、自私自利的、要求回报的付出、逃离綑绑和束缚、以错误的方式看世界。'
    ), init=False)

    death: TarotCard = field(default=TarotCard(
        id=13, index='death', type='major_arcana', orig_name='Death (XIII)', name='死神',
        intro='',
        words='结束',
        desc='它像征着你生命中重要方面的终结，这反过来可能会带来更有价值的东西。虽然你可能最初发现很难继续进行新的事情和改变，但最终你会成为赢家。',
        positive='必须结束旧有的现状、面临重新开始的时刻到了、将不好的过去清除掉、专注于心的开始、挥别过去的历史、展开心的旅程、在心里做个了结、激烈的变化。',
        negative='已经历经了重生阶段了、革命已经完成、挥别了过去、失去了、结束了、失败了、病了、走出阴霾的时刻到了、没有转圜余地了。'
    ), init=False)

    temperance: TarotCard = field(default=TarotCard(
        id=14, index='temperance', type='major_arcana', orig_name='Temperance (XIV)', name='节制',
        intro='',
        words='净化',
        desc='它表明被赋予了清晰的视野，你可以避免极端，并试着保持温和的生活。您可能还会遇到旧的和新的想法之间的冲突，因此对于该怎么做感到困惑。该卡建议您耐心评估当前情况，然后根据您面临的任何新情况进行调整。',
        positive='良好的疏导、希望与承诺、得到调和、有节制的、平衡的、沟通良好的、健康的、成熟与均衡的个性、以机智处理问题、从过去的错误中学习、避免重蹈覆辙、净化的、有技巧的、有艺术才能的。',
        negative='缺乏能力的、技术不佳的、不懂事的、需反省的、失去平衡状态、沟通不良的、缺乏自我控制力、不确定的、重复犯错的、挫败的、受阻碍的、暂时的分离、希望与承诺遥遥无期。'
    ), init=False)

    the_devil: TarotCard = field(default=TarotCard(
        id=15, index='the_devil', type='major_arcana', orig_name='The Devil (XV)', name='恶魔',
        intro='',
        words='诅咒',
        desc='它表明你的恐惧，成瘾和其他负面冲动会限制你并让你把它们视为无法控制的事物。因此，您无法前进或采取任何建设性步骤。你也可能感到绝望或痴迷，甚至对生活抱有悲观的看法。该卡建议您摆脱这些负面模式，为您的生活带来积极的变化。',
        positive='不伦之恋、不正当的欲望、受诱惑的、违反世俗约定的、不道德的、有特殊的艺术才能、沉浸在消极里、沉溺在恐惧之中的、充满愤怒和怨恨、因恐惧而阻碍了自己、错误的方向、不忠诚的、秘密恋情。',
        negative='解脱了不伦之恋、挣脱了世俗的枷锁、不顾道德的、逃避的、伤害自己的、欲望的化解、被诅咒的、欲望强大的、不利的环境、盲目做判断、被唾弃的。'
    ), init=False)

    the_tower: TarotCard = field(default=TarotCard(
        id=16, index='the_tower', type='major_arcana', orig_name='The Tower (XVI)', name='塔',
        intro='',
        words='毁灭',
        desc='它代表您在意识到您之前关于特定情况是错误时的震惊和不安全感。习惯于生活的狭窄范围，你倾向于将某些思想和信仰视为不变。当然，你看到塔罗牌时感到动摇，因为你无法理解你是如何错误的。该卡建议您质疑您的看法，以便您可以分析问题所在。你可能会在这个过程中感到痛苦，但那是暂时的。它还要求你拆除自我的结构，以及你作为自卫手段创造的骄傲。只有这样，你才能在精神上成长。',
        positive='双方关系破裂、难以挽救的局面、组织瓦解了、损失惨重的、惨烈的破坏、毁灭性的事件、混乱的影响力、意外的发展、震惊扰人的问题、悲伤的、离别的、失望的、需要协助的、生活需要重建的。',
        negative='全盘覆没、一切都已破坏殆尽、毫无转圜余地的、失去了、不安的、暴力的、已经遭逢厄运了、急需重建的。'
    ), init=False)

    the_star: TarotCard = field(default=TarotCard(
        id=17, index='the_star', type='major_arcana', orig_name='The Star (XVII)', name='星星',
        intro='',
        words='希望',
        desc='它表明你正在经历一个充满活力，精神稳定，冷静和对自己更深刻理解的积极阶段。您过去所经历的艰难挑战正在帮助您进行彻底的转型并拥抱新的机遇。根据卡片的建议，您需要对自己的个性进行重大改变，并从新的角度看待生活。',
        positive='未来充满希望的、新的诞生、无限的希望、情感面精神面的希望、达成目标的、健康纯洁的、美好的未来、好运即将到来、美丽的身心、光明的时机、平静的生活、和平的处境。',
        negative='希望遥遥无期的、失去信心的、没有寄托的未来、失去目标的、感伤的、放弃希望的、好运远离的、毫无进展的、过于虚幻、假想的爱情运、偏执于理想、希望破灭的。'
    ), init=False)

    the_moon: TarotCard = field(default=TarotCard(
        id=18, index='the_moon', type='major_arcana', orig_name='The Moon (XVIII)', name='月亮',
        intro='',
        words='不安',
        desc='这意味着你对目前的情况非常不安全和怀疑。虽然周围的一切似乎都很正常，但你很清楚一个重大问题正在酝酿之中。此外，您在做梦时显然得到的直观信息似乎会导致更多的困惑，并且难以专注于生活中的重要事情。建议仅仅根据事实与内在的自我联系并理解现实。',
        positive='负面的情绪、不安和恐惧、充满恐惧感、阴森恐怖的感觉、黑暗的环境、景气低落、白日梦、忽略现实的、未知的危险、无法预料的威胁、胡思乱想的、不脚踏实地的、沉溺的、固执的。',
        negative='度过低潮阶段、心情平复、黑暗即将过去、曙光乍现、景气复甦、挥别恐惧、从忧伤中甦醒、恢复理智的、看清现实的、摆脱欲望的、脚踏实地的、走出谎言欺骗。'
    ), init=False)

    the_sun: TarotCard = field(default=TarotCard(
        id=19, index='the_sun', type='major_arcana', orig_name='The Sun (XIX)', name='太阳',
        intro='',
        words='生命',
        desc='你的积极能量将陪伴你所有的努力，并帮助你获得完成某事的快乐。您也可以与他人一起散发出最高品质。但是，这并不意味着你不需要做艰苦的工作; 通过你的自信，热情和辛劳，你将体验到一种新的洞察力，最终需要在最充实的时期中度过。该卡建议您过上简单的生活，以充分享受自由和启蒙的果实。',
        positive='前景看好的、运势如日中天的、成功的未来、光明正大的恋情、热恋的、美满的婚姻、丰收的、事件进行顺畅的、物质上的快乐、有成就的、满足的生活、旺盛。',
        negative='热情消退的、逐渐黯淡的、遭遇失败的、分离的、傲慢的、失去目标的、没有远景的、失去活力的、没有未来的、物质的贫乏、不快乐的人生阶段。'
    ), init=False)

    judgement: TarotCard = field(default=TarotCard(
        id=20, index='judgement', type='major_arcana', orig_name='Judgement (XX)', name='审判',
        intro='',
        words='复活',
        desc='它表示一段自我分析，集中和冥想的时期。根据这张卡片，你最近有一个顿悟，在那里你意识到以不同的方式过上生活的必要性。你现在的目标是让自己更加真实，这样你就能成为别人的一线希望。建议你根据自己的直觉和智慧做出决定，因为它们将在未来的日子里带来重大变化。',
        positive='死而复生、调整心态重新来过、内心的觉醒、观念的翻新、超脱了束缚的、满意的结果、苦难的结束、重新检视过去而得到新的启发、一个新的开始、一段新的关系。',
        negative='不公平的审判、无法度过考验的、旧事重演的、固执不改变的、自以为是的、对生命的看法狭隘的、后悔莫及的、自责的、不满意的结果、被击垮的。'
    ), init=False)

    the_world: TarotCard = field(default=TarotCard(
        id=21, index='the_world', type='major_arcana', orig_name='The World (XXI)', name='世界',
        intro='',
        words='达成',
        desc='这意味着您已经完成了一个生命中的重要里程碑。尽管遇到逆境，挑战和困难，你的努力终于得到了回报，因为你进入了一个承诺幸福，公众认可和钦佩的新阶段。你现在已经坚如磐石，随时准备勇敢面对任何局面而不会崩溃。现在重要的是利用您的知识和经验，通过教育或社会工作向世界回馈一些东西。随着卡片加强旅行和全球意识，您可能会搬家。',
        positive='完美的结局、重新开始的、生活上的完美境界、获得成功的、心理上的自由、完成成功的旅程、心灵的融合、自信十足带来成功、生活将有重大改变、获得完满的结果。',
        negative='无法完美的、一段过往的结束、缺乏自尊的、感觉难受的、态度悲观的、丑恶的感情、无法挽回的局势、不完美的结局、无法再继续的、残缺的。'
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


__all__ = [
    'TarotCards',
    'TarotPacks'
]
