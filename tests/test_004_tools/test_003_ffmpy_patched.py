"""
@Author         : Ailitonia
@Date           : 2026/9/18 23:25
@FileName       : test_003_ffmpy_patched
@Project        : omega-miya
@Description    : ffmpeg 包装工具单元测试
@GitHub         : https://github.com/Ailitonia
@Software       : PyCharm

仅覆盖输入输出与命令行生成逻辑, 不调用真实 ffmpeg: run/wait 路径使用伪造的 Popen 与 os.read。
"""

import errno
import subprocess
import time
from typing import Any

import pytest

# 完整的 ffmpeg 进度行样例
_PROGRESS_LINE = 'frame= 100 fps= 30 q=-1.0 size= 128kB time=00:00:10.00 bitrate= 104.5kbits/s speed=0.986x'


class _FakeStdin:
    """模拟 Popen 的 stdin 管道, 记录写入内容"""

    def __init__(self) -> None:
        self.written: list[bytes] = []
        self.closed = False

    def write(self, data: bytes) -> int:
        if self.closed:
            raise ValueError('write to closed pipe')
        self.written.append(data)
        return len(data)

    def close(self) -> None:
        self.closed = True


class _FakePipe:
    """模拟 Popen 的 stdout/stderr 管道, 按预设分块供给读取"""

    def __init__(self, chunks: list[bytes] | None = None) -> None:
        self._chunks = list(chunks or [])
        self.closed = False

    def read(self, size: int = -1) -> bytes:
        if self.closed or not self._chunks:
            return b''
        return self._chunks.pop(0)

    def fileno(self) -> int:
        return 12345

    def close(self) -> None:
        self.closed = True

    @property
    def has_data(self) -> bool:
        return bool(self._chunks)


class _FakePopen:
    """模拟 ffmpeg 子进程: stderr 分块读尽后进程退出, 可指定退出码"""

    def __init__(
            self,
            stderr_chunks: list[bytes],
            stdout_chunks: list[bytes] | None = None,
            exit_code: int = 0,
    ) -> None:
        self.stdin: Any = _FakeStdin()
        self.stdout: Any | None = _FakePipe(stdout_chunks) if stdout_chunks is not None else None
        self.stderr: Any = _FakePipe(stderr_chunks)
        self.returncode: int | None = None
        self._exit_code = exit_code
        self.killed = False

    def poll(self) -> int | None:
        if self.returncode is None and not self.stderr.has_data:
            self.returncode = self._exit_code
        return self.returncode

    def kill(self) -> None:
        self.killed = True
        if self.returncode is None:
            self.returncode = -9


def _make_ffmpeg_with_fake_process(
        monkeypatch: pytest.MonkeyPatch,
        stderr_chunks: list[bytes],
        stdout_chunks: list[bytes] | None = None,
        exit_code: int = 0,
        wait_stdin_close: bool = False,
) -> tuple[Any, _FakePopen]:
    """构造使用假子进程的 FFmpeg 实例, monkeypatch 掉 Popen 与 os.read, 不调用真实 ffmpeg"""
    from src.utils import ffmpy_patched

    fake_process = _FakePopen(stderr_chunks=stderr_chunks, stdout_chunks=stdout_chunks, exit_code=exit_code)
    monkeypatch.setattr(ffmpy_patched.subprocess, 'Popen', lambda *args, **kwargs: fake_process)

    def _fake_os_read(_fileno: int, _size: int) -> bytes:
        if wait_stdin_close:
            # 等待后台 writer 线程写入并关闭 stdin, 保证 input_data 断言的确定性
            deadline = time.monotonic() + 10
            while not fake_process.stdin.closed and time.monotonic() < deadline:
                time.sleep(0.001)
        return fake_process.stderr.read()

    monkeypatch.setattr(ffmpy_patched.os, 'read', _fake_os_read)

    ffmpeg = ffmpy_patched.FFmpeg(inputs={'input.mp4': None}, outputs={'output.mp4': None})
    return ffmpeg, fake_process


class TestCommandGeneration:
    """命令行生成: FFmpeg.__init__ 对各形态参数的拼装结果"""

    def test_default_executable(self):
        from src.utils.ffmpy_patched import FFmpeg

        ffmpeg = FFmpeg()
        assert ffmpeg._cmd == ['ffmpeg']
        assert ffmpeg.cmd == 'ffmpeg'
        assert ffmpeg.executable == 'ffmpeg'

    def test_repr(self):
        from src.utils.ffmpy_patched import FFmpeg

        assert repr(FFmpeg()) == "FFmpeg(cmd='ffmpeg')"

    @pytest.mark.parametrize(
        ('global_options', 'expected'),
        [
            (None, []),
            ('', []),
            ('-y', ['-y']),
            ('-hide_banner -loglevel warning', ['-hide_banner', '-loglevel', 'warning']),
            (['-y', '-hide_banner'], ['-y', '-hide_banner']),
            (('-y',), ['-y']),
            (['-y', ''], ['-y']),
            (['-progress pipe:1'], ['-progress', 'pipe:1']),
            ('-progress "pipe:1"', ['-progress', 'pipe:1']),
            ('-y -progress "pipe:1"', ['-y', '-progress', 'pipe:1']),
        ],
        ids=['none', 'empty-str', 'single-str', 'multi-str', 'list', 'tuple', 'list-with-empty', 'list-single',
             'quoted-str', 'mixed-str'],
    )
    def test_global_options(self, global_options: Any, expected: list[str]):
        from src.utils.ffmpy_patched import FFmpeg

        ffmpeg = FFmpeg(global_options=global_options)
        assert ffmpeg._cmd == ['ffmpeg', *expected]

    @pytest.mark.parametrize(
        ('inputs', 'expected'),
        [
            (None, []),
            ({}, []),
            ({'input.mp4': None}, ['-i', 'input.mp4']),
            ({'input.mp4': ''}, ['-i', 'input.mp4']),
            ({'input.avi': '-ss 00:00:10'}, ['-ss', '00:00:10', '-i', 'input.avi']),
            ({'input.avi': ['-ss', '00:00:10']}, ['-ss', '00:00:10', '-i', 'input.avi']),
            ({'input.avi': ('-ss', '00:00:10')}, ['-ss', '00:00:10', '-i', 'input.avi']),
            ({'a.mp4': None, 'b.mp4': '-r 30'}, ['-i', 'a.mp4', '-r', '30', '-i', 'b.mp4']),
            ({'': '-f lavfi'}, ['-f', 'lavfi']),
        ],
        ids=['none', 'empty-dict', 'none-opts', 'empty-opts', 'str-opts', 'list-opts', 'tuple-opts',
             'multiple-inputs', 'empty-arg-key'],
    )
    def test_inputs(self, inputs: Any, expected: list[str]):
        from src.utils.ffmpy_patched import FFmpeg

        ffmpeg = FFmpeg(inputs=inputs)
        assert ffmpeg._cmd == ['ffmpeg', *expected]

    @pytest.mark.parametrize(
        ('outputs', 'expected'),
        [
            (None, []),
            ({}, []),
            ({'output.mp4': None}, ['output.mp4']),
            ({'output.mp4': '-c:v h264'}, ['-c:v', 'h264', 'output.mp4']),
            ({'output.mp4': ['-c:v', 'h264']}, ['-c:v', 'h264', 'output.mp4']),
            ({'a.mp4': None, 'b.mkv': '-c:a aac'}, ['a.mp4', '-c:a', 'aac', 'b.mkv']),
            ({'out put.mp4': None}, ['out put.mp4']),
        ],
        ids=['none', 'empty-dict', 'none-opts', 'str-opts', 'list-opts', 'multiple-outputs', 'filename-with-space'],
    )
    def test_outputs(self, outputs: Any, expected: list[str]):
        from src.utils.ffmpy_patched import FFmpeg

        ffmpeg = FFmpeg(outputs=outputs)
        assert ffmpeg._cmd == ['ffmpeg', *expected]

    def test_full_command(self):
        from src.utils.ffmpy_patched import FFmpeg

        ffmpeg = FFmpeg(
            executable='/usr/bin/ffmpeg',
            global_options='-y -hide_banner',
            inputs={'my input.mp4': '-ss 10'},
            outputs={'my output.mp4': '-c:v h264'},
        )
        assert ffmpeg._cmd == [
            '/usr/bin/ffmpeg', '-y', '-hide_banner',
            '-ss', '10', '-i', 'my input.mp4',
            '-c:v', 'h264', 'my output.mp4',
        ]
        # list2cmdline 按固定规则为含空格参数加引号
        assert ffmpeg.cmd == '/usr/bin/ffmpeg -y -hide_banner -ss 10 -i "my input.mp4" -c:v h264 "my output.mp4"'

    def test_windows_path_in_options_snapshot(self):
        # 已知限制(审计 M-4): 选项字符串经 POSIX 模式 shlex.split 会吞掉未转义的反斜杠, 此处锁定现状
        from src.utils.ffmpy_patched import FFmpeg

        ffmpeg = FFmpeg(inputs={'input.mp4': '-metadata title=C:\\data\\name'})
        assert ffmpeg._cmd == ['ffmpeg', '-metadata', 'title=C:dataname', '-i', 'input.mp4']


class TestFFStateConsume:
    """FFState.consume 对进度行的解析与边界条件"""

    def test_full_progress_line(self):
        from src.utils.ffmpy_patched import FFState

        state = FFState()
        assert state.consume(_PROGRESS_LINE.encode()) is True
        assert state.frame == 100
        assert state.fps == 30.0
        assert state.size == 128000
        assert state.time == 10.0

    def test_full_progress_line_str_input(self):
        # consume 同时接受已解码的 str (wait 内部即传 str)
        from src.utils.ffmpy_patched import FFState

        state = FFState()
        assert state.consume(_PROGRESS_LINE) is True
        assert state.frame == 100
        assert state.time == 10.0

    def test_chunk_boundary_split(self):
        # 分块读取把进度行切断: 前半块不应误更新被切断的 time 字段
        from src.utils.ffmpy_patched import FFState

        split_at = _PROGRESS_LINE.index('time=')
        state = FFState()
        assert state.consume(_PROGRESS_LINE[:split_at].encode()) is True
        assert state.frame == 100
        assert state.fps == 30.0
        assert state.size == 128000
        assert state.time is None

        assert state.consume(_PROGRESS_LINE[split_at:].encode()) is True
        assert state.time == 10.0

    def test_lsize_fallback(self):
        # 结束总结行使用 Lsize= 代替 size=
        from src.utils.ffmpy_patched import FFState

        state = FFState()
        assert state.consume(b'Lsize= 256kB') is True
        assert state.size == 256000

    def test_size_preferred_over_lsize(self):
        from src.utils.ffmpy_patched import FFState

        state = FFState()
        state.consume(b'size= 128kB Lsize= 256kB')
        assert state.size == 128000

    def test_irrelevant_content(self):
        from src.utils.ffmpy_patched import FFState

        state = FFState()
        assert state.consume(b'ffmpeg version 6.1 Copyright (c) 2000-2023 the FFmpeg developers') is False
        assert state.frame is None
        assert state.fps is None
        assert state.size is None
        assert state.time is None

    def test_empty_chunk(self):
        from src.utils.ffmpy_patched import FFState

        assert FFState().consume(b'') is False

    def test_non_utf8_bytes_tolerated(self):
        # 非 UTF-8 字节被 replace 容错, 不抛 UnicodeDecodeError (审计 H-3)
        from src.utils.ffmpy_patched import FFState

        state = FFState()
        assert state.consume(b'\xd6\xd0\xce\xc4 frame= 10 ') is True
        assert state.frame == 10

    def test_na_values_ignored(self):
        # frame=N/A 等非法数值不应抛异常, 仅忽略 (审计 M-1)
        from src.utils.ffmpy_patched import FFState

        state = FFState()
        assert state.consume(b'frame=N/A fps=N/A size=N/A time=N/A') is False
        assert state.frame is None
        assert state.fps is None
        assert state.size is None
        assert state.time is None

    def test_repeated_consume(self):
        # 重复消费同一值: 状态被覆盖, 返回值仍为 True
        from src.utils.ffmpy_patched import FFState

        state = FFState()
        assert state.consume(b'frame= 5') is True
        assert state.consume(b'frame= 5') is True
        assert state.frame == 5

    def test_state_str_and_repr(self):
        from src.utils.ffmpy_patched import FFState

        state = FFState()
        state.consume(b'frame= 1 fps= 2.0 size= 3kB time=00:00:04.00')
        assert repr(state) == 'FFState(frame=1, fps=2.0, size=3000, time=4.0)'
        assert str(state) == 'frame: 1, fps: 2.0, size: 3000, time: 4.0'


class TestFFStateUpdateUnits:
    """FFState 各 update_* 方法的取值边界"""

    @pytest.mark.parametrize(
        ('raw_frame', 'expected'),
        [('0', 0), ('100', 100), ('999999', 999999)],
        ids=['zero', 'normal', 'large'],
    )
    def test_update_frame_valid(self, raw_frame: str, expected: int):
        from src.utils.ffmpy_patched import FFState

        state = FFState()
        assert state.update_frame(raw_frame) is True
        assert state.frame == expected

    def test_update_frame_none(self):
        from src.utils.ffmpy_patched import FFState

        state = FFState()
        assert state.update_frame(None) is False
        assert state.frame is None

    @pytest.mark.parametrize('raw_frame', ['N/A', 'abc', ''], ids=['na', 'garbage', 'empty'])
    def test_update_frame_invalid(self, raw_frame: str):
        from src.utils.ffmpy_patched import FFState

        state = FFState()
        assert state.update_frame(raw_frame) is False
        assert state.frame is None

    @pytest.mark.parametrize(
        ('fps_raw', 'expected'),
        [('0.0', 0.0), ('29.97', 29.97), ('100', 100.0)],
        ids=['zero', 'decimal', 'integer-str'],
    )
    def test_update_fps_valid(self, fps_raw: str, expected: float):
        from src.utils.ffmpy_patched import FFState

        state = FFState()
        assert state.update_fps(fps_raw) is True
        assert state.fps == expected

    def test_update_fps_none(self):
        from src.utils.ffmpy_patched import FFState

        state = FFState()
        assert state.update_fps(None) is False
        assert state.fps is None

    @pytest.mark.parametrize('fps_raw', ['N/A', 'abc', ''], ids=['na', 'garbage', 'empty'])
    def test_update_fps_invalid(self, fps_raw: str):
        from src.utils.ffmpy_patched import FFState

        state = FFState()
        assert state.update_fps(fps_raw) is False
        assert state.fps is None

    @pytest.mark.parametrize(
        ('raw_size', 'expected'),
        [('0kB', 0), ('128kB', 128000), ('1024kB', 1024000)],
        ids=['zero', 'normal', 'large'],
    )
    def test_update_size_valid(self, raw_size: str, expected: int):
        from src.utils.ffmpy_patched import FFState

        state = FFState()
        assert state.update_size(raw_size) is True
        assert state.size == expected

    @pytest.mark.parametrize(
        'raw_size',
        ['1.5kB', '128KB', 'N/A', '', 'kB'],
        ids=['decimal', 'capital-b', 'na', 'empty', 'no-digits'],
    )
    def test_update_size_no_match(self, raw_size: str):
        from src.utils.ffmpy_patched import FFState

        state = FFState()
        assert state.update_size(raw_size) is False
        assert state.size is None

    @pytest.mark.parametrize(
        ('raw_time', 'expected'),
        [('00:00:00.00', 0.0), ('00:00:10.5', 10.5), ('01:02:03.04', 3723.04), ('100:00:00.00', 360000.0)],
        ids=['zero', 'one-segment', 'hms', 'multi-digit-hours'],
    )
    def test_update_time_valid(self, raw_time: str, expected: float):
        from src.utils.ffmpy_patched import FFState

        state = FFState()
        assert state.update_time(raw_time) is True
        assert state.time == pytest.approx(expected)

    @pytest.mark.parametrize(
        'raw_time',
        ['00:00:01', '10:00', 'N/A', ''],
        ids=['no-fraction-seconds', 'missing-segment', 'na', 'empty'],
    )
    def test_update_time_no_match(self, raw_time: str):
        from src.utils.ffmpy_patched import FFState

        state = FFState()
        assert state.update_time(raw_time) is False
        assert state.time is None


class TestExceptions:
    """异常类与 FFTool.start 的可执行文件查找"""

    @pytest.mark.parametrize(
        ('stderr', 'expected_fragment'),
        [('some error', 'some error'), (b'bytes error', 'bytes error'), ('', ''), (b'', '')],
        ids=['str', 'bytes', 'empty-str', 'empty-bytes'],
    )
    def test_ffruntime_error(self, stderr: str | bytes, expected_fragment: str):
        from src.utils.ffmpy_patched import FFRuntimeError

        error = FFRuntimeError('ffmpeg -y', 1, stderr)
        assert error.cmd == 'ffmpeg -y'
        assert error.exit_code == 1
        assert error.stderr == stderr
        assert 'exited with status 1' in str(error)
        assert 'ffmpeg -y' in str(error)
        assert expected_fragment in str(error)
        assert repr(error).startswith("FFRuntimeError(cmd='ffmpeg -y'")

    def test_start_executable_not_found(self, monkeypatch: pytest.MonkeyPatch):
        from src.utils import ffmpy_patched

        def _raise_enoent(*args: Any, **kwargs: Any) -> None:
            raise OSError(errno.ENOENT, 'No such file or directory')

        monkeypatch.setattr(ffmpy_patched.subprocess, 'Popen', _raise_enoent)
        with pytest.raises(ffmpy_patched.FFExecutableNotFoundError, match="Executable 'ffmpeg' not found"):
            ffmpy_patched.FFmpeg().start()

    def test_start_other_oserror_reraised(self, monkeypatch: pytest.MonkeyPatch):
        from src.utils import ffmpy_patched

        def _raise_eacces(*args: Any, **kwargs: Any) -> None:
            raise OSError(errno.EACCES, 'Permission denied')

        monkeypatch.setattr(ffmpy_patched.subprocess, 'Popen', _raise_eacces)
        with pytest.raises(OSError, match='Permission denied') as excinfo:
            ffmpy_patched.FFmpeg().start()
        assert not isinstance(excinfo.value, ffmpy_patched.FFExecutableNotFoundError)


class TestRunMocked:
    """run/wait 全程使用伪造子进程, 不调用真实 ffmpeg"""

    def test_wait_without_start(self):
        from src.utils.ffmpy_patched import FFmpeg

        with pytest.raises(RuntimeError, match='Popen'):
            FFmpeg().wait()

    def test_run_success_with_pipes(self, monkeypatch: pytest.MonkeyPatch):
        # input_data 写入 stdin + stdout 管道被排空并返回 (审计 H-1/H-2 修复后行为)
        ffmpeg, fake_process = _make_ffmpeg_with_fake_process(
            monkeypatch,
            stderr_chunks=[_PROGRESS_LINE.encode(), b'some=1 '],
            stdout_chunks=[b'fake stdout output'],
            exit_code=0,
            wait_stdin_close=True,
        )

        progresses: list[Any] = []
        stdout, stderr = ffmpeg.run(
            input_data=b'fake input data',
            stdout=subprocess.PIPE,
            on_progress=progresses.append,
        )

        assert fake_process.stdin.written == [b'fake input data']
        assert fake_process.stdin.closed
        assert stdout == b'fake stdout output'
        assert fake_process.stdout.closed
        assert 'frame= 100' in stderr
        assert fake_process.killed is False

        # 仅第一块产生进度更新, 'some=1 ' 不触发回调
        assert len(progresses) == 1
        assert progresses[0].frame == 100
        assert progresses[0].fps == 30.0
        assert progresses[0].size == 128000
        assert progresses[0].time == 10.0

    def test_run_success_no_redirection(self, monkeypatch: pytest.MonkeyPatch):
        ffmpeg, fake_process = _make_ffmpeg_with_fake_process(
            monkeypatch,
            stderr_chunks=[_PROGRESS_LINE.encode()],
            exit_code=0,
        )

        stdout, stderr = ffmpeg.run()

        assert stdout is None
        assert 'frame= 100' in stderr
        assert fake_process.stdin.closed
        assert fake_process.stderr.closed
        assert fake_process.killed is False

    def test_run_nonzero_exit(self, monkeypatch: pytest.MonkeyPatch):
        from src.utils.ffmpy_patched import FFRuntimeError

        ffmpeg, fake_process = _make_ffmpeg_with_fake_process(
            monkeypatch,
            stderr_chunks=[b'Input #0, matroska, from input.mp4\n', b'Error: invalid data found\n'],
            exit_code=3,
        )

        with pytest.raises(FFRuntimeError) as excinfo:
            ffmpeg.run()

        assert excinfo.value.exit_code == 3
        assert excinfo.value.cmd == ffmpeg.cmd
        assert 'invalid data' in excinfo.value.stderr
        assert fake_process.stderr.closed

    def test_run_progress_callback_exception_kills_process(self, monkeypatch: pytest.MonkeyPatch):
        # 进度回调抛异常时应终止进程并关闭管道 (审计 M-2 修复后行为)
        ffmpeg, fake_process = _make_ffmpeg_with_fake_process(
            monkeypatch,
            stderr_chunks=[_PROGRESS_LINE.encode()],
            exit_code=0,
        )

        def _boom(_state: Any) -> None:
            raise RuntimeError('callback boom')

        with pytest.raises(RuntimeError, match='callback boom'):
            ffmpeg.run(on_progress=_boom)

        assert fake_process.killed is True
        assert fake_process.stderr.closed
        assert fake_process.stdin.closed

    def test_run_non_utf8_stderr_single_chunk(self, monkeypatch: pytest.MonkeyPatch):
        # 非 UTF-8 的 stderr 块被 replace 容错, 不抛 UnicodeDecodeError (审计 H-3)
        ffmpeg, _fake_process = _make_ffmpeg_with_fake_process(
            monkeypatch,
            stderr_chunks=[b'\xd6\xd0\xce\xc4 frame= 7 '],
            exit_code=0,
        )

        progresses: list[Any] = []
        _stdout, stderr = ffmpeg.run(on_progress=progresses.append)

        assert len(progresses) == 1
        assert progresses[0].frame == 7
        assert 'frame= 7' in stderr

    def test_run_multibyte_char_split_across_chunks(self, monkeypatch: pytest.MonkeyPatch):
        # 多字节 UTF-8 字符被切在读取分块边界时由增量解码器拼回, 不产生半截乱码 (审计 H-3)
        ffmpeg, _fake_process = _make_ffmpeg_with_fake_process(
            monkeypatch,
            stderr_chunks=[b'\xe4\xb8', b'\xad frame= 3 '],
            exit_code=0,
        )

        progresses: list[Any] = []
        _stdout, stderr = ffmpeg.run(on_progress=progresses.append)

        assert len(progresses) == 1
        assert progresses[0].frame == 3
        assert '中 frame= 3 ' in stderr

    async def test_async_run(self, monkeypatch: pytest.MonkeyPatch):
        ffmpeg, _fake_process = _make_ffmpeg_with_fake_process(
            monkeypatch,
            stderr_chunks=[_PROGRESS_LINE.encode()],
            exit_code=0,
        )

        stdout, stderr = await ffmpeg.async_run()

        assert stdout is None
        assert 'frame= 100' in stderr
