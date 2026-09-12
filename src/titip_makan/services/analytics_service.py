from typing import List, Dict, Any
from collections import defaultdict
from datetime import timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from titip_makan.repositories.order_repository import OrderRepository
from titip_makan.repositories.session_repository import SessionRepository
from titip_makan.schemas.analytics import (
    AnalyticsOverview,
    LeaderboardOut,
    LeaderboardEntry,
    BadgeInfo,
    TopItem,
    PeriodStat,
)

WIB = timezone(timedelta(hours=7))

class AnalyticsService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.order_repo = OrderRepository(db)
        self.session_repo = SessionRepository(db)

    async def get_overview(self) -> AnalyticsOverview:
        sessions = await self.session_repo.get_all_history()
        orders = await self.order_repo.get_all()

        total_sessions = len(sessions)
        total_orders = len(orders)
        total_spend = sum(o.price for o in orders)
        avg_price = (total_spend / total_orders) if total_orders > 0 else 0.0

        unique_users = len(set(o.user_name for o in orders))

        # Top menus
        menu_counts: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"count": 0, "total": 0, "vendor": ""})
        vendor_counts: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"count": 0, "total": 0})
        user_orders: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"spend": 0, "count": 0, "notes": 0, "menus": set()}
        )

        # Period buckets: daily, weekly, monthly
        daily_buckets: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"count": 0, "spend": 0, "menus": defaultdict(int), "users": defaultdict(int)}
        )
        weekly_buckets: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"count": 0, "spend": 0, "menus": defaultdict(int), "users": defaultdict(int)}
        )
        monthly_buckets: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"count": 0, "spend": 0, "menus": defaultdict(int), "users": defaultdict(int)}
        )

        for o in orders:
            # Menu aggregation
            menu_key = o.item_name
            menu_counts[menu_key]["count"] += 1
            menu_counts[menu_key]["total"] += o.price
            menu_counts[menu_key]["vendor"] = o.vendor

            # Vendor aggregation
            vendor_counts[o.vendor]["count"] += 1
            vendor_counts[o.vendor]["total"] += o.price

            # User aggregation
            user_orders[o.user_name]["spend"] += o.price
            user_orders[o.user_name]["count"] += 1
            if o.notes and o.notes.strip():
                user_orders[o.user_name]["notes"] += 1
            user_orders[o.user_name]["menus"].add(o.item_name)

            # Datetime in WIB
            dt = o.created_at
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            dt_wib = dt.astimezone(WIB)

            day_key = dt_wib.strftime("%Y-%m-%d")
            week_key = f"{dt_wib.year}-W{dt_wib.isocalendar().week:02d}"
            month_key = dt_wib.strftime("%Y-%m")

            for b_key, bucket_dict in [
                (day_key, daily_buckets),
                (week_key, weekly_buckets),
                (month_key, monthly_buckets),
            ]:
                b = bucket_dict[b_key]
                b["count"] += 1
                b["spend"] += o.price
                b["menus"][o.item_name] += 1
                b["users"][o.user_name] += o.price

        # Sort top menus & vendors
        top_menus = [
            TopItem(name=k, vendor=v["vendor"], count=v["count"], total_amount=v["total"])
            for k, v in sorted(menu_counts.items(), key=lambda item: (item[1]["count"], item[1]["total"]), reverse=True)
        ][:15]

        top_vendors = [
            TopItem(name=k, count=v["count"], total_amount=v["total"])
            for k, v in sorted(vendor_counts.items(), key=lambda item: (item[1]["count"], item[1]["total"]), reverse=True)
        ][:10]

        # Top spenders list
        sorted_users = sorted(user_orders.items(), key=lambda x: x[1]["spend"], reverse=True)
        top_spenders = [
            LeaderboardEntry(
                rank=idx + 1,
                user_name=k,
                total_spend=v["spend"],
                order_count=v["count"],
                custom_notes_count=v["notes"],
                unique_menus_count=len(v["menus"]),
                badges=[],
            )
            for idx, (k, v) in enumerate(sorted_users[:10])
        ]

        def _format_period(bucket_dict: Dict[str, Dict[str, Any]], period_type: str) -> List[PeriodStat]:
            result = []
            for k in sorted(bucket_dict.keys()):
                b = bucket_dict[k]
                top_m = max(b["menus"].items(), key=lambda x: x[1])[0] if b["menus"] else None
                top_u = max(b["users"].items(), key=lambda x: x[1])[0] if b["users"] else None
                label = k
                if period_type == "daily":
                    label = k  # e.g. 2026-09-08
                elif period_type == "weekly":
                    label = f"Pekan {k.split('-W')[-1]} ({k})"
                elif period_type == "monthly":
                    label = k
                result.append(
                    PeriodStat(
                        period=k,
                        label=label,
                        order_count=b["count"],
                        total_spend=b["spend"],
                        top_menu=top_m,
                        top_spender=top_u,
                    )
                )
            return result

        daily_stats = _format_period(daily_buckets, "daily")
        weekly_stats = _format_period(weekly_buckets, "weekly")
        monthly_stats = _format_period(monthly_buckets, "monthly")

        return AnalyticsOverview(
            total_sessions=total_sessions,
            total_orders=total_orders,
            total_spend=total_spend,
            unique_users=unique_users,
            average_order_price=round(avg_price, 2),
            daily_stats=daily_stats,
            weekly_stats=weekly_stats,
            monthly_stats=monthly_stats,
            top_menus=top_menus,
            top_vendors=top_vendors,
            top_spenders=top_spenders,
        )

    async def get_leaderboard(self) -> LeaderboardOut:
        orders = await self.order_repo.get_all()

        user_data: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"spend": 0, "count": 0, "notes": 0, "menus": set()}
        )

        for o in orders:
            user_data[o.user_name]["spend"] += o.price
            user_data[o.user_name]["count"] += 1
            if o.notes and o.notes.strip():
                user_data[o.user_name]["notes"] += 1
            user_data[o.user_name]["menus"].add(o.item_name)

        # Build initial badges templates
        badges = [
            BadgeInfo(
                code="sultan",
                title="Sultan Titip Makan",
                icon="👑",
                description="Top Spender dengan total pengeluaran paling tinggi",
            ),
            BadgeInfo(
                code="rajin",
                title="Si Paling Rajin Titip",
                icon="🏆",
                description="Paling sering titip makan (order count tertinggi)",
            ),
            BadgeInfo(
                code="catatan",
                title="Raja Catatan / Si Paling Custom",
                icon="✍️",
                description="Paling sering nulis catatan khusus saat titip makan",
            ),
            BadgeInfo(
                code="ninja",
                title="Ninja Lapar",
                icon="🥷",
                description="Paling jarang titip, tapi sekalinya muncul langsung memesan",
            ),
            BadgeInfo(
                code="setia",
                title="Penganut Setia / Konsisten",
                icon="🗿",
                description="Paling konsisten, pesan menu yang itu-itu saja terus",
            ),
            BadgeInfo(
                code="eksplorator",
                title="Eksplorator Kuliner",
                icon="🎨",
                description="Paling berani mencoba menu yang berbeda-beda terus",
            ),
        ]

        if not user_data:
            return LeaderboardOut(badges_summary=badges, rankings=[])

        # Assign badge winners
        user_badge_map: Dict[str, List[str]] = defaultdict(list)

        # 1. Sultan (Highest spend)
        top_spender_user, top_spender_val = max(user_data.items(), key=lambda x: x[1]["spend"])
        if top_spender_val["spend"] > 0:
            badges[0].holder = top_spender_user
            badges[0].metric_value = f"Rp {top_spender_val['spend']:,}"
            user_badge_map[top_spender_user].append("👑 Sultan Titip Makan")

        # 2. Si Paling Rajin (Highest order count)
        most_orders_user, most_orders_val = max(user_data.items(), key=lambda x: x[1]["count"])
        if most_orders_val["count"] > 0:
            badges[1].holder = most_orders_user
            badges[1].metric_value = f"{most_orders_val['count']} pesanan"
            user_badge_map[most_orders_user].append("🏆 Si Paling Rajin")

        # 3. Raja Catatan (Most custom notes)
        most_notes_user, most_notes_val = max(user_data.items(), key=lambda x: x[1]["notes"])
        if most_notes_val["notes"] > 0:
            badges[2].holder = most_notes_user
            badges[2].metric_value = f"{most_notes_val['notes']} catatan"
            user_badge_map[most_notes_user].append("✍️ Raja Catatan")

        # 4. Ninja Lapar (Lowest order count among active members)
        fewest_orders_user, fewest_orders_val = min(user_data.items(), key=lambda x: x[1]["count"])
        if fewest_orders_val["count"] > 0:
            badges[3].holder = fewest_orders_user
            badges[3].metric_value = f"{fewest_orders_val['count']} pesanan"
            user_badge_map[fewest_orders_user].append("🥷 Ninja Lapar")

        # 5. Penganut Setia (Lowest menu diversity ratio = unique_menus / order_count)
        eligible_setia = [
            (u, len(d["menus"]) / d["count"], len(d["menus"]), d["count"])
            for u, d in user_data.items()
            if d["count"] >= 2
        ]
        if eligible_setia:
            most_loyal_user, ratio, u_m, c_m = min(eligible_setia, key=lambda x: (x[1], -x[3]))
            badges[4].holder = most_loyal_user
            badges[4].metric_value = f"{u_m} variasi dari {c_m} order"
            user_badge_map[most_loyal_user].append("🗿 Penganut Setia")
        elif len(user_data) == 1:
            # If only 1 user with < 2 orders
            u, d = next(iter(user_data.items()))
            badges[4].holder = u
            badges[4].metric_value = f"{len(d['menus'])} menu"
            user_badge_map[u].append("🗿 Penganut Setia")

        # 6. Eksplorator Kuliner (Highest unique menus count)
        explorer_user, explorer_val = max(user_data.items(), key=lambda x: len(x[1]["menus"]))
        if len(explorer_val["menus"]) > 0:
            badges[5].holder = explorer_user
            badges[5].metric_value = f"{len(explorer_val['menus'])} menu unik"
            user_badge_map[explorer_user].append("🎨 Eksplorator Kuliner")

        # Sort rankings by total_spend desc
        sorted_users = sorted(user_data.items(), key=lambda x: (x[1]["spend"], x[1]["count"]), reverse=True)
        rankings = [
            LeaderboardEntry(
                rank=idx + 1,
                user_name=u,
                total_spend=d["spend"],
                order_count=d["count"],
                custom_notes_count=d["notes"],
                unique_menus_count=len(d["menus"]),
                badges=user_badge_map.get(u, []),
            )
            for idx, (u, d) in enumerate(sorted_users)
        ]

        return LeaderboardOut(badges_summary=badges, rankings=rankings)
