from src.evaluators.brawlstars import BrawlStarsEvaluator
from src.evaluators.minecraft import MinecraftEvaluator
from src.evaluators.valorant import ValorantEvaluator


def test_minecraft_evaluator():
    evaluator = MinecraftEvaluator()
    raw = {"title": "Minecraft Java Full Access Hypixel MVP+", "price": 150.0}
    res = evaluator.evaluate(raw)
    assert res is not None
    assert res.estimated_price > 150.0
    assert "MVP+" in res.details.get("rank")


def test_brawlstars_evaluator():
    evaluator = BrawlStarsEvaluator()
    raw = {"title": "Brawl Stars 25к кубков с гиперзарядом", "price": 100.0}
    res = evaluator.evaluate(raw)
    assert res is not None
    assert res.estimated_price > 100.0
    assert res.details.get("hypercharge") is True


def test_valorant_evaluator():
    evaluator = ValorantEvaluator()
    raw = {"title": "Valorant EU Vandal Prime + Нож", "price": 300.0}
    res = evaluator.evaluate(raw)
    assert res is not None
    assert res.estimated_price > 300.0
    assert res.details.get("has_knife") is True
