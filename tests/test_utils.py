from __future__ import annotations

import asyncio

import pytest
from werkzeug.datastructures import Headers

from quart.utils import cancel_tasks
from quart.utils import decode_headers
from quart.utils import encode_headers
from quart.utils import raise_task_exceptions


def test_encode_headers() -> None:
    assert encode_headers(Headers({"Foo": "Bar"})) == [(b"foo", b"Bar")]


def test_decode_headers() -> None:
    assert decode_headers([(b"foo", b"Bar")]) == Headers({"Foo": "Bar"})


async def test_cancel_tasks_cancels_and_waits() -> None:
    started = asyncio.Event()

    async def runner() -> None:
        started.set()
        await asyncio.sleep(10)

    task = asyncio.ensure_future(runner())
    await started.wait()
    await cancel_tasks({task})
    assert task.cancelled()
    # A clean cancellation must not raise
    raise_task_exceptions({task})


async def test_cancel_tasks_preserves_exceptions_raised_whilst_cancelling() -> None:
    started = asyncio.Event()

    async def runner() -> None:
        try:
            started.set()
            await asyncio.sleep(10)
        finally:
            raise ValueError("cleanup error")

    task = asyncio.ensure_future(runner())
    await started.wait()
    await cancel_tasks({task})
    assert not task.cancelled()
    with pytest.raises(ValueError, match="cleanup error"):
        raise_task_exceptions({task})


async def test_raise_task_exceptions_chains_multiple_exceptions() -> None:
    async def raise_error(error: Exception) -> None:
        raise error

    tasks = {
        asyncio.ensure_future(raise_error(ValueError("first"))),
        asyncio.ensure_future(raise_error(KeyError("second"))),
    }
    await asyncio.gather(*tasks, return_exceptions=True)
    with pytest.raises(Exception) as exc_info:
        raise_task_exceptions(tasks)
    # The other exception must be chained, not silently dropped
    assert exc_info.value.__context__ is not None
