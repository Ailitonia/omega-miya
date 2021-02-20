"""
修改自https://github.com/HakuRemu/ZhouShen_Hime
能用就行(
"""
import os
import re
import datetime
from nonebot import logger
from omega_miya.utils.Omega_Base import Result
from .asstm import *


class ZhouChecker(object):
    def __init__(self, file_path: str, flash_mode: bool):
        self.__flash_mode = flash_mode
        self.__file_path = file_path
        self.__init_flag = False
        self.__lines = list()
        self.__headers = list()

    def init_file(self) -> Result:
        if not os.path.exists(self.__file_path):
            return Result(error=True, info='File not exist', result=-1)

        if os.path.splitext(self.__file_path)[-1] not in ['.ass', '.ASS']:
            return Result(error=True, info='File type error, not ass', result=-1)

        with open(self.__file_path, 'r', encoding='utf8') as f_ass:
            for line in f_ass.readlines():
                if line.startswith('Dialogue'):
                    self.__lines.append(line)
                elif line.startswith('Comment'):
                    self.__lines.append(line)
                else:
                    self.__headers.append(line)
        self.__init_flag = True
        return Result(error=False, info='Success', result=0)

    def handle(self) -> Result:
        if not self.__init_flag:
            logger.error('Handle processing error: 时轴文件未未初始化')
            return Result(error=True, info='Handle without init file', result={})
        logger.info('Handle processing started')

        # 用于写入txt的内容
        outlog = '字符检查部分：\n'
        character_count = 0

        for i in range(len(self.__lines)):
            # 当前行的text内容
            line_text = self.__lines[i].split(',')[9]

            # 出现需要校对的关键词
            key_words = ['ong', '???', '？？？', '校对']

            # 跳过注释
            if self.__lines[i].startswith('Comment') or re.search(r",fx,", self.__lines[i]):
                pass
            # 检查需要校对的关键词
            elif any(key in line_text for key in key_words):
                outlog += '第{}行可能翻译没听懂，校对请注意一下————{}\n'.format(i + 1, line_text.replace('\n', ''))
                character_count += 1
            # 检查标点符号
            else:
                if any(punctuation in line_text for punctuation in punctuation_ignore):
                    outlog += '第{}行轴标点有问题（不确定怎么改），请注意一下————{}\n'.format(i + 1, line_text)
                    character_count += 1
                elif any(punctuation in line_text for punctuation in punctuation_replace.keys()):
                    for key, value in punctuation_replace.items():
                        if key in line_text:
                            self.__lines[i] = self.__lines[i].replace(key, value)
                            outlog += "第{}行轴的{}标点有问题，但是我给你换成了{}\n".format(i + 1, key, value)
                            character_count += 1

        # 开始锤轴啦
        zhou_count = 0
        # 读取时间和位置
        start, end, location = [], [], []
        for i, l in enumerate(self.__lines):
            if (not re.search(r",fx,", l)) and l[:7] != 'Comment':
                start.append(l.split(',')[1])
                end.append(l.split(',')[2])
                location.append(i + 1)

        outlog += '\n锤轴部分：\n'

        length = len(start)  # 总行数

        # 先找出连轴
        zhou = []
        for i in range(length):
            lianzhou = []
            lianzhou_flag = False
            for k in zhou:
                if location[i] in k:
                    lianzhou_flag = True
                    break
            if lianzhou_flag:
                continue
            else:
                lianzhou.append(location[i])
                tmp = end[i]
                for j in range(length):
                    if start[j] == tmp:
                        tmp = end[j]
                        lianzhou.append(location[j])
                zhou.append(lianzhou)

        # 查行内的闪轴
        for i in range(length):
            shenzhou = False  # 是不是六亲不认轴
            # 先锤行自己的闪轴
            tdelta1 = timedelta(end[i], start[i])  # 轴的时间
            if 0.5 > tdelta1 > 0:
                tneeded = 0.5 - tdelta1  # 算出要加的时间
                for j in range(length):
                    tdelta2 = timedelta(start[j], end[i])
                    if tneeded + 0.3 >= tdelta2 > 0:
                        shenzhou = True  # 遇到神轴了
                        if self.__flash_mode:
                            outlog += "第{}行轴（{}ms）要是不闪就和第{}行轴之间是闪轴了，不过我姑且给你连上了（{}）\n".format(
                                location[i], tdelta1 * 1000, location[j], start[j])
                            zhou_count += 1
                            self.__lines[location[i] - 1] = self.__lines[location[i] - 1].replace(
                                self.__lines[location[i] - 1].split(',')[2], start[j])
                            end[i] = start[j]
                        else:
                            outlog += "第{}行轴（{}ms）要是不闪就和第{}行轴之间是闪轴了，草这啥神轴啊，你自己看着改吧\n\n".format(
                                location[i], tdelta1 * 1000, location[j])
                            zhou_count += 1
                        break
                if not shenzhou:  # 没遇到神轴
                    # 看看有没有什么轴和它连着
                    kanguole = False
                    for j in zhou:
                        if location[i] in j and len(j) > 1 and location[i] < max(j):
                            outlog += "第{}行轴是闪轴（{}ms），但是它和{}行轴是连轴，所以看着改吧\n\n".format(
                                location[i], tdelta1 * 1000, j[j.index(location[i]) + 1])
                            zhou_count += 1
                            kanguole = True
                            break
                    if not kanguole:
                        if self.__flash_mode:
                            tmp = timeplus(end[i], tneeded)
                            outlog += "第{}行轴是闪轴（{}ms），但是我给你改好了\n以防万一告诉你一下从{}改成了{}\n\n".format(
                                location[i], tdelta1 * 1000, end[i], tmp)
                            zhou_count += 1
                            self.__lines[location[i] - 1] = self.__lines[location[i] - 1].replace(
                                self.__lines[location[i] - 1].split(',')[2], tmp)
                            end[i] = tmp
                        else:
                            outlog += "第{}行轴是闪轴（{}ms），请注意一下\n\n".format(location[i], tdelta1 * 1000)
                            zhou_count += 1

            # 再锤行与行之间的闪轴
            # 考虑到联动轴里面可能会有按样式分的情况
            # 打算每次都遍历一遍
            # 再考虑到看的这行轴可能和别的轴之间是连轴
            # 或者你从连轴中间往外看
            # 草联动轴咋这么恶心

            buyongkan = False
            # 先看看现在看的这行轴是不是连轴的一部分
            for j in zhou:
                if location[i] in j and len(j) > 1 and location[i] < max(j):  # 看的这行轴是一串连轴的一部分，那就跳过这行轴
                    buyongkan = True
                    break
            if buyongkan:
                continue
            else:  # 如果看的不是连轴，就先找找有没有闪轴
                for k in range(length):
                    tdelta = timedelta(start[k], end[i])
                    if 0.3 > tdelta > 0:
                        # 发现有闪轴就检查一下这条是不是连轴的一部分
                        for j in zhou:
                            if location[k] in j and len(j) > 1 and min(j) < location[k] < max(j):
                                buyongkan = True
                                break
                        if buyongkan:
                            break
                        else:
                            tdelta = timedelta(start[k], end[i])  # 看看两个轴之间到底差了多少
                            if self.__flash_mode:
                                outlog += "第{}行轴和第{}行轴之间是闪轴（{}ms），不过我给你连上了（{}）\n".format(
                                    location[i], location[k], tdelta * 1000, start[k])
                                zhou_count += 1
                                self.__lines[location[i] - 1] = self.__lines[location[i] - 1].replace(
                                    self.__lines[location[i] - 1].split(',')[2], start[k])
                                end[i] = start[k]
                            else:
                                tneeded = 0.3 - tdelta  # 看看要改多少
                                candidate = timeminus(end[i], tneeded)
                                outlog += "第{}行轴和第{}行轴之间是闪轴（{}ms），建议分开成{}或者连上（{}）\n".format(
                                    location[i], location[k], tdelta * 1000, candidate, start[k])
                                zhou_count += 1

        # 输出路径
        output_txt_path = f"{self.__file_path}_{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}_锤.txt"
        output_ass_path = f"{self.__file_path}_{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}-改.ass"
        with open(output_txt_path, 'w', encoding='utf-8') as ft:
            ft.writelines(outlog)
        with open(output_ass_path, 'w', encoding='utf-8-sig') as fn:
            fn.writelines(self.__headers)
            fn.writelines(self.__lines)
        logger.info(f'Handle processing finished, result:\n{outlog}')

        result_dict = {'output_txt_path': output_txt_path, 'output_ass_path': output_ass_path,
                       'character_count': character_count, 'zhou_count': zhou_count}

        return Result(error=False, info='Success', result=result_dict)
