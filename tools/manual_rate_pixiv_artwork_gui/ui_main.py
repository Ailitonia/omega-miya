"""
@Author         : Ailitonia
@Date           : 2024/9/8 17:11
@FileName       : ui_main
@Project        : ailitonia-toolkit
@Description    : 
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm
"""

from tkinter import StringVar, Tk, messagebox, ttk

from .data_source import BasePixivArtworkSource


class ManualRatingPixivArtworkMain[T: BasePixivArtworkSource]:

    def __init__(self, source: T) -> None:
        self.root: Tk = Tk()
        self.source: T = source

        # 构造布局
        self.root.title(f'Pixiv 作品分级 - {self.source.title_name}')

        # 顶部功能区布局框架
        top_frm = ttk.Frame(self.root, padding=5)
        top_frm.pack(side='top', fill='x')

        # 右侧布局按钮框架
        button_frm = ttk.Frame(top_frm, padding=5)
        button_frm.pack(side='right')

        # 初始化工作目录和文件列表显示框架
        info_frm = ttk.Frame(top_frm, padding=5)
        info_frm.pack(side='top', anchor='center', expand=True, fill='x')

        # 选择图片及加载工作目录组件
        file_frm = ttk.Frame(info_frm, padding=5)
        file_frm.pack(side='top', fill='x')
        ttk.Label(file_frm, text='当前文件: ').pack(side='left')
        self._file_entry = ttk.Entry(file_frm, textvariable=StringVar())
        self._file_entry.pack(fill='x')

        remaining_num_frm = ttk.Frame(info_frm, padding=5)
        remaining_num_frm.pack(side='top', fill='x')
        ttk.Label(remaining_num_frm, text='剩余文件数: ').pack(side='left')
        self._remaining_num_entry = ttk.Entry(remaining_num_frm, textvariable=StringVar())
        self._remaining_num_entry.pack(fill='x')

        # 底部图片显示及分级按钮布局框架
        separator = ttk.Separator(self.root, orient='horizontal')
        separator.pack(fill='x', pady=2)
        show_frm = ttk.Frame(self.root, padding=5)
        show_frm.pack(side='left', fill='x')
        rate_frm = ttk.Frame(self.root, padding=5)
        rate_frm.pack(side='right', fill='x')

        # 图片显示
        self._image_label = ttk.Label(show_frm)
        self._image_label.pack()

        # 主要显示控件元组
        show_components = (self._image_label, self._file_entry, self._remaining_num_entry)

        # 主要流程按钮
        ttk.Button(
            button_frm,
            text='选择图片并初始化',
            command=lambda: self.source.select_current(*show_components)
        ).pack()
        ttk.Button(button_frm, text='生成导入文件', command=self.source.merge).pack()
        ttk.Button(button_frm, text='退出', command=self._shutdown).pack()

        # 分级按钮
        ttk.Button(
            rate_frm, text='(0) General | 萌图', padding=6,
            command=lambda: self.source.set_current_general(*show_components)
        ).pack(anchor='center')
        self.root.bind('<Control-KeyPress-0>', lambda x: self.source.set_current_general(*show_components))

        ttk.Button(
            rate_frm, text='(1) Sensitive | 涩图', padding=6,
            command=lambda: self.source.set_current_sensitive(*show_components)
        ).pack(anchor='center')
        self.root.bind('<Control-KeyPress-1>', lambda x: self.source.set_current_sensitive(*show_components))

        ttk.Button(
            rate_frm, text='(2) Questionable | 软色情', padding=6,
            command=lambda: self.source.set_current_questionable(*show_components)
        ).pack(anchor='center')
        self.root.bind('<Control-KeyPress-2>', lambda x: self.source.set_current_questionable(*show_components))

        ttk.Button(
            rate_frm, text='(3) Explicit | R18', padding=6,
            command=lambda: self.source.set_current_explicit(*show_components)
        ).pack(anchor='center')
        self.root.bind('<Control-KeyPress-3>', lambda x: self.source.set_current_explicit(*show_components))

        ttk.Button(
            rate_frm, text='(P) Pass | 跳过', padding=6,
            command=lambda: self.source.next_image(*show_components)
        ).pack(anchor='center')
        self.root.bind('<Control-KeyPress-Right>', lambda x: self.source.next_image(*show_components))

        ttk.Button(
            rate_frm, text='(R) Reset | 重置', padding=6,
            command=lambda: self.source.set_current_reset(*show_components)
        ).pack(anchor='center')
        self.root.bind('<Control-KeyPress-Down>', lambda x: self.source.set_current_reset(*show_components))

        ttk.Button(
            rate_frm, text='(I) Ignored | 忽略', padding=6,
            command=lambda: self.source.set_current_ignored(*show_components)
        ).pack(anchor='center')

        # 拦截关闭按钮处理
        self.root.protocol('WM_DELETE_WINDOW', self._shutdown)

    def _shutdown(self) -> None:
        ok_exist = messagebox.askokcancel(message='退出前记得生成导出文件, 确认要退出吗?', icon='question',
                                          title='退出确认')
        if not ok_exist:
            return

        self.root.destroy()

    def run(self):
        self.root.mainloop()


__all__ = [
    'ManualRatingPixivArtworkMain',
]
