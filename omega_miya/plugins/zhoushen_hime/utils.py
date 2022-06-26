import datetime
from dataclasses import dataclass
from pydantic import BaseModel

from nonebot.adapters.onebot.v11.bot import Bot

from omega_miya.onebot_api import GoCqhttpBot
from omega_miya.result import BoolResult
from omega_miya.web_resource import HttpFetcher
from omega_miya.local_resource import TmpResource
from omega_miya.utils.process_utils import run_sync, run_async_catching_exception
from omega_miya.exception import PluginException


_TMP_FOLDER: TmpResource = TmpResource('zhoushen_hime')
"""缓存文件夹"""


class AssScriptException(PluginException):
    """字幕处理异常"""


class AssScriptLine(object):
    """ass字幕行类"""
    # 标记属性
    __STYLE: str = 'Style'
    __DIALOGUE: str = 'Dialogue'
    __COMMENT: str = 'Comment'
    __HEADER: str = 'Header'

    # 为方便时间计算, 字幕时间起点以0点为基准
    @classmethod
    def __time_handle(cls, time: str):
        split_time = time.split(':')

        # 检查时间格式
        if len(split_time) != 3:
            raise AssScriptException(f'时间格式错误, original_values: {repr(time)}')

        try:
            raw_hour = int(split_time[0])
            raw_min = int(split_time[1])
            # 分离秒数部分
            raw_sec_int, raw_sec_dec = map(lambda x: int(x), split_time[2].split('.'))
        except ValueError:
            raise AssScriptException(f'时间格式错误, original_values: {repr(time)}')

        if raw_sec_dec >= 100:
            raise AssScriptException(f'时间格式错误, original_values: {repr(time)}')

        # 转化为datetime.time类型
        return datetime.time(hour=raw_hour, minute=raw_min, second=raw_sec_int, microsecond=raw_sec_dec * 10000)

    # 定义实例时只赋值原始行信息, 其他属性由初始化函数处理
    def __init__(self, line_num: int, raw_text: str):
        self.__line_num: int = line_num
        self.__event_line_num: int = 0
        self.__raw_text: str = raw_text
        self.__is_init: bool = False
        self.__type = None
        self.__start_time = None
        self.__end_time = None
        self.__line_duration: datetime.timedelta = datetime.timedelta(0)
        self.__style = None
        self.__actor = None
        self.__left_margin = 0
        self.__right_margin = 0
        self.__vertical_margin = 0
        self.__effect = None
        self.__text = None

    @property
    def line_num(self):
        return self.__line_num

    @property
    def event_line_num(self):
        return self.__event_line_num

    @event_line_num.setter
    def event_line_num(self, event_line_num: int):
        self.__event_line_num = event_line_num

    @property
    def raw_text(self):
        return self.__raw_text

    @property
    def is_init(self):
        return self.__is_init

    @property
    def type(self):
        return self.__type

    @property
    def start_time(self):
        return self.__start_time

    @property
    def end_time(self):
        return self.__end_time

    @property
    def line_duration(self):
        return self.__line_duration

    @property
    def style(self):
        return self.__style

    @property
    def actor(self):
        return self.__actor

    @property
    def left_margin(self):
        return self.__left_margin

    @property
    def right_margin(self):
        return self.__right_margin

    @property
    def vertical_margin(self):
        return self.__vertical_margin

    @property
    def effect(self):
        return self.__effect

    @property
    def text(self):
        return self.__text

    @text.setter
    def text(self, text: str):
        self.__text = text

    def init(self) -> None:
        """初始化该单行, 只有初始化之后才能进行后续处理"""
        # 首先移除首尾空白及换行符
        self.__raw_text = self.__raw_text.strip('\n')
        self.__raw_text = self.__raw_text.strip()

        # 判断类型
        if self.__raw_text.startswith(self.__STYLE):
            self.__type = self.__STYLE
            split_line = self.__raw_text.split(',', maxsplit=22)

            self.__style = split_line[0].split(':')[1].strip()

            self.__is_init = True

        elif self.__raw_text.startswith(self.__DIALOGUE):
            self.__type = self.__DIALOGUE
            split_line = self.__raw_text.split(',', maxsplit=9)

            self.__start_time = self.__time_handle(time=split_line[1])
            self.__end_time = self.__time_handle(time=split_line[2])
            self.__line_duration = \
                datetime.datetime.combine(datetime.datetime.today(), self.__end_time) - \
                datetime.datetime.combine(datetime.datetime.today(), self.__start_time)
            self.__style = split_line[3]
            self.__actor = split_line[4]
            self.__left_margin = split_line[5]
            self.__right_margin = split_line[6]
            self.__vertical_margin = split_line[7]
            self.__effect = split_line[8]
            self.__text = split_line[9]

            self.__is_init = True

        elif self.__raw_text.startswith(self.__COMMENT):
            self.__type = self.__COMMENT
            split_line = self.__raw_text.split(',', maxsplit=9)

            self.__start_time = self.__time_handle(time=split_line[1])
            self.__end_time = self.__time_handle(time=split_line[2])
            self.__line_duration = \
                datetime.datetime.combine(datetime.datetime.today(), self.__end_time) - \
                datetime.datetime.combine(datetime.datetime.today(), self.__start_time)
            self.__style = split_line[3]
            self.__actor = split_line[4]
            self.__left_margin = split_line[5]
            self.__right_margin = split_line[6]
            self.__vertical_margin = split_line[7]
            self.__effect = split_line[8]
            self.__text = split_line[9]

            self.__is_init = True

        else:
            self.__type = self.__HEADER

            self.__is_init = True

    def generate(self) -> str:
        """生成新的event行"""
        if not self.__is_init:
            return self.raw_text

        if self.__type in [self.__HEADER, self.__STYLE]:
            return self.raw_text

        start_time = self.start_time.strftime('%H:%M:%S.%f')[:-4]
        if start_time[0] == '0':
            start_time = start_time[1:]

        end_time = self.end_time.strftime('%H:%M:%S.%f')[:-4]
        if end_time[0] == '0':
            end_time = end_time[1:]

        return f"{self.type}: 0,{start_time},{end_time},{self.style},{self.actor}," \
               f"{self.left_margin},{self.right_margin},{self.vertical_margin},{self.effect},{self.text}"

    def check_flash(self, threshold_time: int) -> tuple[int, datetime.timedelta]:
        """判断该行单行是否是闪轴

        :param threshold_time:
            闪轴判断阈值, 单位毫秒, 小于该值的为单行闪轴
        :return: [判断结果, 补轴时间差]
            1: 闪轴
            0: 非闪轴
            -1: 错误
        """
        if not self.__is_init:
            return -1, datetime.timedelta(0)

        if not self.__is_init:
            return -1, datetime.timedelta(0)

        if self.__type != self.__DIALOGUE:
            return -1, datetime.timedelta(0)

        threshold_duration = datetime.timedelta(microseconds=threshold_time * 1000)
        diff_duration = threshold_duration - self.__line_duration

        if self.__line_duration < threshold_duration:
            return 1, diff_duration
        else:
            return 0, diff_duration

    def change_start_time(self, delta: datetime.timedelta) -> None:
        if not self.__is_init:
            return

        self.__start_time = (datetime.datetime.combine(datetime.datetime.today(), self.__start_time) + delta).time()
        self.__line_duration = self.__line_duration - delta

    def change_end_time(self, delta: datetime.timedelta) -> None:
        if not self.__is_init:
            return

        self.__end_time = (datetime.datetime.combine(datetime.datetime.today(), self.__end_time) + delta).time()
        self.__line_duration = self.__line_duration + delta

    def __repr__(self):
        return f'<AssScriptLine(line_num={self.__line_num}, event_line_num={self.__event_line_num}, ' \
               f'type={self.__type}, raw_text={self.__raw_text}, ' \
               f'start_time={self.__start_time}, end_time={self.__end_time}, line_duration={self.__line_duration}, ' \
               f'style={self.__style}, actor={self.__actor}, left_margin={self.__left_margin}, ' \
               f'right_margin={self.__right_margin}, vertical_margin={self.__vertical_margin}, ' \
               f'effect={self.__effect}, text={self.__text})>'


class AssScriptLineTool(object):
    """ass字幕event行工具类"""
    # 标记属性
    __STYLE: str = 'Style'
    __DIALOGUE: str = 'Dialogue'
    __COMMENT: str = 'Comment'
    __HEADER: str = 'Header'

    @classmethod
    def check_continuous(
            cls,
            start_line: AssScriptLine,
            end_line: AssScriptLine,
            style_mode: bool
    ) -> tuple[int, datetime.timedelta]:
        """判断该行两行是否是连轴(即前轴结束时间等于后轴开始时间)

        :param start_line: 前轴
        :param end_line: 后轴
        :param style_mode: 是否启用样式判断
            True: 两行样式不同不进行比较, 直接返回0
            False: 两行样式不同也会进行比较
        :return: [判断结果, 轴间时间差]
            1: 连轴
            0: 非连轴
            -1: 错误
        """
        if not all([start_line.is_init, end_line.is_init]):
            return -1, datetime.timedelta(0)

        if start_line.type != cls.__DIALOGUE or end_line.type != cls.__DIALOGUE:
            return -1, datetime.timedelta(0)

        lines_duration = \
            datetime.datetime.combine(datetime.datetime.today(), end_line.start_time) - \
            datetime.datetime.combine(datetime.datetime.today(), start_line.end_time)

        if style_mode:
            if start_line.style != end_line.style:
                return 0, lines_duration

        if start_line.end_time == end_line.start_time:
            return 1, datetime.timedelta(0)
        else:
            return 0, lines_duration

    @classmethod
    def check_overlap(
            cls,
            start_line: AssScriptLine,
            end_line: AssScriptLine,
            style_mode: bool
    ) -> tuple[int, datetime.timedelta]:
        """判断该行两行是否是叠轴(即前轴结束时间大于后轴开始时间)

        :param start_line: 前轴
        :param end_line: 后轴
        :param style_mode: 是否启用样式判断
            True: 两行样式不同不进行比较, 直接返回0
            False: 两行样式不同也会进行比较
        :return: [判断结果, 轴间时间差]
            1: 叠轴
            0: 非叠轴
            -1: 错误
        """
        if not all([start_line.is_init, end_line.is_init]):
            return -1, datetime.timedelta(0)

        if start_line.type != cls.__DIALOGUE or end_line.type != cls.__DIALOGUE:
            return -1, datetime.timedelta(0)

        if style_mode:
            if start_line.style != end_line.style:
                return 0, datetime.timedelta(0)

        lines_duration = \
            datetime.datetime.combine(datetime.datetime.today(), end_line.start_time) - \
            datetime.datetime.combine(datetime.datetime.today(), start_line.end_time)

        if start_line.end_time > end_line.start_time:
            return 1, lines_duration
        else:
            return 0, lines_duration

    @classmethod
    def check_flash(
            cls,
            start_line: AssScriptLine,
            end_line: AssScriptLine,
            threshold_time: int,
            style_mode: bool
    ) -> tuple[int, datetime.timedelta]:
        """判断该行两行是否是闪轴(即前轴结束时间与后轴开始时间差小于一定值)

        :param start_line: 前轴
        :param end_line: 后轴
        :param threshold_time: 闪轴判断阈值, 单位毫秒, 小于该值的为单行闪轴
        :param style_mode: 是否启用样式判断
            True: 两行样式不同不进行比较, 直接返回0
            False: 两行样式不同也会进行比较
        :return: [判断结果, 轴间时间差]
            1: 闪轴
            0: 非闪轴
            -1: 错误
        """
        if not all([start_line.is_init, end_line.is_init]):
            return -1, datetime.timedelta(0)

        if start_line.type != cls.__DIALOGUE or end_line.type != cls.__DIALOGUE:
            return -1, datetime.timedelta(0)

        lines_duration = \
            datetime.datetime.combine(datetime.datetime.today(), end_line.start_time) - \
            datetime.datetime.combine(datetime.datetime.today(), start_line.end_time)

        if style_mode:
            if start_line.style != end_line.style:
                return 0, lines_duration

        threshold_duration = datetime.timedelta(microseconds=threshold_time * 1000)

        # 是负数的话就是叠轴了
        if lines_duration < datetime.timedelta(0):
            return -1, lines_duration

        if lines_duration < threshold_duration:
            return 1, lines_duration
        else:
            return 0, lines_duration


class HandleResult(BaseModel):
    """处理结果"""
    output_txt: str
    character_count: int
    overlap_count: int
    flash_count: int


@dataclass
class OutputHandleResult:
    """对外输出的处理结果"""
    output_txt_file: TmpResource
    output_ass_file: TmpResource
    character_count: int
    overlap_count: int
    flash_count: int


class ZhouChecker(AssScriptLineTool):
    """ass字幕文件处理工具"""
    # 需要校对的关键词
    __proofreading_words = ['???', '？？？']

    # 要替换的标点, key为替换前, value为替换后
    __punctuation_replace = {
        '。。。': '...',
        '。': ' ',
        '‘': '「',
        '’': '」',
        '・・・': '...',
        '···': '...',
        '“': '『',
        '”': '』',
        '、': ' ',
        '~': '～',
        '!': '！',
        '?': '？',
        '　': ' ',
        '[': '「',
        ']': '」',
        '【': '「',
        '】': '」'
    }

    # 不知道咋换的标点
    __punctuation_ignore = ["'", '"', '，', '/']

    def __init__(
            self,
            file: TmpResource,
            single_threshold_time: int = 500,
            multi_threshold_time: int = 300,
            flash_mode: bool = False,
            style_mode: bool = False,
            fx_mode: bool = True):
        """初始化工具类实例

        :param file: ass字幕文件
        :param single_threshold_time: 单行闪轴判断阈值, 单位毫秒, 默认500
        :param multi_threshold_time: 多行闪轴判断阈值, 单位毫秒, 默认300
        :param flash_mode: 是否启用单行闪轴强制去除(可能导致多行闪轴), 默认False
        :param style_mode: 是否启用样式判断, 默认False
        :param fx_mode: 是否检查含特效的行, 默认True
        """
        self.__file = file
        self.__single_threshold_time = single_threshold_time
        self.__multi_threshold_time = multi_threshold_time
        self.__flash_mode = flash_mode
        self.__style_mode = style_mode
        self.__fx_mode = fx_mode
        self.__is_init = False
        self.__event_lines: list[AssScriptLine] = list()
        self.__header_lines: list[AssScriptLine] = list()
        self.__styles = set()

    async def _init_file(self, auto_style: bool = False) -> BoolResult:
        """载入文件并初始化字幕内容

        :param auto_style: 是否启用智能样式, 启用后会检查字幕文件使用样式数, 若只使用一种则自动停用style_mode
        """
        if not self.__file.path.exists() or not self.__file.path.is_file():
            return BoolResult(error=True, info='FileNotExist', result=False)

        if self.__file.path.suffix not in ['.ass', '.ASS']:
            return BoolResult(error=True, info='NotAssFileTypeError', result=False)

        async with self.__file.async_open('r', encoding='utf8') as af:
            line_count = 0
            event_line_count = 0
            for line in await af.readlines():
                line_count += 1
                ass_line = AssScriptLine(line_num=line_count, raw_text=line)
                ass_line.init()
                if ass_line.type in ['Dialogue', 'Comment']:
                    event_line_count += 1
                    ass_line.event_line_num = event_line_count
                    if self.__fx_mode:
                        self.__styles.add(ass_line.style)
                        self.__event_lines.append(ass_line)
                    else:
                        if ass_line.effect:
                            self.__header_lines.append(ass_line)
                        else:
                            self.__styles.add(ass_line.style)
                            self.__event_lines.append(ass_line)
                else:
                    self.__header_lines.append(ass_line)

            if auto_style:
                if len(self.__styles) == 1:
                    self.__style_mode = False
                else:
                    self.__style_mode = True

        self.__is_init = True
        return BoolResult(error=False, info='Success', result=True)

    def _handle(self) -> HandleResult:
        """处理时轴检查"""
        if not self.__is_init:
            raise RuntimeError('Handle without initializing file')

        flash_mode = self.__flash_mode
        style_mode = self.__style_mode

        # 用于写入txt的内容
        out_log = '--- 自动审轴姬 v1.1 by: Ailitonia ---\n\n'
        if style_mode:
            out_log += '--- 样式模式已启用: 样式不同的行之间不会相互进行比较 ---\n\n'
        else:
            out_log += '--- 样式模式已禁用: 所有行之间都相互进行比较 ---\n\n'

        out_log += '--- 字符检查部分 ---\n'
        # 开始字符检查
        character_count = 0
        for line in self.__event_lines:
            # 检查需要校对的关键词
            if any(key in line.text for key in self.__proofreading_words):
                out_log += f'第{line.event_line_num}行可能翻译没听懂, 校对请注意一下: "{line.text}"\n'
                character_count += 1
            # 检查标点符号
            if any(punctuation in line.text for punctuation in self.__punctuation_ignore):
                out_log += f'第{line.event_line_num}行轴标点有问题（不确定怎么改）, 请注意一下: "{line.text}"\n'
                character_count += 1
            elif any(punctuation in line.text for punctuation in self.__punctuation_replace.keys()):
                for key, value in self.__punctuation_replace.items():
                    if key in line.text:
                        line.text = line.text.replace(key, value)
                        out_log += f'第{line.event_line_num}行轴的{key}标点有问题, 但是我给你换成了{value}\n'
                        character_count += 1
        out_log += '--- 字符检查部分结束 ---\n\n'

        # 开始锤轴部分
        out_log += '--- 锤轴部分 ---\n'
        overlap_count = 0
        flash_count = 0

        # 构建event_line字典
        event_lines = dict()
        for line in self.__event_lines:
            event_lines[line.event_line_num] = line

        # 直接暴力遍历整个字典
        seq = 0
        for start_line_num, start_line in event_lines.items():
            seq += 1
            if seq >= len(event_lines):
                # 这里是最后一行了
                break
            # 由前向后搜索, 匹配最近符合的两行. 处理完直接跳出
            for end_line_num, end_line in list(event_lines.items())[seq:]:

                # 开启style_mode后跳过不比较不同style的行
                if style_mode:
                    if start_line.style != end_line.style:
                        continue

                # 检查自己是不是闪轴
                single_flash, single_flash_lines_duration = start_line.check_flash(
                    threshold_time=self.__single_threshold_time)

                # 检查连轴
                continuous, continuous_lines_duration = self.check_continuous(
                    start_line=start_line, end_line=end_line, style_mode=style_mode)

                # 检查叠轴
                overlap, overlap_duration = self.check_overlap(
                    start_line=start_line, end_line=end_line, style_mode=style_mode)

                # 检查轴间闪轴
                multi_flash, multi_flash_lines_duration = self.check_flash(
                    start_line=start_line, end_line=end_line,
                    threshold_time=self.__multi_threshold_time, style_mode=style_mode)

                # 处理叠轴
                if overlap == 1:
                    overlap_count += 1
                    out_log += f"第{start_line.event_line_num}行轴和第{end_line.event_line_num}行可能是叠轴, 请检查一下\n"

                # 处理闪轴
                # 是单行闪轴还和后面连轴了
                if single_flash == 1 and continuous == 1:
                    flash_count += 1
                    out_log += f"第{start_line.event_line_num}行轴是闪轴" \
                               f"（{start_line.line_duration.microseconds / 1000}ms）, " \
                               f"但是它和{end_line.event_line_num}行轴是连轴, 所以看着改吧\n"
                    break
                # 是单行闪轴而且补也补不够的神轴
                elif single_flash == 1 and continuous != 1 and start_line.end_time < end_line.start_time \
                        and single_flash_lines_duration > multi_flash_lines_duration:
                    if flash_mode:
                        flash_count += 1
                        before_duration = start_line.line_duration
                        start_line.change_end_time(delta=multi_flash_lines_duration)
                        after_change_time = start_line.end_time
                        out_log += f"第{start_line.event_line_num}行轴（{before_duration.microseconds / 1000}ms）" \
                                   f"要是不闪就和第{end_line.event_line_num}行轴之间是叠轴了, " \
                                   f"不过我姑且给你连上了（{after_change_time}）\n"
                        break
                    else:
                        flash_count += 1
                        out_log += f"第{start_line.event_line_num}行轴（{start_line.line_duration.microseconds / 1000}ms）" \
                                   f"要是不闪就和第{end_line.event_line_num}行轴之间是叠轴了, " \
                                   f"这啥神轴啊, 你自己看着改吧\n"
                        break
                # 是单行闪轴而且补上后就会和后面的轴变成闪轴的神轴
                elif single_flash == 1 and continuous != 1 and start_line.end_time < end_line.start_time \
                        and single_flash_lines_duration > \
                        (multi_flash_lines_duration - datetime.timedelta(
                            microseconds=self.__multi_threshold_time * 1000)):
                    if flash_mode:
                        flash_count += 1
                        before_duration = start_line.line_duration
                        start_line.change_end_time(delta=multi_flash_lines_duration)
                        after_change_time = start_line.end_time
                        out_log += f"第{start_line.event_line_num}行轴（{before_duration.microseconds / 1000}ms）" \
                                   f"要是不闪就和第{end_line.event_line_num}行轴之间是闪轴了, " \
                                   f"不过我姑且给你连上了（{after_change_time}）\n"
                        break
                    else:
                        flash_count += 1
                        out_log += f"第{start_line.event_line_num}行轴（{start_line.line_duration.microseconds / 1000}ms）" \
                                   f"要是不闪就和第{end_line.event_line_num}行轴之间是闪轴了, " \
                                   f"这啥神轴啊, 你自己看着改吧\n"
                        break
                # 上面的都没有发生而且已经连轴了就跳过
                elif continuous == 1:
                    break
                # 正常的单行闪轴
                elif single_flash == 1:
                    flash_count += 1
                    before_duration = start_line.line_duration
                    before_change_time = start_line.end_time
                    start_line.change_end_time(delta=single_flash_lines_duration)
                    after_change_time = start_line.end_time
                    out_log += f"第{start_line.event_line_num}行轴是闪轴（{before_duration.microseconds / 1000}ms）, " \
                               f"但是我给你改好了, 从原来的{before_change_time}改成了{after_change_time}\n"
                    break
                # 处理轴间闪轴
                elif multi_flash == 1 and continuous == 0:
                    flash_count += 1
                    start_line.change_end_time(delta=multi_flash_lines_duration)
                    after_change_time = start_line.end_time
                    out_log += f"第{start_line.event_line_num}行轴和第{end_line.event_line_num}行轴之间是闪轴" \
                               f"（{multi_flash_lines_duration.microseconds / 1000}ms）, 不过我给你连上了（{after_change_time}）\n"
                    break
        out_log += '--- 锤轴部分结束 ---\n\n' \
                   '--- 审轴信息 ---\n' \
                   f'原始文件: {self.__file.path.name}\n' \
                   f'报告生成时间: {datetime.datetime.now()}\n' \
                   f'符号及疑问文本问题: {character_count}\n' \
                   f'叠轴问题: {overlap_count}\n' \
                   f'闪轴问题: {flash_count}'

        # 刷新数据
        self.__event_lines.clear()
        self.__event_lines.extend(event_lines.values())

        result = HandleResult(output_txt=out_log, character_count=character_count,
                              overlap_count=overlap_count, flash_count=flash_count)
        return result

    async def handle(self, auto_style: bool = False) -> OutputHandleResult:
        """处理时轴检查

        :param auto_style: 是否启用智能样式, 启用后会检查字幕文件使用样式数, 若只使用一种则自动停用style_mode
        """
        init_result = await self._init_file(auto_style=auto_style)
        if init_result.error:
            raise RuntimeError(init_result.info)

        handle_result = await run_sync(self._handle)()

        # 输出文件
        time_text = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
        output_txt_file = _TMP_FOLDER(f"{self.__file.path.name}_{time_text}_锤.txt")
        output_ass_file = _TMP_FOLDER(f"{self.__file.path.name}_{time_text}_改.ass")

        async with output_txt_file.async_open('w', encoding='utf-8') as af:
            await af.write(handle_result.output_txt)

        async with output_ass_file.async_open('w', encoding='utf-8-sig') as af:
            header_lines_text = [x.raw_text for x in self.__header_lines]
            out_header_lines = '\n'.join(header_lines_text)

            event_lines_text = [x.generate() for x in self.__event_lines]
            out_event_lines = '\n'.join(event_lines_text)

            await af.writelines([out_header_lines, '\n', out_event_lines])

        result = OutputHandleResult(output_txt_file=output_txt_file,
                                    output_ass_file=output_ass_file,
                                    character_count=handle_result.character_count,
                                    overlap_count=handle_result.overlap_count,
                                    flash_count=handle_result.flash_count)
        return result


@run_async_catching_exception
async def download_file(url: str, file_name: str) -> TmpResource:
    """下载文件到本地, 使用自定义文件名, 直接覆盖同名文件"""
    file_content = await HttpFetcher().get_bytes(url=url)
    if file_content.status != 200:
        raise RuntimeError(f'NetworkError, status code {file_content.status}')

    local_file = _TMP_FOLDER('download', file_name)
    async with local_file.async_open('wb') as af:
        await af.write(file_content.result)
    return local_file


@run_async_catching_exception
async def upload_result_file(group_id: int | str, bot: Bot, result_data: OutputHandleResult) -> None:
    """上传审轴结果到群文件"""
    gocq_bot = GoCqhttpBot(bot=bot)
    group_file_info = await gocq_bot.get_group_root_files(group_id=group_id)
    group_folders = group_file_info.folders

    folder_id = None
    if group_folders:
        for folder in group_folders:
            if folder.folder_name == '锤轴记录':
                folder_id = folder.folder_id
                break

    await gocq_bot.upload_group_file(group_id=group_id, folder=folder_id,
                                     file=result_data.output_txt_file.resolve_path,
                                     name=result_data.output_txt_file.path.name)

    await gocq_bot.upload_group_file(group_id=group_id, folder=folder_id,
                                     file=result_data.output_ass_file.resolve_path,
                                     name=result_data.output_ass_file.path.name)


__all__ = [
    'ZhouChecker',
    'download_file',
    'upload_result_file'
]
