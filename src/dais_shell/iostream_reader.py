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


class IOStreamReaderSync:
    def __init__(self,
                 proc: subprocess.Popen,
                 on_stdout: IOStreamCallback | None = None,
                 on_stderr: IOStreamCallback | None = None,
                 max_lines: int = 10000):
        self._proc = proc
        self._max_lines = max_lines
        self._on_stdout = on_stdout
        self._on_stderr = on_stderr
        self._cancel_event = threading.Event()

    def cancel(self):
        self._cancel_event.set()

    @staticmethod
    def _consumer(pipe: TextIO, callback: IOStreamCallback | None, buf: IOStreamBuffer):
        for line in iter(pipe.readline, ""):
            buf.append(line)
            if callback: callback(line)

    def read(self, timeout_sec: int | None = None) -> IOStreamReaderResult:
        if (returncode := self._proc.poll()) is not None:
            return IOStreamReaderResult(
                returncode,
                status=IOStreamReaderStatus.SUCCESS,
                error=None,
                stdout_buf=IOStreamBuffer(),
                stderr_buf=IOStreamBuffer())

        stdout_buf = IOStreamBuffer(maxlen=self._max_lines)
        stderr_buf = IOStreamBuffer(maxlen=self._max_lines)

        stdout_consumer = threading.Thread(
            target=IOStreamReaderSync._consumer,
            args=(self._proc.stdout, self._on_stdout, stdout_buf))
        stderr_consumer = threading.Thread(
            target=IOStreamReaderSync._consumer,
            args=(self._proc.stderr, self._on_stderr, stderr_buf))

        stdout_consumer.start()
        stderr_consumer.start()

        start_time = time.monotonic()
        status = IOStreamReaderStatus.SUCCESS
        error: Exception | None = None
        try:
            while self._proc.poll() is None:
                if self._cancel_event.is_set():
                    self._proc.kill()
                    status = IOStreamReaderStatus.CANCELED
                    break

                if (timeout_sec is not None and
                   (time.monotonic() - start_time) > timeout_sec):
                    self._proc.kill()
                    status = IOStreamReaderStatus.TIMEOUT
                    break
                time.sleep(0.1)
        except Exception as exc:
            self._proc.kill()
            status = IOStreamReaderStatus.ERROR
            error = exc

        stdout_consumer.join(timeout=3)
        stderr_consumer.join(timeout=3)

        returncode = self._proc.returncode
        if returncode is None:
            returncode = self._proc.wait()
        return IOStreamReaderResult(returncode, status, error, stdout_buf, stderr_buf)

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
