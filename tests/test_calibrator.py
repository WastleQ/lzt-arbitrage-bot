import pytest

from src.lzt.client import LZTClient
from src.utils.calibrator import MarketCalibrator
from src.utils.rate_limiter import AsyncRateLimiter
from tests.test_lzt_client import FakeResponse, FakeSession


@pytest.mark.asyncio
async def test_market_calibrator(tmp_path):
    fake = FakeSession(
        [
            FakeResponse(
                200,
                {
                    "items": [
                        {"item_id": 1, "title": "Minecraft MVP+", "price": 500},
                        {"item_id": 2, "title": "Minecraft Default", "price": 200},
                    ]
                },
            ),
            FakeResponse(200, {"items": []}),
            FakeResponse(200, {"items": []}),
        ]
    )
    client = LZTClient(api_token="t", session=fake, rate_limiter=AsyncRateLimiter(100, 100))
    calibrator = MarketCalibrator(client)

    yaml_file = tmp_path / "categories.yaml"
    yaml_file.write_text("categories:\n  minecraft:\n    base_price: 250.0\n    weights: {}\n", encoding="utf-8")

    res = await calibrator.calibrate_and_update_yaml(str(yaml_file))
    assert res["status"] == "success"
    assert "minecraft" in res["report"]
