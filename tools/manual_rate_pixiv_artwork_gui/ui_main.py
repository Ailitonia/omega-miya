"""
@Author         : Ailitonia
@Date           : 2024/9/8 17:11
@FileName       : ui_main
@Project        : omega-miya
@Description    : GUI 主界面
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

import asyncio
from tkinter import StringVar, TclError, Tk, messagebox, ttk
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .data_source import BaseArtworkSource


class ManualRatingArtworkMain[T: 'BaseArtworkSource']:

    def __init__(self, source: T) -> None:
        self.root: Tk = Tk()
        self.source: T = source

        # 构造布局
        self.root.title(f'ArtworkCollection 作品分级 - {self.source.title_name}')

        # ------------------------------------------------------------------ #
        # 顶部功能区布局框架
        # ------------------------------------------------------------------ #

        top_frm = ttk.Frame(self.root, padding=5)
        top_frm.pack(side='top', fill='x')

        # 顶部子框架: 右侧按钮
        top_button_frm = ttk.Frame(top_frm, padding=5)
        top_button_frm.pack(side='right')

        # 顶部子框架: 左侧初始化工作目录和文件列表显示框架
        top_info_frm = ttk.Frame(top_frm, padding=5)
        top_info_frm.pack(side='top', anchor='center', expand=True, fill='x')

        # 顶部子框架 top_info_frm 内容填充: 选择图片及加载工作目录组件
        file_frm = ttk.Frame(top_info_frm, padding=5)
        file_frm.pack(side='top', fill='x')
        ttk.Label(file_frm, text='当前文件: ').pack(side='left')

        # 初始化当前文件入口输入控件, 绑定实例变量供后续交互
        self._file_entry = ttk.Entry(file_frm, textvariable=StringVar())
        self._file_entry.pack(fill='x')

        # 顶部子框架 top_info_frm 内容填充: 剩余文件显示组件
        remaining_frm = ttk.Frame(top_info_frm, padding=5)
        remaining_frm.pack(side='top', fill='x')
        ttk.Label(remaining_frm, text='剩余文件: ').pack(side='left')

        # 初始化剩余文件输入控件, 绑定实例变量供后续交互
        self._remaining_entry = ttk.Entry(remaining_frm, textvariable=StringVar())
        self._remaining_entry.pack(fill='x')

        # ------------------------------------------------------------------ #
        # 上下功能区分隔线
        # ------------------------------------------------------------------ #

        separator = ttk.Separator(self.root, orient='horizontal')
        separator.pack(fill='x', pady=2)

        # ------------------------------------------------------------------ #
        # 底部功能区布局框架
        # ------------------------------------------------------------------ #

        # 底部子框架: 图片显示区
        show_frm = ttk.Frame(self.root, padding=5)
        show_frm.pack(side='left', fill='x')

        # 底部子框架: 分级按钮布局区
        foot_button_frm = ttk.Frame(self.root, padding=5)
        foot_button_frm.pack(side='right', fill='x')
        rating_button_frm = ttk.Frame(foot_button_frm, padding=5)
        rating_button_frm.pack(side='top', anchor='center', fill='x')

        rating_confirmed_button_frm = ttk.Frame(rating_button_frm, padding=5)
        rating_confirmed_button_frm.pack(side='left', fill='x')
        ttk.Label(rating_confirmed_button_frm, text='C(3): HUMAN_CONFIRMED').pack(side='top')

        rating_featured_button_frm = ttk.Frame(rating_button_frm, padding=5)
        rating_featured_button_frm.pack(side='top', fill='x')
        ttk.Label(rating_featured_button_frm, text='C(4): FEATURED').pack(side='top')

        extra_button_frm = ttk.Frame(foot_button_frm, padding=5)
        extra_button_frm.pack(side='top', anchor='center', fill='x')

        # 初始化图片显示控件, 绑定实例变量供后续交互
        self._image_label = ttk.Label(show_frm)
        self._image_label.pack()

        # ------------------------------------------------------------------ #
        # 显示控件元组, 统一执行方法传参
        # ------------------------------------------------------------------ #

        show_components: tuple[ttk.Label, ttk.Entry, ttk.Entry] = (
            self._image_label,
            self._file_entry,
            self._remaining_entry,
        )

        # ------------------------------------------------------------------ #
        # 按钮及其功能执行方法实现
        # ------------------------------------------------------------------ #

        # 顶部右侧按钮
        ttk.Button(
            top_button_frm,
            text='选择图片/初始化',
            command=lambda: self.source.select_current(*show_components)
        ).pack()
        ttk.Button(top_button_frm, text='生成导入文件', command=self.source.merge).pack()
        ttk.Button(top_button_frm, text='退出', command=self._shutdown).pack()

        # Classification: HUMAN_CONFIRMED 类型的评级按钮
        ttk.Button(
            rating_confirmed_button_frm,
            text='(0) General | 萌图',
            padding=6,
            command=lambda: self.source.set_current_general_c3(*show_components)
        ).pack(anchor='center')
        self.root.bind('<Control-KeyPress-0>', lambda x: self.source.set_current_general_c3(*show_components))

        ttk.Button(
            rating_confirmed_button_frm,
            text='(1) Sensitive | 涩图',
            padding=6,
            command=lambda: self.source.set_current_sensitive_c3(*show_components)
        ).pack(anchor='center')
        self.root.bind('<Control-KeyPress-1>', lambda x: self.source.set_current_sensitive_c3(*show_components))

        ttk.Button(
            rating_confirmed_button_frm,
            text='(2) Questionable | R18',
            padding=6,
            command=lambda: self.source.set_current_questionable_c3(*show_components)
        ).pack(anchor='center')
        self.root.bind('<Control-KeyPress-2>', lambda x: self.source.set_current_questionable_c3(*show_components))

        ttk.Button(
            rating_confirmed_button_frm,
            text='(3) Explicit | R18+(G)',
            padding=6,
            command=lambda: self.source.set_current_explicit_c3(*show_components)
        ).pack(anchor='center')
        self.root.bind('<Control-KeyPress-3>', lambda x: self.source.set_current_explicit_c3(*show_components))

        # Classification: FEATURED 类型的评级按钮
        ttk.Button(
            rating_featured_button_frm,
            text='(0) General | 萌图',
            padding=6,
            command=lambda: self.source.set_current_general_c4(*show_components)
        ).pack(anchor='center')

        ttk.Button(
            rating_featured_button_frm,
            text='(1) Sensitive | 涩图',
            padding=6,
            command=lambda: self.source.set_current_sensitive_c4(*show_components)
        ).pack(anchor='center')

        ttk.Button(
            rating_featured_button_frm,
            text='(2) Questionable | R18',
            padding=6,
            command=lambda: self.source.set_current_questionable_c4(*show_components)
        ).pack(anchor='center')

        ttk.Button(
            rating_featured_button_frm,
            text='(3) Explicit | R18+(G)',
            padding=6,
            command=lambda: self.source.set_current_explicit_c4(*show_components)
        ).pack(anchor='center')

        # 特殊类型的评级按钮
        ttk.Button(
            extra_button_frm,
            text='(P) Pass | 跳过',
            padding=6,
            command=lambda: self.source.load_next(*show_components)
        ).pack(anchor='center')
        self.root.bind('<Control-KeyPress-Right>', lambda x: self.source.load_next(*show_components))

        ttk.Button(
            extra_button_frm,
            text='(R) Reset | 重置',
            padding=6,
            command=lambda: self.source.set_current_reset(*show_components)
        ).pack(anchor='center')
        self.root.bind('<Control-KeyPress-Down>', lambda x: self.source.set_current_reset(*show_components))

        ttk.Button(
            extra_button_frm,
            text='(I) Ignored | 忽略',
            padding=6,
            command=lambda: self.source.set_current_ignored(*show_components)
        ).pack(anchor='center')

        # 拦截关闭按钮处理
        self.root.protocol('WM_DELETE_WINDOW', self._shutdown)

    def _shutdown(self) -> None:
        ok_exist = messagebox.askokcancel(
            message='退出前记得生成导出文件, 确认要退出吗?',
            icon='question',
            title='退出确认',
        )
        if not ok_exist:
            return

        self.root.destroy()

    def run(self) -> None:
        asyncio.run(self._run_mainloop())

    async def _run_mainloop(self) -> None:
        """单线程事件循环中交替驱动 Tk 事件与 asyncio 任务"""
        while True:
            try:
                if not self.root.winfo_exists():
                    break
                self.root.update()
            except TclError:
                break
            await asyncio.sleep(0.02)


__all__ = [
    'ManualRatingArtworkMain',
]
