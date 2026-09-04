from src.evaluators.brawlstars import BrawlStarsEvaluator
from src.evaluators.minecraft import MinecraftEvaluator
from src.evaluators.valorant import ValorantEvaluator


def test_minecraft_evaluator():
    evaluator = MinecraftEvaluator()
    raw = {
        "title": "Minecraft Java Full Access Hypixel MVP+",
        "description": "150 звёзд bedwars",
        "price": 150.0,
    }
    res = evaluator.evaluate(raw)
    assert res is not None
    assert res.estimated_price > 150.0
    assert "MVP+" in res.details.get("rank")
    assert res.details.get("bedwars_stars") == 150


def test_minecraft_banned_account():
    evaluator = MinecraftEvaluator()
    raw = {"title": "Minecraft Java (бан на hypixel)", "price": 50.0}
    assert evaluator.evaluate(raw) is None


def test_minecraft_minecon_cape_huge_bonus():
    evaluator = MinecraftEvaluator()
    raw = {"title": "Minecraft Java Minecon cape 200 звёзд", "price": 500.0}
    res = evaluator.evaluate(raw)
    assert res is not None
    assert "Minecon" in res.details.get("capes", [])
    assert res.estimated_price > 2000.0


def test_minecraft_full_access_multiplier():
    evaluator = MinecraftEvaluator()
    without = evaluator.evaluate({"title": "Minecraft Java VIP", "price": 100.0})
    with_fa = evaluator.evaluate(
        {"title": "Minecraft Java VIP full access", "price": 100.0}
    )
    assert without and with_fa
    assert with_fa.estimated_price > without.estimated_price


def test_brawlstars_evaluator():
    evaluator = BrawlStarsEvaluator()
    raw = {"title": "Brawl Stars 35k кубков с Star Shelly", "price": 100.0}
    res = evaluator.evaluate(raw)
    assert res is not None
    assert res.estimated_price > 100.0
    assert res.details.get("trophies") == 35000
    assert res.details.get("rare_skin") == "Star Shelly"


def test_brawlstars_hypercharge_count():
    evaluator = BrawlStarsEvaluator()
    raw = {"title": "Brawl Stars 20 гипер 30к кубков", "price": 200.0}
    res = evaluator.evaluate(raw)
    assert res is not None
    assert res.details.get("hypercharges_count") == 20


def test_valorant_evaluator():
    evaluator = ValorantEvaluator()
    raw = {
        "title": "Valorant EU Radiant Account",
        "description": "2 ножа и Kuronami",
        "price": 300.0,
    }
    res = evaluator.evaluate(raw)
    assert res is not None
    assert res.estimated_price > 300.0
    assert res.details.get("region") == "EU"
    assert res.details.get("rank") == "Radiant"
    assert res.details.get("knives_detected", 0) >= 2


def test_valorant_tr_region_penalty():
    evaluator = ValorantEvaluator()
    eu = evaluator.evaluate({"title": "Valorant EU Gold", "price": 200.0})
    tr = evaluator.evaluate({"title": "Valorant TR Gold", "price": 200.0})
    assert eu and tr
    assert eu.estimated_price > tr.estimated_price
