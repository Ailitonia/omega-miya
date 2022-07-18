import random
from pydantic import BaseModel


class Operator(BaseModel):
    name: str
    star: int
    limited: bool  # 限定
    recruit_only: bool  # 公招限定/凭证交易所兑换
    event_only: bool  # 活动获得干员
    special_only: bool  # 升变/异格干员


class UpEvent(BaseModel):
    star: int  # 对应up星级
    operator: list[Operator]  # 干员列表
    zoom: float  # up提升倍率


# 用户抽取的保底概率提升计数
USERS_UP_COUNT: dict[int, int] = {}


# 当期up干员
UP_OPERATOR: list[UpEvent] = [
    UpEvent(
        star=6,
        operator=[
            Operator(name='多萝西/Dorothy', star=6, limited=False, recruit_only=False, event_only=False,
                     special_only=False)
        ],
        zoom=0.5
    ),
    UpEvent(
        star=5,
        operator=[
            Operator(name='承曦格雷伊/Greyy the Lightningbearer', star=5, limited=False, recruit_only=False,
                     event_only=False, special_only=False),
            Operator(name='白面鸮/Ptilopsis', star=5, limited=False, recruit_only=False, event_only=False,
                     special_only=False),
        ],
        zoom=0.5
    )
]

ALL_OPERATOR: list[Operator] = [
    Operator(name='多萝西/Dorothy', star=6, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='承曦格雷伊/Greyy the Lightningbearer', star=5, limited=False, recruit_only=False, event_only=False,
             special_only=False),
    Operator(name='星源/Astgenne', star=5, limited=False, recruit_only=False, event_only=True, special_only=False),
    Operator(name='黑键/Ebenholz', star=6, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='濯尘芙蓉/Hibiscus the Purifier', star=5, limited=False, recruit_only=False, event_only=False,
             special_only=False),
    Operator(name='车尔尼/Czerny', star=5, limited=False, recruit_only=False, event_only=True, special_only=False),
    Operator(name='埃拉托/Erato', star=5, limited=False, recruit_only=False, event_only=True, special_only=False),
    Operator(name='归溟幽灵鲨/Irene', star=6, limited=True, recruit_only=False, event_only=False, special_only=False),
    Operator(name='艾丽妮/Irene', star=6, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='流明/Lumen', star=6, limited=False, recruit_only=False, event_only=True, special_only=False),
    Operator(name='掠风/Windflit', star=5, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='号角/Horn', star=6, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='洛洛/Rockrock', star=5, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='海蒂/Heidi', star=5, limited=False, recruit_only=False, event_only=True, special_only=False),
    Operator(name='褐果/Chestnut', star=4, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='菲亚梅塔/Fiammetta', star=6, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='风丸/Kazemaru', star=5, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='见行者/Enforcer', star=5, limited=False, recruit_only=False, event_only=True, special_only=False),
    Operator(name='澄闪/Goldenglow', star=6, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='夏栎/Quercus', star=5, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='令/Ling', star=6, limited=True, recruit_only=False, event_only=False, special_only=False),
    Operator(name='老鲤/Lee', star=6, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='夜半/Blacknight', star=5, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='寒芒克洛丝/Kroos the Keen Glint', star=5, limited=False, recruit_only=False, event_only=True,
             special_only=False),
    Operator(name='九色鹿/Nine-Colored Deer', star=5, limited=False, recruit_only=False, event_only=True,
             special_only=False),
    Operator(name='暮落/Shalem', star=5, limited=False, recruit_only=False, event_only=True, special_only=False),
    Operator(name='灵知/Aurora', star=6, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='极光/Aurora', star=5, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='耶拉/Kjera', star=5, limited=False, recruit_only=False, event_only=True, special_only=False),
    Operator(name='耀骑士临光/Nearl the Radiant Knight', star=6, limited=True, recruit_only=False, event_only=False,
             special_only=False),
    Operator(name='焰尾/Flametail', star=6, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='蚀清/Corroserum', star=5, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='野鬃/Wild Mane', star=5, limited=False, recruit_only=False, event_only=True, special_only=False),
    Operator(name='蜜莓/Honeyberry', star=5, limited=False, recruit_only=True, event_only=True, special_only=False),
    Operator(name='布丁/Pudding', star=4, limited=False, recruit_only=True, event_only=True, special_only=False),
    Operator(name='正义骑士号/"Justice Knight"', star=1, limited=False, recruit_only=True, event_only=False,
             special_only=False),
    Operator(name='远牙/Fartooth', star=6, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='灰毫/Ashlock', star=5, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='琴柳/Saileach', star=6, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='桑葚/Mulberry', star=5, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='罗比菈塔/Roberta', star=4, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name="假日威龙陈/Ch'en the Holungday", star=6, limited=True, recruit_only=False, event_only=False,
             special_only=False),
    Operator(name='水月/Mizuki', star=6, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='羽毛笔/La Pluma', star=5, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='龙舌兰/Tequila', star=5, limited=False, recruit_only=False, event_only=True, special_only=False),
    Operator(name='帕拉斯/Pallas', star=6, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='卡涅利安/Carnelian', star=6, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='绮良/Kirara', star=5, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='贝娜/Bena', star=5, limited=False, recruit_only=False, event_only=True, special_only=False),
    Operator(name='深靛/Indigo', star=4, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='浊心斯卡蒂/Skadi the Corrupting Heart', star=6, limited=True, recruit_only=False, event_only=False,
             special_only=False),
    Operator(name="凯尔希/Kal'tsit", star=6, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='歌蕾蒂娅/Gladiia', star=6, limited=False, recruit_only=False, event_only=True, special_only=False),
    Operator(name='赤冬/Akafuyu', star=5, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='异客/Passenger', star=6, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='熔泉/Toddifons', star=5, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='暴雨/Heavyrain', star=5, limited=False, recruit_only=False, event_only=True, special_only=False),
    Operator(name='灰烬/ASH', star=6, limited=True, recruit_only=False, event_only=True, special_only=False),
    Operator(name='霜华/FROST', star=5, limited=True, recruit_only=False, event_only=True, special_only=False),
    Operator(name='闪击/BLITZ', star=5, limited=True, recruit_only=False, event_only=True, special_only=False),
    Operator(name='战车/TACHANKA', star=5, limited=True, recruit_only=False, event_only=True, special_only=False),
    Operator(name='嵯峨/Saga', star=6, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='风笛/Bagpipe', star=6, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='推进之王/Siege', star=6, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name="陈/Ch'en", star=6, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='赫拉格/Hellagur', star=6, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='煌/Blaze', star=6, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='棘刺/Thorns', star=6, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='山/Mountain', star=6, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='史尔特尔/Surtr', star=6, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='斯卡蒂/Skadi', star=6, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='银灰/SilverAsh', star=6, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='黑/Schwarz', star=6, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='空弦/Archetto', star=6, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='迷迭香/Rosmontis', star=6, limited=True, recruit_only=False, event_only=False, special_only=False),
    Operator(name='能天使/Exusiai', star=6, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='早露/Роса', star=6, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='W/W', star=6, limited=True, recruit_only=False, event_only=False, special_only=False),
    Operator(name='泥岩/Mudrock', star=6, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='年/Nian', star=6, limited=True, recruit_only=False, event_only=False, special_only=False),
    Operator(name='塞雷娅/Saria', star=6, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='森蚺/Eunectes', star=6, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='瑕光/Blemishine', star=6, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='星熊/Hoshiguma', star=6, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='闪灵/Shining', star=6, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='夜莺/Nightingale', star=6, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='安洁莉娜/Angelina', star=6, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='铃兰/Suzuran', star=6, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='麦哲伦/Magallan', star=6, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='艾雅法拉/Eyjafjalla', star=6, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='刻俄柏/Ceobe', star=6, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='莫斯提马/Mostima', star=6, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='夕/Dusk', star=6, limited=True, recruit_only=False, event_only=False, special_only=False),
    Operator(name='伊芙利特/Ifrit', star=6, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='阿/Aak', star=6, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='傀影/Phantom', star=6, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='温蒂/Weedy', star=6, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='德克萨斯/Texas', star=5, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='格拉尼/Grani', star=5, limited=False, recruit_only=False, event_only=True, special_only=False),
    Operator(name='极境/Elysium', star=5, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='贾维/Chiave', star=5, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='凛冬/Зима', star=5, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='苇草/Reed', star=5, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='柏喙/Bibeak', star=5, limited=False, recruit_only=False, event_only=True, special_only=False),
    Operator(name='暴行/Savage', star=5, limited=False, recruit_only=False, event_only=False, special_only=True),
    Operator(name='鞭刃/Whislash', star=5, limited=False, recruit_only=False, event_only=True, special_only=False),
    Operator(name='布洛卡/Broca', star=5, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='断崖/Ayerscarpe', star=5, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='芙兰卡/Franka', star=5, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='拉普兰德/Lappland', star=5, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='诗怀雅/Swire', star=5, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='燧石/Flint', star=5, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='星极/Astesia', star=5, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='炎客/Flamebringer', star=5, limited=False, recruit_only=False, event_only=True, special_only=False),
    Operator(name='因陀罗/Indra', star=5, limited=False, recruit_only=True, event_only=False, special_only=False),
    Operator(name='幽灵鲨/Specter', star=5, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='铸铁/Sideroca', star=5, limited=False, recruit_only=False, event_only=True, special_only=False),
    Operator(name='安哲拉/Andreana', star=5, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='奥斯塔/Aosta', star=5, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='白金/Platinum', star=5, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='灰喉/GreyThroat', star=5, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='蓝毒/Blue Poison', star=5, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='普罗旺斯/Provence', star=5, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='慑砂/Sesa', star=5, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='守林人/Firewatch', star=5, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='四月/April', star=5, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='送葬人/Executor', star=5, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='陨星/Meteorite', star=5, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='拜松/Bison', star=5, limited=False, recruit_only=False, event_only=True, special_only=False),
    Operator(name='吽/Hung', star=5, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='火神/Vulcan', star=5, limited=False, recruit_only=True, event_only=False, special_only=False),
    Operator(name='可颂/Croissant', star=5, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='雷蛇/Liskarm', star=5, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='临光/Nearl', star=5, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='石棉/Asbestos', star=5, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='白面鸮/Ptilopsis', star=5, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='赫默/Silence', star=5, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='华法琳/Warfarin', star=5, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='图耶/Tuye', star=5, limited=False, recruit_only=False, event_only=True, special_only=False),
    Operator(name='微风/Breeze', star=5, limited=False, recruit_only=True, event_only=True, special_only=False),
    Operator(name='锡兰/Ceylon', star=5, limited=False, recruit_only=False, event_only=True, special_only=False),
    Operator(name='絮雨/Whisperain', star=5, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='亚叶/Folinic', star=5, limited=False, recruit_only=False, event_only=True, special_only=False),
    Operator(name='初雪/Pramanix', star=5, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='格劳克斯/Glaucus', star=5, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='空/Sora', star=5, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='梅尔/Mayer', star=5, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='巫恋/Shamare', star=5, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='稀音/Scene', star=5, limited=False, recruit_only=False, event_only=True, special_only=False),
    Operator(name='月禾/Tsukinogi', star=5, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='真理/Истина', star=5, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='阿米娅/Amiya', star=5, limited=False, recruit_only=False, event_only=False, special_only=True),
    Operator(name='爱丽丝/Iris', star=5, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='薄绿/Mint', star=5, limited=False, recruit_only=False, event_only=True, special_only=False),
    Operator(name='惊蛰/Leizi', star=5, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='苦艾/Absinthe', star=5, limited=False, recruit_only=False, event_only=True, special_only=False),
    Operator(name='莱恩哈特/Leonhardt', star=5, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='蜜蜡/Beeswax', star=5, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='特米米/Tomimi', star=5, limited=False, recruit_only=False, event_only=True, special_only=False),
    Operator(name='天火/Skyfire', star=5, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='炎狱炎熔/Purgatory', star=5, limited=False, recruit_only=False, event_only=False, special_only=True),
    Operator(name='夜魔/Nightmare', star=5, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='红/Projekt Red', star=5, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='槐琥/Waai Fu', star=5, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='卡夫卡/Kafka', star=5, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='罗宾/Robin', star=5, limited=False, recruit_only=False, event_only=True, special_only=False),
    Operator(name='狮蝎/Manticore', star=5, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='食铁兽/FEater', star=5, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='乌有/Mr.Nothing', star=5, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='雪雉/Snowsant', star=5, limited=False, recruit_only=False, event_only=True, special_only=False),
    Operator(name='崖心/Cliffheart', star=5, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='豆苗/Beanstalk', star=4, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='红豆/Vigna', star=4, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='清道夫/Scavenger', star=4, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='桃金娘/Myrtle', star=4, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='讯使/Courier', star=4, limited=False, recruit_only=False, event_only=True, special_only=False),
    Operator(name='艾丝黛尔/Estelle', star=4, limited=False, recruit_only=True, event_only=False, special_only=False),
    Operator(name='缠丸/Matoimaru', star=4, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='杜宾/Dobermann', star=4, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='断罪者/Conviction', star=4, limited=False, recruit_only=False, event_only=True, special_only=False),
    Operator(name='芳汀/Arene', star=4, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='杰克/Jackie', star=4, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='刻刀/Cutter', star=4, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='猎蜂/Beehunter', star=4, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='慕斯/Mousse', star=4, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='霜叶/Frostleaf', star=4, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='宴/Utage', star=4, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='安比尔/Ambriel', star=4, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='白雪/ShiraYuki', star=4, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='红云/Vermeil', star=4, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='杰西卡/Jessica', star=4, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='流星/Meteor', star=4, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='梅/May', star=4, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='松果/Pinecone', star=4, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='酸糖/Aciddrop', star=4, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='古米/Гум', star=4, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='坚雷/Dur-nar', star=4, limited=False, recruit_only=False, event_only=True, special_only=False),
    Operator(name='角峰/Matterhorn', star=4, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='泡泡/Bubble', star=4, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='蛇屠箱/Cuora', star=4, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='调香师/Perfumer', star=4, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='嘉维尔/Gavial', star=4, limited=False, recruit_only=False, event_only=True, special_only=False),
    Operator(name='末药/Myrrh', star=4, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='清流/Purestream', star=4, limited=False, recruit_only=False, event_only=True, special_only=False),
    Operator(name='苏苏洛/Sussurro', star=4, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='波登可/Podenco', star=4, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='地灵/Earthspirit', star=4, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='深海色/Deepcolor', star=4, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='格雷伊/Greyy', star=4, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='卡达/Click', star=4, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='夜烟/Haze', star=4, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='远山/Gitano', star=4, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='阿消/Shaw', star=4, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='暗索/Rope', star=4, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='孑/Jaye', star=4, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='砾/Gravel', star=4, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='伊桑/Ethan', star=4, limited=False, recruit_only=True, event_only=True, special_only=False),
    Operator(name='芬/Fang', star=3, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='翎羽/Plume', star=3, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='香草/Vanilla', star=3, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='玫兰莎/Melantha', star=3, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='泡普卡/Popukar', star=3, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='月见夜/Midnight', star=3, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='安德切尔/Adnachiel', star=3, limited=False, recruit_only=True, event_only=False, special_only=False),
    Operator(name='克洛丝/Kroos', star=3, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='空爆/Catapult', star=3, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='斑点/Spot', star=3, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='卡缇/Cardigan', star=3, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='米格鲁/Beagle', star=3, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='安赛尔/Ansel', star=3, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='芙蓉/Hibiscus', star=3, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='梓兰/Orchid', star=3, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='史都华德/Steward', star=3, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='炎熔/Lava', star=3, limited=False, recruit_only=False, event_only=False, special_only=False),
    Operator(name='夜刀/Yato', star=2, limited=False, recruit_only=True, event_only=False, special_only=False),
    Operator(name='巡林者/Rangers', star=2, limited=False, recruit_only=True, event_only=False, special_only=False),
    Operator(name='黑角/Noir Corne', star=2, limited=False, recruit_only=True, event_only=False, special_only=False),
    Operator(name='12F/12F', star=2, limited=False, recruit_only=True, event_only=False, special_only=False),
    Operator(name='杜林/Durin', star=2, limited=False, recruit_only=True, event_only=False, special_only=False),
    Operator(name='Castle-3/Castle-3', star=1, limited=False, recruit_only=True, event_only=False, special_only=False),
    Operator(name='Lancet-2/Lancet-2', star=1, limited=False, recruit_only=True, event_only=False, special_only=False),
    Operator(name='THRM-EX/Thermal-EX', star=1, limited=False, recruit_only=True, event_only=False, special_only=False)
]


def draw_one_operator(user_id: int) -> str:
    global USERS_UP_COUNT
    draw_count = USERS_UP_COUNT.get(user_id, 0)

    # 首先要先决定出的星级
    if 0 <= draw_count <= 50:
        # 没有抽过或者刚刚重置过, 无概率提升
        star = random.sample([6, 5, 4, 3], counts=[2, 8, 50, 40], k=1)[0]
        USERS_UP_COUNT.update({user_id: draw_count + 1})
    elif 50 < draw_count <= 99:
        # 触发概率提升
        if random.randint(1, 100) <= (draw_count - 49) * 2:
            # 触发概率提升则为6星
            star = 6
        else:
            # 否则则在5, 4, 3星中随机
            star = random.sample([5, 4, 3], counts=[8, 50, 40], k=1)[0]
        USERS_UP_COUNT.update({user_id: draw_count + 1})
    else:
        # 多半是出bug了, 强制重置次数
        star = random.sample([6, 5, 4, 3], counts=[2, 8, 50, 40], k=1)[0]
        USERS_UP_COUNT.update({user_id: 1})

    # 如果出6星了就重置up次数
    if star == 6:
        USERS_UP_COUNT.update({user_id: 0})

    # 生成对应卡池和处理up事件
    up_event = [(x.zoom, x.operator) for x in UP_OPERATOR if x.star == star]

    if up_event:
        # 对应星级有up活动
        up_zoom, up_operator = up_event[0]
        # 确定是否up
        if random.random() <= up_zoom:
            # up了
            acquire_operator = random.sample([x.name for x in up_operator], k=1)[0]
        else:
            # 没up成
            acquire_operator = random.sample(
                [x.name for x in ALL_OPERATOR if (
                        x.star == star and not any([x.limited, x.event_only, x.recruit_only, x.special_only]))],
                k=1)[0]
    else:
        # 对应星级无up活动
        acquire_operator = random.sample(
            [x.name for x in ALL_OPERATOR if (
                    x.star == star and not any([x.limited, x.event_only, x.recruit_only, x.special_only]))],
            k=1)[0]

    return f"【{star}★】{acquire_operator}"


def draw_one_arknights(draw_seed: int) -> str:
    # 获得当期up干员
    up_operators = []
    for item in [x.operator for x in UP_OPERATOR]:
        up_operators.extend([f"【{x.star}★】{x.name}" for x in item])
    up_up_operator = '\n'.join(up_operators)
    up_info = f'当期UP干员:\n{up_up_operator}'

    acquire_operator = draw_one_operator(user_id=draw_seed)

    return f"获得了以下干员:\n{acquire_operator}\n{'='*12}\n{up_info}"


def draw_ten_arknights(draw_seed: int) -> str:
    # 获得当期up干员
    up_operators = []
    for item in [x.operator for x in UP_OPERATOR]:
        up_operators.extend([f"【{x.star}★】{x.name}" for x in item])
    up_up_operator = '\n'.join(up_operators)
    up_info = f'当期UP干员:\n{up_up_operator}'

    acquire_operators = []
    for i in range(10):
        acquire_operators.append(draw_one_operator(user_id=draw_seed))

    acquire_operator = '\n'.join(acquire_operators)

    return f"获得了以下干员:\n{acquire_operator}\n{'='*12}\n{up_info}"


__all__ = [
    'draw_one_arknights',
    'draw_ten_arknights'
]
