"""
@Author         : Ailitonia
@Date           : 2025/4/29 19:33
@FileName       : ffmpy_patched
@Project        : omega-miya
@Description    : Pythonic interface for FFmpeg command line
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm


## ffmpy patched

Patched Version to support progress event.
Reference: https://github.com/Ch00k/ffmpy/issues/23
Source: https://github.com/astroza/ffmpy/blob/progress_support_v2/ffmpy.py
Raw: https://raw.githubusercontent.com/astroza/ffmpy/35659ee0ac9d62bdddead17726d56b64812a71aa/ffmpy.py

## quick example

```
>>> ff = FFmpeg(
...     inputs={'input.mp4': None},
...     outputs={'output.avi': None}
... )
>>> ff.run()
```
"""

import codecs
import errno
import os
import re
import shlex
import subprocess
import threading
from collections.abc import Callable, Sequence
from typing import Any

from nonebot.utils import run_sync

type FFProgressHandler = Callable[[FFState], Any]


class FFTool:
    def __init__(
            self,
            executable: str,
            global_options: Sequence[str] | str | None = None,
            inputs: dict[str, Sequence[str] | str | None] | None = None,
            outputs: dict[str, Sequence[str] | str | None] | None = None,
    ) -> None:
        self.executable = executable
        self._cmd: list[str] = [executable]

        global_options = global_options or []
        if isinstance(global_options, Sequence) and not isinstance(global_options, str):
            normalized_global_options: list[str] = []
            for opt in global_options:
                normalized_global_options += shlex.split(opt)
        else:
            normalized_global_options = shlex.split(global_options)

        self._cmd += normalized_global_options
        self._cmd += _merge_args_opts(inputs, add_input_option=True)
        self._cmd += _merge_args_opts(outputs)

        self.cmd: str = subprocess.list2cmdline(self._cmd)
        self.process: subprocess.Popen[bytes] | None = None

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(cmd={self.cmd!r})'

    def start(
            self,
            input_data: bytes | None = None,
            stdin: Any = None,
            stdout: Any = None,
            stderr: Any = None,
    ) -> None:
        if input_data is not None or stdin is None:
            stdin = subprocess.PIPE

        try:
            self.process = subprocess.Popen(
                self._cmd,
                stdin=stdin,
                stdout=stdout,
                stderr=stderr
            )
        except OSError as e:
            if e.errno == errno.ENOENT:
                raise FFExecutableNotFoundError(f"Executable '{self.executable}' not found")
            else:
                raise


class FFmpeg(FFTool):
    """Wrapper for various `FFmpeg <https://www.ffmpeg.org/>`_ related applications (ffmpeg, ...).

    Note:
        Option strings are tokenized with ``shlex.split`` in POSIX mode, so unescaped Windows
        backslash paths (``C:\\dir\\file``) lose their backslashes; prefer forward-slash paths
        or pre-split option lists.
    """

    def __init__(
            self,
            executable='ffmpeg',
            global_options: Sequence[str] | str | None = None,
            inputs: dict[str, Sequence[str] | str | None] | None = None,
            outputs: dict[str, Sequence[str] | str | None] | None = None,
            update_size: int = 2048,
    ) -> None:
        """Initialize FFmpeg command line wrapper.

        Compiles FFmpeg command line from passed arguments (executable path, options, inputs and
        outputs). ``inputs`` and ``outputs`` are dictionares containing inputs/outputs as keys and
        their respective options as values. One dictionary value (set of options) must be either a
        single space separated string, or a list or strings without spaces (i.e. each part of the
        option is a separate item of the list, the result of calling ``split()`` on the options
        string). If the value is a list, it cannot be mixed, i.e. cannot contain items with spaces.
        An exception are complex FFmpeg command lines that contain quotes: the quoted part must be
        one string, even if it contains spaces (see *Examples* for more info).
        For more info about FFmpeg command line format see `here
        <https://ffmpeg.org/ffmpeg.html#Synopsis>`_.

        :param str executable: path to ffmpeg executable; by default the ``ffmpeg`` command will be
            searched for in the ``PATH``, but can be overridden with an absolute path to ``ffmpeg``
            executable
        :param iterable global_options: global options passed to ``ffmpeg`` executable (e.g.
            ``-y``, ``-v`` etc.); can be specified either as a list/tuple/set of strings, or one
            space-separated string; by default no global options are passed
        :param dict inputs: a dictionary specifying one or more input arguments as keys with their
            corresponding options (either as a list of strings or a single space separated string) as
            values
        :param dict outputs: a dictionary specifying one or more output arguments as keys with their
            corresponding options (either as a list of strings or a single space separated string) as
            values
        """
        super().__init__(executable, global_options, inputs, outputs)
        self.update_size = update_size

    def run(
            self,
            input_data: bytes | None = None,
            stdin: Any = None,
            stdout: Any = None,
            on_progress: FFProgressHandler | None = None,
    ):
        """Execute FFmpeg command line.

        ``input_data`` can contain input for FFmpeg in case ``pipe`` protocol is used for
        input; it is written to the process stdin from a background thread, so large payloads
        cannot deadlock against the stderr reading loop. ``stdout`` specifies where to
        redirect the ``stdout`` of the process; if FFmpeg ``pipe`` protocol is used for
        output, pass ``subprocess.PIPE`` as ``stdout`` - the pipe is drained in the
        background and its content is returned as bytes. By default, no redirection is done,
        which means all output goes to running shell (this mode should normally only be used
        for debugging purposes).

        Returns a 2-tuple ``(stdout, stderr)``: ``stdout`` holds the raw bytes read from the
        process stdout pipe if it was piped (otherwise `None`), ``stderr`` holds the decoded
        tail (last ``30`` read chunks by default) of the process stderr.

        More info about ``pipe`` protocol `here <https://ffmpeg.org/ffmpeg-protocols.html#pipe>`_.

        :param input_data: input data for FFmpeg to deal with (audio, video etc.) as bytes (e.g.
            the result of reading a file in binary mode)
        :param stdin: replace FFmpeg ``stdin`` (default is `None` which means `subprocess.PIPE`)
        :param stdout: redirect FFmpeg ``stdout`` there (default is `None` which means no redirection)
        :param on_progress: a callable handle function to process running status; it receives an
            independent snapshot of the progress state on each update, safe to store or compare
        :return: a 2-tuple containing ``stdout`` and ``stderr`` of the process
        :rtype: tuple
        :raise: `FFRuntimeError` in case FFmpeg command exits with a non-zero code;
            `FFExecutableNotFoundError` in case the executable path passed was not valid
        """
        self.start(input_data, stdin, stdout, subprocess.PIPE)

        # input_data 由后台线程写入, 避免同步写入 stdin 与读取 stderr 相互阻塞
        if input_data is not None:
            if self.process is None or self.process.stdin is None:
                raise RuntimeError('Popen is not init or stdin is not piped')
            threading.Thread(target=_write_stdin, args=(self.process.stdin, input_data), daemon=True).start()

        return self.wait(on_progress)

    @run_sync
    def async_run(
            self,
            input_data: bytes | None = None,
            stdin: Any = None,
            stdout: Any = None,
            on_progress: FFProgressHandler | None = None,
    ):
        return self.run(input_data, stdin, stdout, on_progress)

    def wait(self, on_progress: FFProgressHandler | None = None, stderr_ring_size: int = 30):
        if self.process is None or self.process.stderr is None:
            raise RuntimeError('Popen is not init or stderr is not piped')

        stderr_ring: list[str] = []
        stdout_chunks: list[bytes] = []
        # UTF-8 增量解码, 容忍坏字节以及分块读取把多字节字符切开的情况
        decoder = codecs.getincrementaldecoder('utf-8')(errors='replace')
        ff_state = FFState()

        # 后台排空 stdout, 避免 pipe 协议输出写满缓冲区导致进程阻塞
        stdout_reader: threading.Thread | None = None
        if self.process.stdout is not None:
            stdout_reader = threading.Thread(
                target=_drain_pipe,
                args=(self.process.stdout, stdout_chunks),
                daemon=True,
            )
            stdout_reader.start()

        try:
            stderr_fileno = self.process.stderr.fileno()
            # EOF 驱动读尽 stderr: 进程退出会关闭管道写端, 读到 b'' 才代表管道已排空;
            # 若以 poll() 作为退出条件, 进程先退出时管道中尚未读取的尾部数据会被丢弃
            while True:
                latest_update = os.read(stderr_fileno, self.update_size)
                if not latest_update:
                    break
                latest_text = decoder.decode(latest_update)
                if ff_state.consume(latest_text) and on_progress is not None:
                    on_progress(ff_state.snapshot())
                stderr_ring.append(latest_text)
                if len(stderr_ring) > stderr_ring_size:
                    del stderr_ring[0]
            decoder_tail = decoder.decode(b'', final=True)
            if decoder_tail:
                stderr_ring.append(decoder_tail)
            # 回收子进程并取得退出码
            self.process.wait()
        except BaseException:
            # 进度回调或解析异常时终止进程, 避免遗留孤儿进程和泄漏的管道
            self.process.kill()
            # kill 后回收子进程, 避免僵尸进程/句柄泄漏
            self.process.wait()
            raise
        finally:
            if self.process.stdin is not None and not self.process.stdin.closed:
                try:
                    self.process.stdin.close()
                except OSError:
                    pass
            self.process.stderr.close()
            if stdout_reader is not None:
                stdout_reader.join()
            if self.process.stdout is not None:
                self.process.stdout.close()

        stderr_out = str.join('', stderr_ring)
        stdout_out = b''.join(stdout_chunks) if self.process.stdout is not None else None

        if self.process.returncode != 0:
            raise FFRuntimeError(self.cmd, self.process.returncode, stderr_out, stdout=stdout_out)

        return stdout_out, stderr_out


# FFmpeg 进度输出中 size 字段的单位换算表 (FFmpeg 5.x 起由 kB 改为 KiB/MiB/GiB 等 IEC 单位)
_SIZE_UNIT_SCALE: dict[str, int] = {
    'kB': 1000,
    'MB': 1000 ** 2,
    'GB': 1000 ** 3,
    'KiB': 1024,
    'MiB': 1024 ** 2,
    'GiB': 1024 ** 3,
}


class FFState:
    def __init__(self) -> None:
        self.frame = None
        self.fps = None
        self.size = None
        self.time = None

    def __str__(self):
        return f'frame: {self.frame!r}, fps: {self.fps!r}, size: {self.size!r}, time: {self.time!r}'

    def __repr__(self) -> str:
        return (f'{self.__class__.__name__}(frame={self.frame!r}, '
                f'fps={self.fps!r}, size={self.size!r}, time={self.time!r})')

    def snapshot(self) -> 'FFState':
        """返回当前状态的独立副本, 供进度回调保存历史状态而不被后续更新覆盖."""
        state = FFState()
        state.frame = self.frame
        state.fps = self.fps
        state.size = self.size
        state.time = self.time
        return state

    def consume(self, update: bytes | str) -> bool:
        if isinstance(update, bytes):
            update = update.decode(encoding='utf-8', errors='replace')
        raw_update_dict: dict[str, str] = {}
        for match in re.finditer(r'(?P<key>\S+)=\s*(?P<value>\S+)', update):
            raw_update_dict[match.group('key')] = match.group('value')
        updated: int = (
                self.update_frame(raw_update_dict.get('frame'))
                + self.update_fps(raw_update_dict.get('fps'))
                + self.update_size(raw_update_dict.get('size') or raw_update_dict.get('Lsize', ''))
                + self.update_time(raw_update_dict.get('time', ''))
        )
        return updated > 0

    def update_frame(self, raw_frame: str | None) -> bool:
        if raw_frame is None:
            return False
        try:
            self.frame = int(raw_frame)
        except ValueError:
            return False
        return True

    def update_fps(self, fps_raw: str | None) -> bool:
        if fps_raw is None:
            return False
        try:
            self.fps = float(fps_raw)
        except ValueError:
            return False
        return True

    def update_size(self, raw_size: str) -> bool:
        # 大小写敏感匹配, 兼容旧版 kB/MB/GB 与 FFmpeg 5.x+ 的 KiB/MiB/GiB
        digits_match = re.match(r'(?P<size>\d+)(?P<unit>kB|MB|GB|KiB|MiB|GiB)', raw_size)
        if digits_match is None:
            return False
        self.size = int(digits_match.group('size')) * _SIZE_UNIT_SCALE[digits_match.group('unit')]
        return True

    def update_time(self, raw_time: str) -> bool:
        time_units_match = re.match(r'(?P<hours>\d+):(?P<minutes>\d+):(?P<seconds>\d+\.\d+)', raw_time)
        if time_units_match is None:
            return False
        try:
            self.time = (int(time_units_match.group('hours')) * 3600
                         + int(time_units_match.group('minutes')) * 60
                         + float(time_units_match.group('seconds')))
        except ValueError:
            return False
        return True


class FFExecutableNotFoundError(Exception):
    """Raise when FFmpeg executable was not found."""


class FFRuntimeError(Exception):
    """Raise when FFmpeg command line execution returns a non-zero exit code.

    The resulting exception object will contain the attributes relates to command line execution:
    ``cmd``, ``exit_code``, ``stdout``, ``stderr``.
    """

    def __init__(self, cmd: str, exit_code: int, stderr: str | bytes, stdout: bytes | None = None) -> None:
        self.cmd = cmd
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr
        self.message = f'{self.cmd!r} exited with status {exit_code!r}\n\n\nSTDERR:\n{stderr or ""}'
        super().__init__(self.message)

    def __str__(self) -> str:
        return f'FFRuntimeError: {self.message}'

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}(cmd={self.cmd!r}, exit_code={self.exit_code!r}, stderr={self.stderr!r})'


def _drain_pipe(stream: Any, buffer: list[bytes]) -> None:
    """后台持续读取管道内容到缓冲, 防止写端因缓冲区写满而阻塞."""
    try:
        while chunk := stream.read(8192):
            buffer.append(chunk)
    except (ValueError, OSError):
        pass


def _write_stdin(stdin: Any, input_data: bytes) -> None:
    """后台向进程 stdin 写入数据, 写入完成或管道断裂时关闭 stdin."""
    try:
        stdin.write(input_data)
    except (ValueError, OSError):
        pass
    finally:
        try:
            stdin.close()
        except (ValueError, OSError):
            pass


def _merge_args_opts(args_opts_dict: dict[str, Any] | None, **kwargs: Any) -> list[Any]:
    """Merge options with their corresponding arguments.

    Iterates over the dictionary holding arguments (keys) and options (values). Merges each
    options string with its corresponding argument.

    :param dict args_opts_dict: a dictionary of arguments and options
    :param dict kwargs: *input_option* - if specified prepends ``-i`` to input argument
    :return: merged list of strings with arguments and their corresponding options
    :rtype: list
    """
    merged: list[Any] = []

    if not args_opts_dict:
        return merged

    for arg, opt in args_opts_dict.items():
        if isinstance(opt, str) or not isinstance(opt, Sequence):
            opt = shlex.split(opt or '')
        merged += opt

        if not arg:
            continue

        if 'add_input_option' in kwargs:
            merged.append('-i')

        merged.append(arg)

    return merged


__all__ = [
    'FFmpeg',
    'FFState',
    'FFTool',
    'FFProgressHandler',
    'FFRuntimeError',
    'FFExecutableNotFoundError',
]
