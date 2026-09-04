import pytest

from src.lzt.client import LZTClient
from src.utils.rate_limiter import AsyncRateLimiter


class FakeResponse:
    def __init__(
        self, status: int, body: dict | None = None, headers: dict | None = None
    ) -> None:
        self.status = status
        self._body = body or {}
        self.headers = headers or {}

    async def json(self):
        return self._body

    async def text(self):
        return str(self._body)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


class FakeSession:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self._responses = list(responses)
        self.closed = False
        self.request_calls: list[tuple] = []

    def request(self, method, url, params=None, json=None, timeout=None):
        self.request_calls.append((method, url, params, json))
        resp = self._responses.pop(0) if self._responses else FakeResponse(500)
        return resp

    async def close(self):
        self.closed = True


@pytest.mark.asyncio
async def test_get_my_balance_parses_user():
    fake = FakeSession([FakeResponse(200, {"user": {"balance": "100", "hold": "5"}})])
    client = LZTClient(
        api_token="t", session=fake, rate_limiter=AsyncRateLimiter(100, 100)
    )
    result = await client.get_my_balance()
    assert result == {"balance": 100.0, "hold": 5.0}


@pytest.mark.asyncio
async def test_request_retries_on_429():
    fake = FakeSession(
        [
            FakeResponse(429, headers={"Retry-After": "0"}),
            FakeResponse(200, {"user": {"balance": "50", "hold": "0"}}),
        ]
    )
    client = LZTClient(
        api_token="t", session=fake, rate_limiter=AsyncRateLimiter(100, 100)
    )
    result = await client.get_my_balance()
    assert result == {"balance": 50.0, "hold": 0.0}
    assert len(fake.request_calls) == 2


@pytest.mark.asyncio
async def test_search_items_maps_categories():
    fake = FakeSession(
        [
            FakeResponse(
                200,
                {
                    "items": [
                        {
                            "item_id": 42,
                            "title": "Minecraft",
                            "price": "10",
                            "currency": "RUB",
                            "item_state": "active",
                            "published_date": 0,
                            "seller": {"username": "u", "trust": 10},
                        }
                    ]
                },
            ),
        ]
    )
    client = LZTClient(
        api_token="t", session=fake, rate_limiter=AsyncRateLimiter(100, 100)
    )
    items = await client.search_items("brawlstars")
    assert len(items) == 1
    assert items[0].item_id == 42
    assert items[0].item_url.startswith("https://lzt.market/")
    assert items[0].seller_trust == 10
    url = fake.request_calls[0][1]
    assert url.endswith("/supercell")


@pytest.mark.asyncio
async def test_fast_buy_failure_message():
    fake = FakeSession(
        [FakeResponse(200, {"status": "error", "error": "not enough money"})]
    )
    client = LZTClient(
        api_token="t", session=fake, rate_limiter=AsyncRateLimiter(100, 100)
    )
    result = await client.fast_buy(1, 10.0)
    assert not result.success
    assert "not enough money" in result.message
