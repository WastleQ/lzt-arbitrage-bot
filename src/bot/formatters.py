from html import escape
from typing import Any

from src.lzt.client import LZTClient
from src.lzt.schemas import BuyResult, MarketItem

_lzt_client: LZTClient | None = None


def set_lzt_client(client: LZTClient) -> None:
    global _lzt_client
    _lzt_client = client


def _client() -> LZTClient:
    if _lzt_client is None:
        raise RuntimeError("LZT client is not set")
    return _lzt_client


def _humanize_details(category: str, details: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    if not details:
        return lines

    if category == "minecraft":
        if rank := details.get("rank"):
            lines.append(f"🏅 Ранг Hypixel: <b>{escape(str(rank))}</b>")
        if stars := details.get("bedwars_stars"):
            lines.append(f"⭐ BedWars: <b>{stars}</b> ★")
        if capes := details.get("capes"):
            lines.append(f"🎽 Плащи: {escape(', '.join(capes))}")
        if "tenure_days" in details:
            lines.append(f"📅 Отлега: <b>{details['tenure_days']} дн.</b>")
        if details.get("full_access"):
            lines.append("🔑 <b>Full Access / Родная почта</b>")

    elif category == "brawlstars":
        if trophies := details.get("trophies"):
            lines.append(f"🏆 Кубки: <b>{trophies:,}</b>".replace(",", " "))
        if hc := details.get("hypercharges_count"):
            lines.append(f"⚡ Гиперзаряды: <b>{hc}</b>")
        elif details.get("hypercharge"):
            lines.append("⚡ Гиперзаряд: да")
        if rare := details.get("rare_skin"):
            lines.append(f"🌟 Редкий скин: <b>{escape(str(rare))}</b>")
        if details.get("mecha_skins"):
            lines.append("🤖 Скины Mecha")
        if details.get("legendary_brawlers"):
            lines.append("🏅 Легендарные бравлеры")

    elif category == "valorant":
        if region := details.get("region"):
            lines.append(f"🌍 Регион: <b>{escape(str(region))}</b>")
        if rank := details.get("rank"):
            lines.append(f"🎖 Ранг: <b>{escape(str(rank))}</b>")
        if knives := details.get("knives_detected"):
            lines.append(f"🔪 Ножей: <b>{knives}</b>")
        if skins := details.get("premium_skins_count"):
            lines.append(f"💎 Премиум скинов: <b>{skins}</b>")
        if total := details.get("total_skins_mentioned"):
            lines.append(f"🎨 Всего скинов упомянуто: <b>{total}</b>")

    return lines


def format_deal_card(result: dict[str, Any]) -> str:
    item: MarketItem = result["item"]
    details: dict[str, Any] = result["details"]
    warnings: list[str] = result.get("warnings") or []

    header = f"🔥 <b>Найдена сделка! [{escape(item.category.upper())}]</b>"
    title = f"🎮 <b>{escape(item.short_title())}</b>"

    pricing = (
        f"💰 Цена: <b>{item.price:g} {escape(item.currency)}</b>\n"
        f"📊 Оценка: <b>{result['estimated_price']:g} ₽</b> "
        f"(ком. ресейл: {result['resell_fee']:g} ₽)\n"
        f"📈 Чистый профит: <b>+{result['net_profit']:g} ₽</b> "
        f"(<b>{result['roi']}%</b> ROI, с учётом уверенности: {result['adjusted_roi']}%)\n"
        f"🎯 Уверенность оценки: <b>{int(result['confidence'] * 100)}%</b>"
    )

    lines = _humanize_details(item.category, details)
    breakdown = "\n".join(lines) if lines else ""

    seller = (
        f"👤 Продавец: <b>@{escape(item.seller_username)}</b> "
        f"(trust: {item.seller_trust})\n"
        f'🔗 <a href="{escape(item.item_url)}">Открыть лот на LZT</a> | '
        f'<a href="{escape(_client().build_seller_profile_url(item.seller_username))}">'
        f"Профиль продавца</a>"
    )

    warns_text = ""
    if warnings:
        warns_text = "\n\n" + "\n".join(warnings)

    parts = [header, "", title, "", pricing]
    if breakdown:
        parts += ["", "📋 <b>Состав лота:</b>", breakdown]
    parts += ["", seller + warns_text, "", "⚡ <b>Решение за вами:</b>"]
    return "\n".join(parts)


def format_buy_success(result: dict[str, Any], buy: BuyResult) -> str:
    item: MarketItem = result["item"]
    account_lines = buy.account_lines()
    account_block = ""
    if account_lines:
        joined = "\n".join(account_lines[:15])
        if len(account_lines) > 15:
            joined += f"\n<i>…и ещё {len(account_lines) - 15} полей</i>"
        account_block = f"\n\n🔐 <b>Данные аккаунта:</b>\n{joined}"

    return (
        f"✅ <b>Аккаунт успешно куплен!</b>\n\n"
        f"🎮 {escape(item.short_title())}\n"
        f"💰 Цена покупки: <b>{buy.purchase_price:g} ₽</b>\n"
        f"📈 Ожидаемый профит: <b>+{result['net_profit']:g} ₽</b> ({result['roi']}% ROI)\n"
        f'🔗 <a href="{escape(item.item_url)}">Лот на LZT</a>'
        f"{account_block}"
    )


def format_stats(stats: dict[str, Any]) -> str:
    spent = stats.get("total_spent") or 0
    profit = stats.get("total_expected_profit") or 0
    trades = stats.get("total_trades") or 0
    avg_profit = (profit / trades) if trades else 0
    by_status = stats.get("by_status") or {}
    by_cat = stats.get("by_category") or []

    cat_lines = []
    for row in by_cat:
        cat_lines.append(
            f"  • {escape(str(row['category']))}: "
            f"{row['cnt']} сделок, профит {row['profit']:g} ₽"
        )
    cat_block = "\n".join(cat_lines) if cat_lines else "  <i>пока пусто</i>"

    status_block = ", ".join(f"{k}: {v}" for k, v in by_status.items()) or "—"

    return (
        f"📊 <b>Статистика LZT Arbitrage Bot</b>\n\n"
        f"Всего сделок: <b>{trades}</b>\n"
        f"Потрачено: <b>{spent:g} ₽</b>\n"
        f"Ожидаемый профит: <b>{profit:g} ₽</b>\n"
        f"Средний профит на сделку: <b>{avg_profit:g} ₽</b>\n\n"
        f"<b>По статусам:</b> {status_block}\n\n"
        f"<b>По категориям:</b>\n{cat_block}"
    )


def format_balance(balances: dict[str, float] | None) -> str:
    if not balances:
        return "❌ Не удалось получить баланс. Проверьте LZT_API_TOKEN."
    return (
        f"💰 <b>Баланс LZT:</b>\n"
        f"Основной: <b>{balances['balance']:g} ₽</b>\n"
        f"Холд: <b>{balances['hold']:g} ₽</b>"
    )
