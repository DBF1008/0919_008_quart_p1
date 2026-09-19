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


async def test_cancel_tasks_ignores_expected_cancellation() -> None:
    async def sleeper() -> None:
        await asyncio.Event().wait()

    task = asyncio.ensure_future(sleeper())
    await asyncio.sleep(0)
    await cancel_tasks({task})
    assert task.cancelled()


async def test_cancel_tasks_raises_exception_raised_during_cancellation() -> None:
    # A genuine exception raised by a task whilst it is being
    # cancelled must not be silently dropped.
    async def cleanup_error() -> None:
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            raise ValueError("cleanup failed") from None

    task = asyncio.ensure_future(cleanup_error())
    await asyncio.sleep(0)
    with pytest.raises(ValueError, match="cleanup failed"):
        await cancel_tasks({task})


async def test_cancel_tasks_raises_existing_exception() -> None:
    async def error() -> None:
        raise ValueError("task failed")

    task = asyncio.ensure_future(error())
    await asyncio.sleep(0)
    with pytest.raises(ValueError, match="task failed"):
        await cancel_tasks({task})


async def test_raise_task_exceptions_skips_cancelled() -> None:
    task = asyncio.ensure_future(asyncio.Event().wait())
    await asyncio.sleep(0)
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)
    raise_task_exceptions({task})  # Should not raise


async def test_raise_task_exceptions_raises_exception() -> None:
    async def error() -> None:
        raise ValueError("task failed")

    task = asyncio.ensure_future(error())
    await asyncio.gather(task, return_exceptions=True)
    with pytest.raises(ValueError, match="task failed"):
        raise_task_exceptions({task})


async def test_raise_task_exceptions_retrieves_all_exceptions() -> None:
    # With multiple failed tasks every exception must be retrieved
    # (none silently dropped) with the first raised.
    async def raise_error(error: Exception) -> None:
        raise error

    task1 = asyncio.ensure_future(raise_error(ValueError("one")))
    task2 = asyncio.ensure_future(raise_error(KeyError("two")))
    await asyncio.gather(task1, task2, return_exceptions=True)
    with pytest.raises((ValueError, KeyError)):
        raise_task_exceptions({task1, task2})
