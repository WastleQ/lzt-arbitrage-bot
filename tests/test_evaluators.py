from evaluators.brawlstars import BrawlStarsEvaluator
from evaluators.minecraft import MinecraftEvaluator
from evaluators.valorant import ValorantEvaluator


def test_minecraft_evaluator():
    evaluator = MinecraftEvaluator()
    raw = {"title": "Minecraft Java Full Access Hypixel MVP+", "description": "150 звёзд bedwars", "price": 150.0}
    res = evaluator.evaluate(raw)
    assert res is not None
    assert res.estimated_price > 150.0
    assert "MVP+" in res.details.get("rank")
    assert res.details.get("bedwars_stars") == 150


def test_minecraft_banned_account():
    evaluator = MinecraftEvaluator()
    raw = {"title": "Minecraft Java (бан на hypixel)", "price": 50.0}
    res = evaluator.evaluate(raw)
    assert res is None


def test_brawlstars_evaluator():
    evaluator = BrawlStarsEvaluator()
    raw = {"title": "Brawl Stars 35k кубков с Star Shelly", "price": 100.0}
    res = evaluator.evaluate(raw)
    assert res is not None
    assert res.estimated_price > 100.0
    assert res.details.get("trophies") == 35000
    assert res.details.get("rare_skin") == "Star Shelly"


def test_valorant_evaluator():
    evaluator = ValorantEvaluator()
    raw = {"title": "Valorant EU Radiant Account", "description": "2 ножа и Kuronami", "price": 300.0}
    res = evaluator.evaluate(raw)
    assert res is not None
    assert res.estimated_price > 300.0
    assert res.details.get("region") == "EU"
    assert res.details.get("rank") == "Radiant"
