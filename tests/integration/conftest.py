"""Pytest configuration for integration tests."""
from vcr.stubs import aiohttp_stubs

# vcrpy 8.x ships MockClientResponse.release as a sync no-op returning None,
# but real aiohttp.ClientResponse.release() returns an awaitable, and
# dataclass_rest's aiohttp adapter does `await response.release()`. Patch
# the stub to an async no-op so cassette playback works for async clients.
_orig_release = aiohttp_stubs.MockClientResponse.release


async def _async_release(self) -> None:
    _orig_release(self)


aiohttp_stubs.MockClientResponse.release = _async_release
