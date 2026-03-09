import asyncio
import subprocess
import threading
import time
from enum import Enum
from dataclasses import dataclass
from collections import deque
from typing import Callable, TextIO

IOStreamCallback = Callable[[str], None]
IOStreamBuffer = deque[str]

class IOStreamReaderStatus(str, Enum):
    SUCCESS = "success"
    TIMEOUT = "timeout"
    CANCELED = "canceled"
    ERROR = "error"

@dataclass
class IOStreamReaderResult:
    returncode: int
    status: IOStreamReaderStatus
    error: Exception | None
    stdout_buf: IOStreamBuffer
    stderr_buf: IOStreamBuffer

    @property
    def stdout(self) -> str:
        """Get the full text of stdout"""
        return "\n".join(self.stdout_buf)

    @property
    def stderr(self) -> str:
        """Get the full text of stderr"""
        return "\n".join(self.stderr_buf)

class IOStreamReader:
    def __init__(self,
                 proc: asyncio.subprocess.Process,
                 max_lines: int,
                 on_stdout: IOStreamCallback | None = None,
                 on_stderr: IOStreamCallback | None = None,
                 ):
        self._proc = proc
        self._max_lines = max_lines
        self._on_stdout = on_stdout
        self._on_stderr = on_stderr

    @staticmethod
    async def _consumer(stream: asyncio.StreamReader, callback: IOStreamCallback | None, buf: IOStreamBuffer):
        while not stream.at_eof():
            line = await stream.readline()
            if not line: break
            text = line.decode("utf-8", errors="replace")
            buf.append(text)
            if callback: callback(text)

    async def read(self, timeout_sec: int | None = None) -> IOStreamReaderResult:
        stdout_buf = IOStreamBuffer(maxlen=self._max_lines)
        stderr_buf = IOStreamBuffer(maxlen=self._max_lines)

        assert self._proc.stdout is not None
        assert self._proc.stderr is not None
        consumer_task = [
            asyncio.create_task(IOStreamReader._consumer(self._proc.stdout, self._on_stdout, stdout_buf)),
            asyncio.create_task(IOStreamReader._consumer(self._proc.stderr, self._on_stderr, stderr_buf))
        ]

        status = IOStreamReaderStatus.SUCCESS
        error: Exception | None = None
        try:
            if timeout_sec is not None:
                returncode = await asyncio.wait_for(self._proc.wait(), timeout=timeout_sec)
            else:
                returncode = await self._proc.wait()
        except asyncio.TimeoutError:
            self._proc.kill()
            returncode = await self._proc.wait()
            status = IOStreamReaderStatus.TIMEOUT
        except asyncio.CancelledError:
            self._proc.kill()
            returncode = await self._proc.wait()
            status = IOStreamReaderStatus.CANCELED
        except Exception as exc:
            self._proc.kill()
            returncode = await self._proc.wait()
            status = IOStreamReaderStatus.ERROR
            error = exc
        finally:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*consumer_task, return_exceptions=True),
                    timeout=2)
            except asyncio.TimeoutError:
                for task in consumer_task: task.cancel()
                await asyncio.gather(*consumer_task, return_exceptions=True)

        return IOStreamReaderResult(returncode, status, error, stdout_buf, stderr_buf)
