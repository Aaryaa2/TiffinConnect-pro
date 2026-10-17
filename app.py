"""
Tiffin Connect Pro — Design Thinking Prototype 2
================================================
Homely meals, hassle-free.

A single-file Streamlit demo for home tiffin services and their customers.

    pip install -r requirements.txt
    streamlit run app.py

IMPORTANT (demo only)
- All people, kitchens, prices, ratings, orders and payments are fictional.
- No real payments, logins, GPS or messaging.
- Data lives in Streamlit session state: it resets when the browser session
  ends or when "Reset demo data" is pressed. Nothing is stored permanently.
- The app runs on a fixed DEMO DATE with an adjustable DEMO TIME so cutoff
  rules behave the same way in every presentation.

File layout (top to bottom)
  1. Constants & sample data
  2. Business rules (pure functions: dates, subscriptions, money)
  3. Seed data builder
  4. State helpers & actions (callbacks that change data)
  5. Styling & reusable UI pieces
  6. Landing page
  7. Customer pages
  8. Owner pages
  9. main()
"""

from __future__ import annotations

import calendar
import html as _html
import random
from collections import defaultdict
from copy import deepcopy
from datetime import date, datetime, time, timedelta

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Tiffin Connect Pro", page_icon="🍱", layout="wide")

# =============================================================================
# 1. CONSTANTS & SAMPLE DATA
# =============================================================================

DEMO_TODAY = date(2026, 10, 20)          # fixed demo date (a Tuesday)
DEFAULT_TIME = "09:30"                    # default demo time
DEMO_TIMES = [f"{h:02d}:{m:02d}" for h in range(6, 23) for m in (0, 30)]
SCHEDULE_DAYS_AHEAD = 2                   # plan meals are scheduled today + 2 days

LOCALITIES = ["Wakad", "Hinjawadi", "Baner", "Aundh", "Pimple Saudagar"]
SLOTS = ["Lunch", "Dinner"]
SLOT_ICON = {"Lunch": "☀️", "Dinner": "🌙"}
SLOT_TIME = {"Lunch": time(13, 0), "Dinner": time(20, 0)}   # delivery time used for cutoffs

MEALS_PER_MONTH = 26                      # Mon–Sat delivery, Sundays off
PACKAGES = [                              # months, discount
    {"months": 1, "label": "1 month", "discount": 0.00},
    {"months": 3, "label": "3 months", "discount": 0.05},
    {"months": 6, "label": "6 months", "discount": 0.08},
    {"months": 9, "label": "9 months", "discount": 0.10},
    {"months": 12, "label": "12 months", "discount": 0.12},
]

STATUSES = ["Confirmed", "Preparing", "Prepared", "Out for delivery", "Delivered", "Skipped", "Cancelled"]
TRANSITIONS = {
    "Confirmed": ["Preparing", "Skipped", "Cancelled"],
    "Preparing": ["Prepared", "Cancelled"],
    "Prepared": ["Out for delivery"],
    "Out for delivery": ["Delivered"],
    "Delivered": [], "Skipped": [], "Cancelled": [],
}
ACTIVE = ("Confirmed", "Preparing", "Prepared", "Out for delivery")   # not yet delivered
COUNTED = ACTIVE + ("Delivered",)                                     # real meals (excl. skip/cancel)
FLOW = ["Confirmed", "Preparing", "Prepared", "Out for delivery", "Delivered"]
NEXT_LABEL = {
    "Preparing": "👩‍🍳 Start preparing", "Prepared": "✅ Mark prepared",
    "Out for delivery": "🛵 Send out", "Delivered": "📦 Mark delivered",
}
STATUS_STYLE = {
    "Confirmed": ("#E3EDE6", "#1F4D3A"), "Preparing": ("#F6E6DC", "#8E4528"),
    "Prepared": ("#EAE6F3", "#4B3F78"), "Out for delivery": ("#E2EAF3", "#2A4F78"),
    "Delivered": ("#D8EAD9", "#1F5A30"), "Skipped": ("#EEEBE5", "#615B51"),
    "Cancelled": ("#F5E0DC", "#8A2E24"),
    "Active": ("#D8EAD9", "#1F5A30"), "Upcoming": ("#E2EAF3", "#2A4F78"), "Expired": ("#EEEBE5", "#615B51"),
    "Paid": ("#D8EAD9", "#1F5A30"), "Partially paid": ("#F6E6DC", "#8E4528"), "Pending": ("#F5E0DC", "#8A2E24"),
    "Refunded": ("#E2EAF3", "#2A4F78"), "Not charged": ("#EEEBE5", "#615B51"), "Covered by plan": ("#E3EDE6", "#1F4D3A"),
}
PAY_NOW = "UPI · pay now (simulated)"
PAY_LATER_ORDER = "Cash / UPI on delivery"
PAY_LATER_SUB = "Pay later (adds a due)"

PROVIDERS = [
    {"id": "P1", "name": "Aaji's Kitchen", "owner": "Sunanda Kale", "icon": "🍛", "since": 2019,
     "locality": "Wakad", "cuisine": "Maharashtrian", "diet": "Veg", "slots": ["Lunch", "Dinner"],
     "prices": {"Lunch": 100, "Dinner": 90}, "rating": 4.7, "reviews": 212,
     "description": "Simple Maharashtrian ghar-ka-khana cooked by a grandmother-and-daughter team. "
                    "Less oil, soft polis and a different bhaji every day.",
     "phone": "+91 90000 11001", "email": "aajis.kitchen@example.com",
     "delivers_to": ["Wakad", "Hinjawadi", "Pimple Saudagar"],
     "accepting_orders": True, "accepting_subs": True, "capacity": 40, "cutoff_hours": 3},
    {"id": "P2", "name": "Annapurna Dabba Co.", "owner": "Hetal Shah", "icon": "🥘", "since": 2021,
     "locality": "Baner", "cuisine": "Gujarati", "diet": "Veg", "slots": ["Lunch", "Dinner"],
     "prices": {"Lunch": 110, "Dinner": 100}, "rating": 4.5, "reviews": 168,
     "description": "Gujarati dal, bhaat, shaak and rotli with a sweet on Saturdays. "
                    "Popular with working professionals around Baner and Balewadi.",
     "phone": "+91 90000 11002", "email": "annapurna.dabba@example.com",
     "delivers_to": ["Baner", "Aundh", "Wakad"],
     "accepting_orders": True, "accepting_subs": True, "capacity": 30, "cutoff_hours": 3},
    {"id": "P3", "name": "Konkan Coast Home Meals", "owner": "Vaishali Sawant", "icon": "🐟", "since": 2020,
     "locality": "Aundh", "cuisine": "Malvani / Konkani", "diet": "Veg & Non-Veg", "slots": ["Lunch", "Dinner"],
     "prices": {"Lunch": 140, "Dinner": 150}, "rating": 4.4, "reviews": 131,
     "description": "Malvani home cooking — fish thalis, chicken rassa and egg curries with solkadhi. "
                    "A vegetarian option is always on the menu.",
     "phone": "+91 90000 11003", "email": "konkan.coast@example.com",
     "delivers_to": ["Aundh", "Baner", "Wakad"],
     "accepting_orders": True, "accepting_subs": True, "capacity": 25, "cutoff_hours": 4},
    {"id": "P4", "name": "Green Bowl Tiffins", "owner": "Ritu Malhotra", "icon": "🥗", "since": 2022,
     "locality": "Hinjawadi", "cuisine": "Healthy North Indian", "diet": "Veg", "slots": ["Lunch"],
     "prices": {"Lunch": 120, "Dinner": 0}, "rating": 4.6, "reviews": 97,
     "description": "Light, high-protein lunches for IT-park professionals — millets, sprouts, "
                    "paneer and seasonal sabzi. Lunch only, delivered to your desk.",
     "phone": "+91 90000 11004", "email": "greenbowl@example.com",
     "delivers_to": ["Hinjawadi", "Wakad"],
     "accepting_orders": True, "accepting_subs": True, "capacity": 50, "cutoff_hours": 3},
    {"id": "P5", "name": "Ghar Ki Rasoi", "owner": "Manpreet Gill", "icon": "🍲", "since": 2018,
     "locality": "Pimple Saudagar", "cuisine": "Punjabi", "diet": "Veg & Non-Veg", "slots": ["Lunch", "Dinner"],
     "prices": {"Lunch": 100, "Dinner": 110}, "rating": 4.3, "reviews": 156,
     "description": "Hearty Punjabi home food — rajma chawal, chole and a home-style chicken curry "
                    "twice a week. Generous, student-friendly portions.",
     "phone": "+91 90000 11005", "email": "gharkirasoi@example.com",
     "delivers_to": ["Pimple Saudagar", "Wakad", "Aundh"],
     "accepting_orders": True, "accepting_subs": True, "capacity": 35, "cutoff_hours": 3},
    {"id": "P6", "name": "Dakshin Mane", "owner": "Lakshmi Iyer", "icon": "🍚", "since": 2023,
     "locality": "Hinjawadi", "cuisine": "South Indian", "diet": "Veg", "slots": ["Lunch", "Dinner"],
     "prices": {"Lunch": 90, "Dinner": 90}, "rating": 4.5, "reviews": 74,
     "description": "Comforting South Indian meals — sambar, rasam, poriyal and curd rice for lunch, "
                    "dosa and idli combos for dinner.",
     "phone": "+91 90000 11006", "email": "dakshin.mane@example.com",
     "delivers_to": ["Hinjawadi", "Wakad"],
     "accepting_orders": True, "accepting_subs": False, "capacity": 30, "cutoff_hours": 3},
]

# Two daily menu sets per kitchen: (meal name, description, price difference from the slot price)
MENU_LIB = {
    "P1": [
        {"Lunch": [("Maharashtrian Veg Thali", "Matki usal, varan bhaat, 3 poli, koshimbir, papad", 0),
                   ("Mini Tiffin", "Batata bhaji, 2 poli, dal, rice", -25)],
         "Dinner": [("Pithla Bhakri Plate", "Besan pithla, 2 jowar bhakri, thecha, onion", 0),
                    ("Light Khichdi", "Moong dal khichdi, kadhi, papad", -15)]},
        {"Lunch": [("Maharashtrian Veg Thali", "Bharli vangi, masale bhaat, 3 poli, salad", 0),
                   ("Mini Tiffin", "Usal, 2 poli, jeera rice", -25)],
         "Dinner": [("Varan Bhaat Plate", "Varan bhaat with ghee, batata bhaji, 2 poli", 0)]},
    ],
    "P2": [
        {"Lunch": [("Gujarati Thali", "Dal, bhaat, sev tameta shaak, 4 rotli, chaas", 0),
                   ("Kathiyawadi Combo", "Ringan oro, bajra rotla, khichdi, chaas", 20)],
         "Dinner": [("Kadhi Khichdi", "Gujarati kadhi, moong khichdi, papad", -10)]},
        {"Lunch": [("Gujarati Thali", "Tuvar dal, bhaat, bhindi shaak, 4 rotli", 0)],
         "Dinner": [("Thepla Combo", "3 methi thepla, aloo shaak, curd", -10)]},
    ],
    "P3": [
        {"Lunch": [("Fish Thali", "Bangda fry, Malvani fish curry, rice, solkadhi", 0),
                   ("Veg Malvani Thali", "Kala vatana usal, rice, 2 chapati, solkadhi", -30)],
         "Dinner": [("Chicken Rassa Plate", "Malvani chicken curry, 2 vade, rice", 10),
                    ("Egg Curry Plate", "Egg curry, 2 chapati, rice", -20)]},
        {"Lunch": [("Fish Thali", "Surmai fry, kokum curry, rice, solkadhi", 20),
                   ("Veg Malvani Thali", "Bharli vangi, rice, 2 chapati", -30)],
         "Dinner": [("Chicken Rassa Plate", "Malvani chicken curry, 2 vade, rice", 10)]},
    ],
    "P4": [
        {"Lunch": [("Protein Bowl", "Rajma, brown rice, paneer tikka salad, curd", 0),
                   ("Millet Meal", "Bajra roti, lauki chana, sprouts chaat", -10)]},
        {"Lunch": [("Protein Bowl", "Chole, quinoa pulao, cucumber raita", 0)]},
    ],
    "P5": [
        {"Lunch": [("Punjabi Veg Thali", "Rajma, jeera rice, aloo gobhi, 3 roti", 0),
                   ("Chicken Curry Meal", "Home-style chicken curry, rice, 2 roti", 40)],
         "Dinner": [("Dal Makhani Plate", "Dal makhani, 3 phulka, salad", 0)]},
        {"Lunch": [("Punjabi Veg Thali", "Chole, rice, bhindi, 3 roti", 0)],
         "Dinner": [("Kadhi Chawal", "Punjabi kadhi pakoda, rice, papad", -10)]},
    ],
    "P6": [
        {"Lunch": [("South Indian Meals", "Sambar, rasam, poriyal, rice, curd, appalam", 0)],
         "Dinner": [("Dosa Combo", "2 dosas, coconut chutney, sambar", -10)]},
        {"Lunch": [("South Indian Meals", "Bisi bele bath, curd rice, kosambari", 0)],
         "Dinner": [("Idli Combo", "4 idlis, sambar, chutney", -15)]},
    ],
}

CUSTOMERS = [
    {"id": "C1", "name": "Riya Kulkarni", "locality": "Wakad", "address": "Flat 302, Shanti Heights, Dange Chowk",
     "about": "Student, lives alone"},
    {"id": "C2", "name": "Amit Joshi", "locality": "Wakad", "address": "Room 14, Kaspate Wasti PG"},
    {"id": "C3", "name": "Sneha Patil", "locality": "Hinjawadi", "address": "B-6, Phase 1, Blue Ridge"},
    {"id": "C4", "name": "Rahul Deshmukh", "locality": "Wakad", "address": "Palm Spring Society, Wing C"},
    {"id": "C5", "name": "Kavya Iyer", "locality": "Pimple Saudagar", "address": "Kunal Icon Road, Flat 9"},
    {"id": "C6", "name": "Omkar Bhosale", "locality": "Wakad", "address": "Bhumkar Chowk, Lane 2"},
    {"id": "C7", "name": "Neha Shah", "locality": "Baner", "address": "Balewadi High Street, Tower 4"},
    {"id": "C8", "name": "Arjun Menon", "locality": "Hinjawadi", "address": "Megapolis, Phase 3"},
    {"id": "C9", "name": "Pooja Gaikwad", "locality": "Aundh", "address": "ITI Road, Siddhi Apartments"},
    {"id": "C10", "name": "Siddharth Rao", "locality": "Baner", "address": "Pancard Club Road, Flat 11"},
    {"id": "C11", "name": "Ishita Verma", "locality": "Pimple Saudagar", "address": "Rahatani Road, Flat 7"},
    {"id": "C12", "name": "Varun Kapoor", "locality": "Hinjawadi", "address": "Phase 2, Hostel Block B"},
]
for _i, _c in enumerate(CUSTOMERS, start=1):
    _c.setdefault("phone", f"+91 90000 2{_i:04d}")
    _c.setdefault("email", _c["name"].split()[0].lower() + "@example.com")
    _c.setdefault("diet", "Vegetarian")
    _c.setdefault("about", "")
    _c.setdefault("default_pay", PAY_NOW)

# (customer, kitchen, months, meal slots, start date, payment: paid / partial / pending)
SEED_SUBS = [
    ("C1", "P1", 1, ["Lunch"], date(2026, 8, 10), "paid"),          # Riya's previous plan (expired)
    ("C2", "P1", 1, ["Dinner"], date(2026, 7, 6), "paid"),          # expired
    ("C2", "P1", 3, ["Lunch"], date(2026, 8, 3), "paid"),
    ("C3", "P1", 1, ["Lunch"], date(2026, 10, 5), "partial"),
    ("C4", "P1", 6, ["Lunch", "Dinner"], date(2026, 7, 15), "paid"),
    ("C5", "P1", 1, ["Lunch"], date(2026, 9, 21), "paid"),          # last day = demo date
    ("C6", "P1", 1, ["Lunch", "Dinner"], date(2026, 10, 12), "pending"),
    ("C7", "P2", 1, ["Lunch"], date(2026, 10, 1), "paid"),
    ("C10", "P2", 3, ["Lunch", "Dinner"], date(2026, 8, 20), "paid"),
    ("C9", "P3", 3, ["Dinner"], date(2026, 9, 1), "paid"),
    ("C8", "P4", 1, ["Lunch"], date(2026, 10, 8), "pending"),
    ("C11", "P5", 6, ["Dinner"], date(2026, 6, 1), "paid"),
    ("C12", "P6", 1, ["Lunch"], date(2026, 9, 25), "paid"),
]


# =============================================================================
# 2. BUSINESS RULES (pure functions — easy to read and test)
# =============================================================================

def add_months(d: date, months: int) -> date:
    m = d.month - 1 + months
    y = d.year + m // 12
    m = m % 12 + 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def sub_expiry(start: date, months: int) -> date:
    """Validity: from start date up to the day before the same date N months later."""
    return add_months(start, months) - timedelta(days=1)


def sub_total_meals(months: int, slots: list[str]) -> int:
    return MEALS_PER_MONTH * months * len(slots)


def sub_price(provider: dict, months: int, slots: list[str]) -> int:
    disc = next(p["discount"] for p in PACKAGES if p["months"] == months)
    base = sum(provider["prices"][s] for s in slots) * MEALS_PER_MONTH * months
    return int(round(base * (1 - disc), -1))


def cutoff_dt(provider: dict, day: date, slot: str) -> datetime:
    """Orders and skips close `cutoff_hours` before the slot's delivery time."""
    return datetime.combine(day, SLOT_TIME[slot]) - timedelta(hours=provider["cutoff_hours"])


def month_bounds(ym: str) -> tuple[date, date]:
    y, m = map(int, ym.split("-"))
    return date(y, m, 1), date(y, m, calendar.monthrange(y, m)[1])


def mkey(pid: str, day: date) -> str:
    return f"{pid}|{day.isoformat()}"


def payment_index(d: dict) -> dict:
    """
    Money rules (one source of truth):
      * A CHARGE is created by
          - a one-day order (its order value), unless the order was skipped/cancelled
          - a subscription purchase (its package price)
        Plan meals have no charge of their own (they are covered by the subscription),
        so revenue is never counted twice.
      * A PAYMENT is a recorded receipt linked to one charge. Refunds are negative payments.
      * OUTSTANDING = charge − payments recorded against it (never below zero).
      * INCOME for a period = payments recorded in that period (net of refunds).
    Returns {ref_id: {...}} for every chargeable reference.
    """
    paid, n_pay = defaultdict(int), defaultdict(int)
    for p in d["payments"]:
        paid[p["ref_id"]] += p["amount"]
        n_pay[p["ref_id"]] += 1
    idx = {}
    for o in d["orders"]:
        if o["order_type"] != "One-day":
            continue
        charge = 0 if o["status"] in ("Skipped", "Cancelled") else o["amount"]
        idx[o["id"]] = _ledger_row("One-day order", o["id"], o["provider_id"], o["customer_id"],
                                   o["date"], charge, paid[o["id"]], n_pay[o["id"]],
                                   f"{o['meal_name']} × {o['qty']} ({o['slot']}, {o['date']:%d %b})")
    for s in d["subs"]:
        idx[s["id"]] = _ledger_row("Subscription", s["id"], s["provider_id"], s["customer_id"],
                                   s["purchased_at"].date(), s["price"], paid[s["id"]], n_pay[s["id"]],
                                   f"{s['package']} · {' + '.join(s['slots'])}")
    return idx


def _ledger_row(kind, ref, pid, cid, billed_on, charge, paid, n_pay, desc):
    if charge == 0:
        status = "Refunded" if n_pay else "Not charged"
    elif paid >= charge:
        status = "Paid"
    elif paid > 0:
        status = "Partially paid"
    else:
        status = "Pending"
    return {"kind": kind, "ref_id": ref, "provider_id": pid, "customer_id": cid, "billed_on": billed_on,
            "charge": charge, "paid": paid, "outstanding": max(charge - paid, 0), "status": status, "desc": desc}


def order_pay_status(o: dict, idx: dict) -> str:
    if o["order_type"] == "Subscription":
        return "Covered by plan"
    return idx.get(o["id"], {}).get("status", "Pending")


# =============================================================================
# 3. SEED DATA (deterministic — the same every time)
# =============================================================================

def new_id(d: dict, kind: str) -> str:
    prefix = {"order": "ORD", "pay": "PAY", "sub": "SUB", "item": "MI"}[kind]
    d["counters"][kind] += 1
    return f"{prefix}-{d['counters'][kind]}"


def add_order(d, *, cid, pid, day, slot, meal_name, item_id, qty, unit_price, order_type, sub_id,
              created_at, pay_mode, note="", status="Confirmed", status_at=None, by="Customer") -> dict:
    o = {
        "id": new_id(d, "order"), "customer_id": cid, "provider_id": pid, "date": day, "slot": slot,
        "meal_name": meal_name, "item_id": item_id, "qty": qty, "unit_price": unit_price,
        "amount": unit_price * qty if order_type == "One-day" else 0,
        "order_type": order_type, "sub_id": sub_id, "pay_mode": pay_mode, "note": note,
        "delivery_locality": d["customers"][cid]["locality"], "status": "Confirmed",
        "created_at": created_at, "history": [{"at": created_at, "status": "Confirmed", "by": by}],
    }
    if status != "Confirmed":
        o["status"] = status
        o["history"].append({"at": status_at or created_at, "status": status, "by": "Kitchen"})
    d["orders"].append(o)
    return o


def add_payment(d, *, pid, cid, ref_id, ref_type, amount, method, at, kind="Payment", note="") -> dict:
    p = {"id": new_id(d, "pay"), "provider_id": pid, "customer_id": cid, "ref_id": ref_id,
         "ref_type": ref_type, "kind": kind, "amount": int(amount), "method": method, "at": at, "note": note}
    d["payments"].append(p)
    return p


def make_items(d, pid, day_set) -> list[dict]:
    p = d["providers"][pid]
    items = []
    for slot in SLOTS:
        for name, desc, delta in day_set.get(slot, []):
            items.append({"id": new_id(d, "item"), "slot": slot, "name": name, "desc": desc,
                          "price": p["prices"][slot] + delta})
    return items


def build_seed() -> dict:
    rng = random.Random(2026)
    today = DEMO_TODAY
    d = {
        "providers": {p["id"]: deepcopy(p) for p in PROVIDERS},
        "customers": {c["id"]: dict(c) for c in CUSTOMERS},
        "menus": {}, "orders": [], "subs": [], "payments": [], "activity": [],
        "counters": {"order": 10000, "pay": 5000, "sub": 300, "item": 1000},
    }

    # --- Menus: today published for all; tomorrow published except Aaji's Kitchen (draft only)
    for pid in d["providers"]:
        for off in (0, 1):
            day = today + timedelta(days=off)
            items = make_items(d, pid, MENU_LIB[pid][off])
            entry = {"draft": items, "published": None, "published_at": None}
            if not (pid == "P1" and off == 1):
                entry["published"] = deepcopy(items)
                entry["published_at"] = datetime.combine(today if off else today, time(7, 0 if not off else 15))
            d["menus"][mkey(pid, day)] = entry

    taken = set()   # (customer, kitchen, date, slot) with an active/delivered order

    def status_for_past(r):
        return "Skipped" if r < 0.07 else "Delivered"

    # --- Subscriptions and their meals
    for cid, pid, months, slots, start, pay in SEED_SUBS:
        p = d["providers"][pid]
        purchased_at = datetime.combine(start - timedelta(days=1), time(19, 15))
        sub = {"id": new_id(d, "sub"), "customer_id": cid, "provider_id": pid, "months": months,
               "package": next(x["label"] for x in PACKAGES if x["months"] == months), "slots": list(slots),
               "start": start, "expiry": sub_expiry(start, months), "total_meals": sub_total_meals(months, slots),
               "price": sub_price(p, months, slots), "purchased_at": purchased_at, "status": "Active",
               "pay_choice": PAY_NOW if pay == "paid" else PAY_LATER_SUB}
        d["subs"].append(sub)
        if pay == "paid":
            add_payment(d, pid=pid, cid=cid, ref_id=sub["id"], ref_type="Subscription", amount=sub["price"],
                        method="UPI (simulated)", at=purchased_at)
        elif pay == "partial":
            add_payment(d, pid=pid, cid=cid, ref_id=sub["id"], ref_type="Subscription",
                        amount=int(round(sub["price"] / 2, -1)), method="Cash", at=purchased_at,
                        note="Part payment")
        used = 0
        day = start
        last = min(sub["expiry"], today + timedelta(days=SCHEDULE_DAYS_AHEAD))
        while day <= last and used < sub["total_meals"]:
            if day.weekday() != 6:  # Sundays off
                for slot in slots:
                    if used >= sub["total_meals"]:
                        break
                    st_ = status_for_past(rng.random()) if day < today else "Confirmed"
                    o = add_order(d, cid=cid, pid=pid, day=day, slot=slot, meal_name=f"{slot} plan thali",
                                  item_id=None, qty=1, unit_price=p["prices"][slot], order_type="Subscription",
                                  sub_id=sub["id"], created_at=purchased_at, pay_mode="Plan", status=st_,
                                  status_at=datetime.combine(day, time(9, 0) if st_ == "Skipped" else SLOT_TIME[slot]),
                                  by="Customer" if st_ == "Skipped" else "Kitchen")
                    if st_ == "Skipped":
                        o["history"][-1]["by"] = "Customer"
                    else:
                        used += 1
                        taken.add((cid, pid, day, slot))
            day += timedelta(days=1)

    # --- Riya's (C1) own history
    def riya(pid, day, slot, idx, status, paymode, paid_on_delivery=True):
        p = d["providers"][pid]
        name, desc, delta = MENU_LIB[pid][0][slot][idx]
        created = datetime.combine(day - timedelta(days=1), time(20, 10))
        o = add_order(d, cid="C1", pid=pid, day=day, slot=slot, meal_name=name, item_id=None, qty=1,
                      unit_price=p["prices"][slot] + delta, order_type="One-day", sub_id=None,
                      created_at=created, pay_mode=paymode, status=status,
                      status_at=datetime.combine(day, SLOT_TIME[slot] if status == "Delivered" else time(8, 40)))
        if status == "Skipped":
            o["history"][-1]["by"] = "Customer"
        if paymode == PAY_NOW:
            add_payment(d, pid=pid, cid="C1", ref_id=o["id"], ref_type="Order", amount=o["amount"],
                        method="UPI (simulated)", at=created)
            if status in ("Skipped", "Cancelled"):
                add_payment(d, pid=pid, cid="C1", ref_id=o["id"], ref_type="Order", amount=-o["amount"],
                            method="UPI refund (simulated)", at=o["history"][-1]["at"], kind="Refund",
                            note=f"Refund for {status.lower()} order")
        elif status == "Delivered" and paid_on_delivery:
            add_payment(d, pid=pid, cid="C1", ref_id=o["id"], ref_type="Order", amount=o["amount"],
                        method="Cash", at=datetime.combine(day, SLOT_TIME[slot]))
        taken.add(("C1", pid, day, slot))

    riya("P2", date(2026, 9, 22), "Lunch", 0, "Delivered", PAY_NOW)
    riya("P3", date(2026, 9, 29), "Dinner", 1, "Delivered", PAY_LATER_ORDER)
    riya("P2", date(2026, 10, 6), "Lunch", 1, "Delivered", PAY_NOW)
    riya("P3", date(2026, 10, 9), "Dinner", 0, "Delivered", PAY_LATER_ORDER)
    riya("P1", date(2026, 10, 14), "Dinner", 0, "Delivered", PAY_LATER_ORDER, paid_on_delivery=False)  # a due
    riya("P4", date(2026, 10, 16), "Lunch", 0, "Skipped", PAY_NOW)                                      # refunded

    # --- Random one-day orders from other customers (July → today)
    others = [c for c in d["customers"] if c != "C1"]
    day = date(2026, 7, 1)
    while day <= today:
        for pid, p in d["providers"].items():
            if day.weekday() == 6:
                n = rng.randint(0, 1)
            else:
                n = rng.randint(1, 3) if pid == "P1" else rng.randint(0, 2)
            fixed = [("C8", "Lunch"), ("C12", "Lunch"), ("C11", "Dinner")] if (day == today and pid == "P1") else None
            for k in range(len(fixed) if fixed else n):
                cid, slot = fixed[k] if fixed else (rng.choice(others), rng.choice(p["slots"]))
                if (cid, pid, day, slot) in taken:
                    continue
                set_ = MENU_LIB[pid][0 if day == today else rng.randint(0, 1)]
                name, desc, delta = rng.choice(set_[slot])
                qty = 2 if rng.random() < 0.15 else 1
                prepaid = rng.random() < 0.4
                created = datetime.combine(day - timedelta(days=1), time(rng.randint(18, 21), rng.choice([5, 20, 40])))
                if day == today:
                    created = datetime.combine(today, time(7, rng.choice([10, 25, 45])))
                    status = "Confirmed"
                else:
                    r = rng.random()
                    status = "Delivered" if r < 0.86 else ("Skipped" if r < 0.94 else "Cancelled")
                o = add_order(d, cid=cid, pid=pid, day=day, slot=slot, meal_name=name, item_id=None, qty=qty,
                              unit_price=p["prices"][slot] + delta, order_type="One-day", sub_id=None,
                              created_at=created, pay_mode=PAY_NOW if prepaid else PAY_LATER_ORDER,
                              status=status, status_at=datetime.combine(day, SLOT_TIME[slot] if status == "Delivered" else time(9, 15)))
                if status == "Skipped":
                    o["history"][-1]["by"] = "Customer"
                if prepaid:
                    add_payment(d, pid=pid, cid=cid, ref_id=o["id"], ref_type="Order", amount=o["amount"],
                                method="UPI (simulated)", at=created)
                    if status in ("Skipped", "Cancelled"):
                        add_payment(d, pid=pid, cid=cid, ref_id=o["id"], ref_type="Order", amount=-o["amount"],
                                    method="UPI refund (simulated)", at=o["history"][-1]["at"], kind="Refund",
                                    note=f"Refund for {status.lower()} order")
                elif status == "Delivered" and rng.random() < 0.93:
                    add_payment(d, pid=pid, cid=cid, ref_id=o["id"], ref_type="Order", amount=o["amount"],
                                method=rng.choice(["Cash", "UPI (simulated)"]),
                                at=datetime.combine(day, SLOT_TIME[slot]))
                taken.add((cid, pid, day, slot))
        day += timedelta(days=1)

    # One of today's lunch plan meals is already being prepared (shows the "can't skip" state)
    for o in d["orders"]:
        if o["provider_id"] == "P1" and o["date"] == today and o["slot"] == "Lunch" and o["customer_id"] == "C4":
            o["status"] = "Preparing"
            o["history"].append({"at": datetime.combine(today, time(9, 5)), "status": "Preparing", "by": "Kitchen"})

    d["orders"].sort(key=lambda o: o["id"])
    d["activity"] = [
        {"pid": "P1", "at": datetime.combine(today, time(7, 0)), "icon": "📝", "text": "Today's menu published"},
        {"pid": "P1", "at": datetime.combine(today, time(7, 25)), "icon": "🛒", "text": "New one-day orders received"},
        {"pid": "P1", "at": datetime.combine(today, time(9, 5)), "icon": "👩‍🍳",
         "text": "Rahul Deshmukh's lunch is being prepared"},
    ]
    return d


# =============================================================================
# 4. STATE HELPERS & ACTIONS
# =============================================================================

def init_state() -> None:
    if "db" not in st.session_state:
        st.session_state.db = build_seed()
    for k, v in {"role": None, "cid": "C1", "pid": "P1", "clock": DEFAULT_TIME, "cpage": "Dashboard",
                 "opage": "Dashboard", "sel_provider": None, "skip_pending": None, "flash": [],
                 "edit_item": None, "ver": 0}.items():
        st.session_state.setdefault(k, v)


def D() -> dict:
    return st.session_state.db


def now() -> datetime:
    return datetime.combine(DEMO_TODAY, time.fromisoformat(st.session_state.clock))


def today() -> date:
    return DEMO_TODAY


def prov(pid: str) -> dict:
    return D()["providers"][pid]


def cust(cid: str) -> dict:
    return D()["customers"].get(cid, {"name": "Unknown", "locality": "", "phone": "", "address": "", "email": ""})


def me() -> dict:
    return cust(st.session_state.cid)


def find_order(oid: str) -> dict | None:
    return next((o for o in D()["orders"] if o["id"] == oid), None)


def find_sub(sid: str) -> dict | None:
    return next((s for s in D()["subs"] if s["id"] == sid), None)


def pub_menu(pid: str, day: date) -> list[dict] | None:
    m = D()["menus"].get(mkey(pid, day))
    return m["published"] if m and m["published"] else None


def sub_state(s: dict) -> str:
    if s["status"] == "Cancelled":
        return "Cancelled"
    if s["start"] > today():
        return "Upcoming"
    if s["expiry"] < today():
        return "Expired"
    return "Active"


def sub_counts(s: dict) -> dict:
    c = {"Delivered": 0, "Scheduled": 0, "Skipped": 0, "Cancelled": 0}
    for o in D()["orders"]:
        if o["sub_id"] == s["id"]:
            if o["status"] == "Delivered":
                c["Delivered"] += o["qty"]
            elif o["status"] in ACTIVE:
                c["Scheduled"] += o["qty"]
            else:
                c[o["status"]] += o["qty"]
    c["Remaining"] = max(s["total_meals"] - c["Delivered"] - c["Scheduled"], 0)
    return c


def booked(pid: str, day: date, slot: str) -> int:
    return sum(o["qty"] for o in D()["orders"] if o["provider_id"] == pid and o["date"] == day
               and o["slot"] == slot and o["status"] in COUNTED)


def active_order(cid, pid, day, slot) -> dict | None:
    return next((o for o in D()["orders"] if o["customer_id"] == cid and o["provider_id"] == pid
                 and o["date"] == day and o["slot"] == slot and o["status"] in COUNTED), None)


def can_order(pid: str, cid: str, day: date, slot: str) -> tuple[bool, str]:
    p, c = prov(pid), cust(cid)
    if not p["accepting_orders"]:
        return False, f"{p['name']} isn't taking one-day orders right now."
    if slot not in p["slots"]:
        return False, f"{p['name']} doesn't serve {slot.lower()}."
    if c["locality"] not in p["delivers_to"]:
        return False, f"{p['name']} doesn't deliver to {c['locality']}."
    if not pub_menu(pid, day):
        return False, "The menu for this day isn't published yet."
    if not any(i["slot"] == slot for i in pub_menu(pid, day)):
        return False, f"No {slot.lower()} items on this day's menu."
    if now() >= cutoff_dt(p, day, slot):
        return False, f"Ordering for this {slot.lower()} closed at {cutoff_dt(p, day, slot):%H:%M}."
    ex = active_order(cid, pid, day, slot)
    if ex:
        what = "your plan meal" if ex["order_type"] == "Subscription" else f"order {ex['id']}"
        return False, f"You already have {slot.lower()} from this kitchen that day ({what})."
    if booked(pid, day, slot) >= p["capacity"]:
        return False, "Sold out for this meal."
    return True, ""


def log(pid: str, icon: str, text: str) -> None:
    D()["activity"].append({"pid": pid, "at": now(), "icon": icon, "text": text})


def flash(kind: str, title: str, body: str = "") -> None:
    st.session_state.flash.append((kind, title, body))


def ensure_valid(key: str, options: list) -> None:
    if key in st.session_state and st.session_state[key] not in options:
        del st.session_state[key]


def set_status(o: dict, new: str, by: str) -> tuple[bool, str]:
    """The only place an order status changes. Enforces TRANSITIONS and handles refunds."""
    if new not in TRANSITIONS.get(o["status"], []):
        return False, f"{o['id']} is {o['status']} — it can't move to {new}."
    o["status"] = new
    o["history"].append({"at": now(), "status": new, "by": by})
    if new in ("Skipped", "Cancelled") and o["order_type"] == "One-day":
        paid = sum(p["amount"] for p in D()["payments"] if p["ref_id"] == o["id"])
        if paid > 0:
            add_payment(D(), pid=o["provider_id"], cid=o["customer_id"], ref_id=o["id"], ref_type="Order",
                        amount=-paid, method="UPI refund (simulated)", at=now(), kind="Refund",
                        note=f"Refund for {new.lower()} order")
    return True, ""


def schedule_plan_meals(sub: dict) -> int:
    """Create plan-meal orders from max(start, today) up to today+2 days (Mon–Sat), skipping slots whose
    cutoff has passed. Idempotent: never creates the same (plan, date, slot) twice."""
    d, p = D(), prov(sub["provider_id"])
    existing = {(o["date"], o["slot"]) for o in d["orders"] if o["sub_id"] == sub["id"]}
    created = 0
    day = max(sub["start"], today())
    last = min(sub["expiry"], today() + timedelta(days=SCHEDULE_DAYS_AHEAD))
    while day <= last:
        if day.weekday() != 6:
            for slot in sub["slots"]:
                if (day, slot) in existing or now() >= cutoff_dt(p, day, slot):
                    continue
                if sub_counts(sub)["Remaining"] <= 0:
                    return created
                if active_order(sub["customer_id"], sub["provider_id"], day, slot):
                    continue  # customer already ordered this meal separately
                add_order(d, cid=sub["customer_id"], pid=sub["provider_id"], day=day, slot=slot,
                          meal_name=f"{slot} plan thali", item_id=None, qty=1, unit_price=p["prices"][slot],
                          order_type="Subscription", sub_id=sub["id"], created_at=now(), pay_mode="Plan")
                created += 1
        day += timedelta(days=1)
    return created


# ---------- callbacks: navigation ----------

def clear_keys(*prefixes):
    for k in list(st.session_state.keys()):
        if k.startswith(prefixes):
            del st.session_state[k]


def cb_role(role, account=None):
    clear_keys("pf_", "kp_", "sel_", "last_", "ni_", "ei_", "oq_", "op_", "on_")
    st.session_state.role = role
    st.session_state.skip_pending = None
    st.session_state.edit_item = None
    if role == "customer":
        st.session_state.cid = st.session_state.get("land_cust", "C1")
        st.session_state.cpage = "Dashboard"
    elif role == "owner":
        st.session_state.pid = st.session_state.get("land_owner", "P1")
        st.session_state.opage = "Dashboard"


def cb_cnav(page):
    st.session_state.cpage = page
    st.session_state.skip_pending = None


def cb_onav(page):
    st.session_state.opage = page
    st.session_state.edit_item = None


def cb_open_provider(pid):
    st.session_state.sel_provider = pid
    st.session_state.cpage = "Kitchen"


def cb_clock():
    st.session_state.clock = st.session_state.clock_w
    st.session_state.skip_pending = None


def cb_reset():
    st.session_state.db = build_seed()
    st.session_state.clock = DEFAULT_TIME
    st.session_state.skip_pending = None
    st.session_state.edit_item = None
    st.session_state.ver += 1
    for k in list(st.session_state.keys()):
        if k.startswith(("sel_", "last_", "pf_", "kp_", "oq_", "op_")):
            del st.session_state[k]
    flash("success", "Demo data reset", "All sample records and the demo clock are back to the starting state.")


# ---------- callbacks: customer ----------

def cb_select_item(pid, day_iso, slot, item_id):
    st.session_state[f"sel_{pid}"] = (day_iso, slot, item_id)
    st.session_state.pop(f"last_{pid}", None)


def cb_place_order(pid):
    sel = st.session_state.get(f"sel_{pid}")
    if not sel:
        flash("error", "Choose a meal first")
        return
    day_iso, slot, item_id = sel
    day = date.fromisoformat(day_iso)
    cid = st.session_state.cid
    ok, why = can_order(pid, cid, day, slot)
    if not ok:
        flash("error", "Order not placed", _html.escape(why))
        return
    item = next((i for i in pub_menu(pid, day) if i["id"] == item_id), None)
    if item is None:
        flash("error", "That meal is no longer on the menu", "The kitchen updated its menu. Please choose again.")
        st.session_state.pop(f"sel_{pid}", None)
        return
    qty = int(st.session_state.get(f"oq_{pid}", 1) or 1)
    p = prov(pid)
    if booked(pid, day, slot) + qty > p["capacity"]:
        flash("error", "Not enough tiffins left", f"Only {p['capacity'] - booked(pid, day, slot)} left.")
        return
    pay = st.session_state.get(f"op_{pid}", PAY_NOW)
    note = (st.session_state.get(f"on_{pid}") or "").strip()
    o = add_order(D(), cid=cid, pid=pid, day=day, slot=slot, meal_name=item["name"], item_id=item["id"],
                  qty=qty, unit_price=item["price"], order_type="One-day", sub_id=None, created_at=now(),
                  pay_mode=pay, note=note)
    if pay == PAY_NOW:
        add_payment(D(), pid=pid, cid=cid, ref_id=o["id"], ref_type="Order", amount=o["amount"],
                    method="UPI (simulated)", at=now())
    log(pid, "🛒", f"{cust(cid)['name']} ordered {qty} × {item['name']} ({slot}, {day:%a %d %b})")
    st.session_state[f"last_{pid}"] = o["id"]
    st.session_state.pop(f"sel_{pid}", None)
    st.session_state[f"on_{pid}"] = ""


def cb_activate_sub(prefix: str, fixed_pid: str | None = None):
    cid = st.session_state.cid
    pid = fixed_pid or st.session_state.get(f"{prefix}_pid")
    if not pid:
        flash("error", "Choose a tiffin service")
        return
    p = prov(pid)
    months = int(st.session_state.get(f"{prefix}_months", 3))
    meal_opt = st.session_state.get(f"{prefix}_meals_{pid}") or p["slots"][0]
    slots = list(p["slots"]) if meal_opt == "Lunch + Dinner" else [meal_opt]
    start = st.session_state.get(f"{prefix}_start", today())
    pay = st.session_state.get(f"{prefix}_pay", PAY_NOW)
    errors = []
    if not p["accepting_subs"]:
        errors.append(f"{p['name']} isn't accepting new subscriptions right now.")
    if any(s not in p["slots"] for s in slots):
        errors.append(f"{p['name']} doesn't serve that meal.")
    if not isinstance(start, date) or start < today() or start > today() + timedelta(days=30):
        errors.append("Choose a start date between today and 30 days from now.")
    if cust(cid)["locality"] not in p["delivers_to"]:
        errors.append(f"{p['name']} doesn't deliver to {cust(cid)['locality']}.")
    expiry = sub_expiry(start, months) if isinstance(start, date) else None
    for s in D()["subs"]:
        if (s["customer_id"] == cid and s["provider_id"] == pid and sub_state(s) in ("Active", "Upcoming")
                and expiry and s["start"] <= expiry and s["expiry"] >= start):
            errors.append(f"You already have {s['id']} with this kitchen until {s['expiry']:%d %b %Y}.")
            break
    if errors:
        flash("error", "Subscription not activated", "<br>".join(_html.escape(e) for e in errors))
        return
    sub = {"id": new_id(D(), "sub"), "customer_id": cid, "provider_id": pid, "months": months,
           "package": next(x["label"] for x in PACKAGES if x["months"] == months), "slots": slots,
           "start": start, "expiry": expiry, "total_meals": sub_total_meals(months, slots),
           "price": sub_price(p, months, slots), "purchased_at": now(), "status": "Active", "pay_choice": pay}
    D()["subs"].append(sub)
    if pay == PAY_NOW:
        add_payment(D(), pid=pid, cid=cid, ref_id=sub["id"], ref_type="Subscription", amount=sub["price"],
                    method="UPI (simulated)", at=now())
    n = schedule_plan_meals(sub)
    log(pid, "🔁", f"{cust(cid)['name']} subscribed: {sub['package']} · {' + '.join(slots)}")
    flash("success", f"Subscription activated — {sub['id']}",
          f"<b>{sub['package']}</b> with {_html.escape(p['name'])} · {' + '.join(slots)} · "
          f"valid {start:%d %b %Y} → {expiry:%d %b %Y} · {sub['total_meals']} meals · ₹{sub['price']:,} "
          f"({'paid — simulated UPI' if pay == PAY_NOW else 'payment pending'}). "
          f"{n} upcoming meal(s) scheduled.")
    st.session_state.cpage = "Dashboard"


def cb_request_skip(oid):
    st.session_state.skip_pending = oid


def cb_cancel_skip():
    st.session_state.skip_pending = None


def cb_confirm_skip(oid):
    st.session_state.skip_pending = None
    o = find_order(oid)
    if o is None or o["customer_id"] != st.session_state.cid:
        flash("error", "Order not found")
        return
    if o["status"] == "Skipped":
        flash("warning", "Already skipped", f"{oid} was skipped earlier — nothing changed.")
        return
    p = prov(o["provider_id"])
    if o["status"] != "Confirmed":
        flash("error", "Can't skip this meal", f"The kitchen has already marked it <b>{o['status']}</b>.")
        return
    if o["date"] < today() or now() >= cutoff_dt(p, o["date"], o["slot"]):
        flash("error", "Skip cutoff has passed",
              f"Skips for this {o['slot'].lower()} closed at {cutoff_dt(p, o['date'], o['slot']):%a %d %b, %H:%M}.")
        return
    ok, why = set_status(o, "Skipped", "Customer")
    if not ok:
        flash("error", "Can't skip", why)
        return
    log(p["id"], "⏭️", f"{cust(o['customer_id'])['name']} skipped {o['slot'].lower()} on {o['date']:%a %d %b}")
    extra = ("The meal stays in your plan balance." if o["order_type"] == "Subscription" else
             "Your simulated UPI payment has been refunded." if o["pay_mode"] == PAY_NOW else "You won't be charged.")
    flash("success", "Meal skipped",
          f"{o['slot']} on {o['date']:%a %d %b} from {_html.escape(p['name'])} ({oid}) is now <b>Skipped</b>. "
          f"The kitchen's preparation count has been updated. {extra}")


def cb_pay_due(ref_id, by="Customer"):
    idx = payment_index(D())
    row = idx.get(ref_id)
    if not row or row["outstanding"] <= 0:
        flash("warning", "Nothing to pay", f"{ref_id} has no outstanding amount.")
        return
    method = "UPI (simulated)" if by == "Customer" else st.session_state.get("rec_method", "Cash")
    add_payment(D(), pid=row["provider_id"], cid=row["customer_id"], ref_id=ref_id,
                ref_type="Subscription" if row["kind"] == "Subscription" else "Order",
                amount=row["outstanding"], method=method, at=now())
    log(row["provider_id"], "💰", f"Payment ₹{row['outstanding']:,} recorded for {ref_id}")
    flash("success", "Payment recorded (simulated)",
          f"₹{row['outstanding']:,} for {ref_id} · {method}. No real money was moved.")


def cb_save_profile():
    c = D()["customers"][st.session_state.cid]
    name = (st.session_state.get("pf_name") or "").strip()
    phone = (st.session_state.get("pf_phone") or "").strip()
    addr = (st.session_state.get("pf_addr") or "").strip()
    if not name or not phone or not addr:
        flash("error", "Profile not saved", "Name, phone and delivery address are required.")
        return
    c.update({"name": name, "phone": phone, "address": addr,
              "email": (st.session_state.get("pf_email") or "").strip(),
              "locality": st.session_state.get("pf_loc", c["locality"]),
              "diet": st.session_state.get("pf_diet", c["diet"]),
              "default_pay": st.session_state.get("pf_pay", c["default_pay"])})
    flash("success", "Profile saved", "New orders will use these delivery details.")


# ---------- callbacks: owner ----------

def cb_kitchen():
    st.session_state.pid = st.session_state.kitchen_w
    st.session_state.edit_item = None
    clear_keys("kp_", "ni_", "ei_")


def cb_status(oid, new, collect_cash=False):
    o = find_order(oid)
    if o is None:
        return
    ok, why = set_status(o, new, "Kitchen")
    if not ok:
        flash("error", "Status not changed", why)
        return
    if collect_cash and o["order_type"] == "One-day":
        out = payment_index(D()).get(oid, {}).get("outstanding", 0)
        if out > 0:
            add_payment(D(), pid=o["provider_id"], cid=o["customer_id"], ref_id=oid, ref_type="Order",
                        amount=out, method="Cash", at=now())
    log(o["provider_id"], {"Preparing": "👩‍🍳", "Prepared": "✅", "Out for delivery": "🛵", "Delivered": "📦",
                           "Skipped": "⏭️", "Cancelled": "✖️"}.get(new, "•"),
        f"{cust(o['customer_id'])['name']}'s {o['slot'].lower()} → {new}")
    st.toast(f"{oid} → {new}", icon="✅")


def cb_batch(pid, day_iso, slot, meal, frm, to):
    day = date.fromisoformat(day_iso)
    n = 0
    for o in D()["orders"]:
        if (o["provider_id"] == pid and o["date"] == day and o["slot"] == slot and o["meal_name"] == meal
                and o["status"] == frm):
            if set_status(o, to, "Kitchen")[0]:
                n += o["qty"]
    if n:
        log(pid, "👩‍🍳", f"{n} × {meal} → {to}")
        flash("success", f"{n} tiffin(s) of {meal} marked {to}")


def menu_entry(pid: str, day: date) -> dict:
    return D()["menus"].setdefault(mkey(pid, day), {"draft": [], "published": None, "published_at": None})


def cb_add_item(pid, day_iso):
    day = date.fromisoformat(day_iso)
    name = (st.session_state.get("ni_name") or "").strip()
    desc = (st.session_state.get("ni_desc") or "").strip()
    slot = st.session_state.get("ni_slot")
    price = st.session_state.get("ni_price") or 0
    errs = []
    if not name:
        errs.append("Enter a meal name.")
    if slot not in prov(pid)["slots"]:
        errs.append("Choose lunch or dinner (only the slots your kitchen serves).")
    if not 0 < price <= 1000:
        errs.append("Price must be between ₹1 and ₹1,000.")
    if any(i["name"].lower() == name.lower() and i["slot"] == slot for i in menu_entry(pid, day)["draft"]):
        errs.append(f"'{name}' is already on the {slot} menu.")
    if errs:
        flash("error", "Item not added", "<br>".join(_html.escape(e) for e in errs))
        return
    menu_entry(pid, day)["draft"].append({"id": new_id(D(), "item"), "slot": slot, "name": name,
                                          "desc": desc, "price": int(price)})
    for k in ("ni_name", "ni_desc"):
        st.session_state[k] = ""
    flash("success", f"Added '{name}' to the {slot.lower()} draft", "Publish the menu to show it to customers.")


def cb_edit_item(item_id):
    st.session_state.edit_item = item_id


def cb_save_item(pid, day_iso, item_id):
    entry = menu_entry(pid, date.fromisoformat(day_iso))
    item = next((i for i in entry["draft"] if i["id"] == item_id), None)
    if item is None:
        return
    name = (st.session_state.get(f"ei_name_{item_id}") or "").strip()
    price = st.session_state.get(f"ei_price_{item_id}") or 0
    slot = st.session_state.get(f"ei_slot_{item_id}", item["slot"])
    if not name or not 0 < price <= 1000:
        flash("error", "Item not saved", "Name is required and price must be between ₹1 and ₹1,000.")
        return
    item.update({"name": name, "desc": (st.session_state.get(f"ei_desc_{item_id}") or "").strip(),
                 "price": int(price), "slot": slot})
    st.session_state.edit_item = None
    flash("success", f"Updated '{name}' in the draft", "Publish to show the change to customers.")


def cb_delete_item(pid, day_iso, item_id):
    entry = menu_entry(pid, date.fromisoformat(day_iso))
    entry["draft"] = [i for i in entry["draft"] if i["id"] != item_id]
    st.session_state.edit_item = None
    flash("success", "Item removed from the draft", "Publish to update the customer menu.")


def cb_copy_menu(pid, day_iso, from_iso):
    entry = menu_entry(pid, date.fromisoformat(day_iso))
    src = D()["menus"].get(mkey(pid, date.fromisoformat(from_iso)))
    if not src or not (src["published"] or src["draft"]):
        flash("warning", "Nothing to copy")
        return
    entry["draft"] = [dict(i, id=new_id(D(), "item")) for i in (src["published"] or src["draft"])]
    flash("success", f"Copied {len(entry['draft'])} items into the draft", "Edit anything that changes, then publish.")


def cb_discard_draft(pid, day_iso):
    entry = menu_entry(pid, date.fromisoformat(day_iso))
    entry["draft"] = deepcopy(entry["published"] or [])
    st.session_state.edit_item = None
    flash("success", "Draft changes discarded")


def cb_publish(pid, day_iso):
    day = date.fromisoformat(day_iso)
    entry = menu_entry(pid, day)
    if not entry["draft"]:
        flash("error", "Menu not published", "Add at least one item first.")
        return
    entry["published"] = deepcopy(entry["draft"])
    entry["published_at"] = now()
    st.session_state.edit_item = None
    missing = [s for s in prov(pid)["slots"] if not any(i["slot"] == s for i in entry["draft"])]
    log(pid, "📝", f"Menu published for {day:%a %d %b} ({len(entry['draft'])} items)")
    flash("success", f"Menu published for {day:%a %d %b}",
          "Customers see it now in Discover and on your kitchen page."
          + (f" Note: no {', '.join(missing).lower()} items — customers can't order that meal." if missing else ""))


def cb_save_kitchen(pid):
    p = prov(pid)
    g = st.session_state.get
    slots = [s for s in SLOTS if s in (g("kp_slots") or [])]
    errs = []
    if len((g("kp_desc") or "").strip()) < 20:
        errs.append("Description should be at least 20 characters.")
    if not (g("kp_cuisine") or "").strip():
        errs.append("Enter a cuisine.")
    if not slots:
        errs.append("Serve at least one meal (lunch or dinner).")
    if not (g("kp_phone") or "").strip():
        errs.append("Enter a contact number.")
    if not g("kp_delivers"):
        errs.append("Choose at least one delivery locality.")
    for s in slots:
        if not 0 < (g(f"kp_price_{s}") or 0) <= 1000:
            errs.append(f"{s} price must be between ₹1 and ₹1,000.")
    if errs:
        flash("error", "Profile not saved", "<br>".join(_html.escape(e) for e in errs))
        return
    p.update({
        "description": g("kp_desc").strip(), "locality": g("kp_loc"), "cuisine": g("kp_cuisine").strip(),
        "diet": g("kp_diet"), "slots": slots, "phone": g("kp_phone").strip(), "email": (g("kp_email") or "").strip(),
        "delivers_to": list(g("kp_delivers")), "accepting_orders": bool(g("kp_orders")),
        "accepting_subs": bool(g("kp_subs")), "capacity": int(g("kp_cap")), "cutoff_hours": int(g("kp_cutoff")),
    })
    for s in SLOTS:
        if s in slots:
            p["prices"][s] = int(g(f"kp_price_{s}"))
    log(pid, "🏠", "Kitchen profile updated")
    flash("success", "Kitchen profile saved", "Customers see the changes immediately in Discover and on your page.")


# =============================================================================
# 5. STYLING & REUSABLE UI
# =============================================================================

CSS = """
<style>
:root{
  --bg:#FAF7F2; --card:#FFFFFF; --sage:#EEF2EA; --sage-2:#DCE6D6; --sage-3:#C6D5BF;
  --forest:#1F4D3A; --forest-2:#2B6A4F; --terra:#B5603F; --terra-2:#94492C; --terra-soft:#F6E6DC;
  --ink:#1D2A23; --muted:#5E6A63; --line:#E8E2D7;
  --shadow:0 1px 2px rgba(31,77,58,.05), 0 6px 20px rgba(31,77,58,.06);
  --serif:"Iowan Old Style","Palatino Linotype",Palatino,"Book Antiqua",Georgia,serif;
  --sans:ui-sans-serif,-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;
}
html, body, .stApp, button, input, textarea, select { font-family: var(--sans); }
.stApp { background: var(--bg); color: var(--ink); }
#MainMenu, footer, .stDeployButton, [data-testid="stToolbarActions"], [data-testid="stDecoration"],
[data-testid="stAppDeployButton"] { display:none !important; }
header[data-testid="stHeader"] { background: transparent; }
.block-container { padding-top: 2rem; padding-bottom: 3rem; max-width: 1200px; }

/* sidebar */
[data-testid="stSidebar"] { background: var(--forest); }
[data-testid="stSidebar"] * { color:#EEF2EA; }
[data-testid="stSidebar"] .stButton button { width:100%; border-radius:12px; background:transparent;
  border:1px solid transparent; color:#E8EFE5; font-weight:500; padding:.5rem .8rem; box-shadow:none; }
[data-testid="stSidebar"] .stButton button > div { justify-content:flex-start; width:100%; }
[data-testid="stSidebar"] .stButton button:hover { background:rgba(255,255,255,.08); border-color:rgba(255,255,255,.12); }
[data-testid="stSidebar"] .stButton button[kind="primary"] { background:var(--sage); border-color:var(--sage); }
[data-testid="stSidebar"] .stButton button[kind="primary"] * { color:var(--forest) !important; font-weight:700; }
[data-testid="stSidebar"] [data-testid="stPopover"] button { background:transparent; border:1px solid rgba(255,255,255,.2); border-radius:12px; }
[data-testid="stSidebar"] [data-testid="stSelectbox"] input,
[data-testid="stSidebar"] [data-testid="stSelectbox"] button,
[data-testid="stSidebar"] [data-testid="stSelectbox"] svg,
[data-testid="stSidebar"] [data-baseweb="select"] * { color:var(--ink) !important; -webkit-text-fill-color:var(--ink) !important; fill:var(--ink) !important; opacity:1 !important; }
[data-testid="stSidebar"] [data-testid="stSelectbox"] [role="group"],
[data-testid="stSidebar"] [data-baseweb="select"] > div { background:#FAF7F2 !important; border-color:transparent; }
[data-testid="stSidebar"] [data-testid="stSlider"] [data-testid="stThumbValue"] { color:#fff !important; }
[data-testid="stSidebar"] hr { border-color: rgba(255,255,255,.15); }
.sb-brand { display:flex; align-items:center; gap:.6rem; margin:.1rem 0 1rem; }
.sb-brand .logo { width:40px; height:40px; border-radius:12px; background:var(--sage); display:grid; place-items:center; font-size:1.3rem; }
.sb-brand .name { font-family:var(--serif); font-size:1.15rem; font-weight:700; line-height:1.1; }
.sb-brand .sub { font-size:.7rem; opacity:.75; letter-spacing:.08em; text-transform:uppercase; }
.sb-box { background:rgba(255,255,255,.07); border:1px solid rgba(255,255,255,.12); border-radius:14px; padding:.65rem .8rem; margin-bottom:.8rem; font-size:.84rem; }
.sb-label { font-size:.68rem; letter-spacing:.1em; text-transform:uppercase; opacity:.65; margin:.4rem 0 .3rem .2rem; }

/* buttons */
.stButton button, .stFormSubmitButton button, .stDownloadButton button { border-radius:12px; font-weight:600; }
.stDownloadButton button { background:var(--forest); color:#fff; border-color:var(--forest); }
.stDownloadButton button * { color:#fff !important; }
.stDownloadButton button:hover { background:var(--forest-2); border-color:var(--forest-2); }
[class*="st-key-cta_"] button { background:var(--terra) !important; border-color:var(--terra) !important;
  padding:.7rem 1rem; box-shadow:0 6px 16px rgba(181,96,63,.22); }
[class*="st-key-cta_"] button p { color:#fff !important; font-weight:700; }
[class*="st-key-cta_"] button:hover { background:var(--terra-2) !important; }
[class*="st-key-cta_"] button:disabled { background:#EFE5DC !important; border-color:#EFE5DC !important; box-shadow:none; }
[class*="st-key-cta_"] button:disabled p { color:#A08B7C !important; }

/* card shells — keyed containers */
[class*="st-key-card_"], [class*="st-key-role_"] {
  background:var(--card); border:1px solid var(--line); border-radius:18px; padding:1.1rem 1.2rem 1.15rem; box-shadow:var(--shadow);
}
[class*="st-key-row_"] { background:var(--card); border:1px solid var(--line); border-radius:14px; padding:.75rem 1rem .8rem; }
[class*="st-key-role_"] { padding:1.5rem 1.6rem; }
[class*="st-key-soft_"] { background:var(--sage); border:1px solid var(--sage-2); border-radius:16px; padding:.9rem 1rem; }
[class*="st-key-confirm_"] { background:var(--terra-soft); border:1px solid #EBC7B3; border-radius:16px; padding:1rem 1.1rem; }
[class*="st-key-sel_"] { background:#FFFDF8; border:2px solid var(--terra); border-radius:14px; padding:.75rem 1rem .8rem; }

/* text */
.eyebrow { font-size:.72rem; font-weight:700; letter-spacing:.11em; text-transform:uppercase; color:var(--terra); margin-bottom:.2rem; }
h1.ptitle, .ptitle { font-family:var(--serif) !important; font-size:clamp(1.55rem,2.4vw,2.05rem) !important; font-weight:700 !important;
  color:var(--ink); line-height:1.15 !important; margin:0 !important; padding:0 !important; }
.psub { color:var(--muted); margin:.35rem 0 1.1rem; font-size:.97rem; }
.h2 { font-family:var(--serif); font-size:1.25rem; font-weight:700; color:var(--ink); margin:.2rem 0 .5rem; }
.muted { color:var(--muted); font-size:.88rem; }
.small { font-size:.8rem; color:var(--muted); line-height:1.45; }

.badge { display:inline-flex; align-items:center; gap:.25rem; padding:.16rem .58rem; border-radius:999px; font-size:.74rem; font-weight:650; white-space:nowrap; }
.chip { display:inline-flex; align-items:center; gap:.3rem; padding:.18rem .58rem; border-radius:999px; font-size:.76rem; background:var(--sage); color:var(--forest); font-weight:600; margin:0 .25rem .25rem 0; white-space:nowrap; }
.chip.terra { background:var(--terra-soft); color:var(--terra-2); }
.chip.grey { background:#F1EDE6; color:#655F55; }
.chip.red { background:#F5E0DC; color:#8A2E24; }

.pc-head { display:flex; gap:.85rem; align-items:flex-start; }
.pc-icon { flex:0 0 auto; width:52px; height:52px; border-radius:15px; background:var(--sage); display:grid; place-items:center; font-size:1.6rem; }
.pc-name { font-family:var(--serif); font-size:1.18rem; font-weight:700; line-height:1.2; color:var(--ink); }
.pc-meta { font-size:.83rem; color:var(--muted); margin-top:.12rem; }
.pc-price { margin-left:auto; text-align:right; white-space:nowrap; }
.pc-price b { font-size:1.12rem; color:var(--forest); }
.pc-price span { display:block; font-size:.7rem; color:var(--muted); }
.pc-desc { color:#3E4A43; font-size:.89rem; margin:.65rem 0 .5rem; line-height:1.45; }

.stat { background:var(--card); border:1px solid var(--line); border-radius:16px; padding:.85rem 1rem; box-shadow:var(--shadow); height:100%; }
.stat .lbl { font-size:.72rem; color:var(--muted); font-weight:650; text-transform:uppercase; letter-spacing:.05em; }
.stat .val { font-family:var(--serif); font-size:1.75rem; font-weight:700; color:var(--forest); line-height:1.15; margin-top:.1rem; }
.stat .hint { font-size:.76rem; color:var(--muted); margin-top:.1rem; }
.stat.terra .val { color:var(--terra); }
.stat .ic { float:right; font-size:1.15rem; }

.callout { border-radius:14px; padding:.8rem 1rem; margin-bottom:.9rem; border:1px solid; display:flex; gap:.7rem; align-items:flex-start; }
.callout .ci { font-size:1.1rem; line-height:1.35; }
.callout .ct { font-weight:700; }
.callout .cb { font-size:.89rem; }
.callout.success { background:#E9F2EA; border-color:#BFD8C3; color:#1D4A31; }
.callout.warning { background:var(--terra-soft); border-color:#EBC7B3; color:#7A3A1F; }
.callout.error { background:#F8E4E0; border-color:#EBC0BA; color:#7D2A20; }
.callout.info { background:var(--sage); border-color:var(--sage-2); color:var(--forest); }

.mi { display:flex; justify-content:space-between; gap:.8rem; }
.mi .n { font-weight:700; color:var(--ink); }
.mi .d { font-size:.83rem; color:var(--muted); }
.mi .p { font-weight:700; color:var(--forest); white-space:nowrap; }

.empty { text-align:center; padding:1.8rem 1rem; border:1.5px dashed var(--sage-3); border-radius:18px; background:#FDFCF8; color:var(--muted); }
.empty .ei { font-size:2rem; }
.empty .et { font-family:var(--serif); font-size:1.1rem; color:var(--ink); font-weight:700; margin:.25rem 0 .15rem; }

.track { display:flex; margin:.55rem 0 .1rem; }
.track .s { flex:1; display:flex; flex-direction:column; align-items:center; font-size:.66rem; color:var(--muted); text-align:center; position:relative; }
.track .dot { width:13px; height:13px; border-radius:50%; background:#E4DFD5; border:2px solid #fff; box-shadow:0 0 0 1px #E4DFD5; margin-bottom:.22rem; z-index:1; }
.track .s.on .dot { background:var(--forest-2); box-shadow:0 0 0 1px var(--forest-2); }
.track .s.on { color:var(--forest); font-weight:650; }
.track .s:not(:first-child)::before { content:""; position:absolute; top:6px; right:50%; width:100%; height:2px; background:#E4DFD5; }
.track .s.on:not(:first-child)::before { background:var(--forest-2); }

.feed { display:flex; gap:.6rem; padding:.5rem 0; border-bottom:1px solid #F0EBE2; font-size:.88rem; }
.feed:last-child { border-bottom:none; }
.feed .t { color:var(--muted); font-size:.76rem; min-width:2.8rem; padding-top:.1rem; }

.hero { text-align:center; padding:1.2rem 0 1rem; }
.hero .logo { width:74px; height:74px; margin:0 auto .8rem; border-radius:22px; background:var(--forest); display:grid; place-items:center; font-size:2.2rem; box-shadow:0 10px 28px rgba(31,77,58,.25); }
.hero h1 { font-family:var(--serif); font-size:clamp(2.1rem,5vw,3.2rem); margin:0; color:var(--forest); font-weight:700; }
.hero .tag { font-family:var(--serif); font-size:clamp(1.1rem,2.2vw,1.4rem); color:var(--terra); font-style:italic; margin:.3rem 0 .7rem; }
.hero .desc { max-width:640px; margin:0 auto; color:var(--muted); font-size:1rem; line-height:1.55; }
.demo-label { display:inline-block; background:var(--terra-soft); color:var(--terra-2); border:1px solid #EBC7B3; border-radius:999px; padding:.2rem .75rem; font-size:.7rem; font-weight:700; letter-spacing:.08em; text-transform:uppercase; margin-bottom:.9rem; }
.role-ic { width:54px; height:54px; border-radius:16px; display:grid; place-items:center; font-size:1.7rem; background:var(--sage); margin-bottom:.7rem; }
.role-t { font-family:var(--serif); font-size:1.4rem; font-weight:700; }
.role-l { list-style:none; padding:0; margin:.6rem 0 .9rem; font-size:.88rem; color:#3E4A43; }
.role-l li { padding:.18rem 0; }
.role-l li::before { content:"✓"; color:var(--forest-2); font-weight:800; margin-right:.5rem; }

.tbl { width:100%; border-collapse:collapse; font-size:.88rem; }
.tbl th { text-align:left; font-size:.72rem; text-transform:uppercase; letter-spacing:.05em; color:var(--muted); padding:.45rem .5rem; border-bottom:1px solid var(--line); }
.tbl td { padding:.5rem .5rem; border-bottom:1px solid #F0EBE2; }
.tbl tr.tot td { font-weight:700; border-top:2px solid var(--line); border-bottom:none; }
.tbl td.num, .tbl th.num { text-align:right; }

.pkg { background:var(--card); border:1px solid var(--line); border-radius:14px; padding:.75rem .8rem; height:100%; }
.pkg.on { border:2px solid var(--forest-2); background:#FBFDFB; }
.pkg .m { font-weight:700; }
.pkg .pr { font-family:var(--serif); font-size:1.25rem; font-weight:700; color:var(--forest); margin:.2rem 0; }

[data-testid="stDataFrame"] { border:1px solid var(--line); border-radius:12px; overflow:hidden; }
[data-testid="stForm"] { background:var(--card); border:1px solid var(--line); border-radius:18px; box-shadow:var(--shadow); }
[data-testid="stExpander"] details { background:var(--card); border-radius:14px; }
.stTabs [data-baseweb="tab"] { font-weight:600; }

@media (max-width:640px){
  .block-container { padding-left:1rem; padding-right:1rem; padding-top:1.1rem; }
  .stat .val { font-size:1.45rem; }
  [class*="st-key-role_"] { padding:1.1rem; }
}
</style>
"""


def html(markup: str) -> None:
    """Render trusted HTML. Lines are stripped so Markdown never treats indentation as a code block."""
    st.markdown(" ".join(line.strip() for line in markup.splitlines()), unsafe_allow_html=True)


def esc(x) -> str:
    return _html.escape(str(x if x is not None else ""))


def rupees(x) -> str:
    x = int(round(x or 0))
    return f"−₹{abs(x):,}" if x < 0 else f"₹{x:,}"


def fmt_day(d: date, rel: bool = True) -> str:
    base = f"{d:%a} {d.day} {d:%b}"
    if rel:
        delta = (d - today()).days
        if delta in (-1, 0, 1):
            return f"{['Yesterday', 'Today', 'Tomorrow'][delta + 1]} · {base}"
    return base


def page_header(eyebrow: str, title: str, sub: str = "") -> None:
    html(f'<div class="eyebrow">{esc(eyebrow)}</div><h1 class="ptitle">{esc(title)}</h1>'
         + (f'<p class="psub">{esc(sub)}</p>' if sub else '<div style="height:.9rem"></div>'))


def callout(kind: str, title: str, body: str = "") -> None:
    icon = {"success": "✅", "warning": "⚠️", "error": "⛔", "info": "💡"}[kind]
    html(f'<div class="callout {kind}"><div class="ci">{icon}</div><div><div class="ct">{esc(title)}</div>'
         + (f'<div class="cb">{body}</div>' if body else "") + "</div></div>")


def show_flash() -> None:
    msgs, st.session_state.flash = st.session_state.flash, []
    for kind, title, body in msgs:
        callout(kind, title, body)


def badge(status: str) -> str:
    bg, fg = STATUS_STYLE.get(status, ("#EEE", "#333"))
    return f'<span class="badge" style="background:{bg};color:{fg}">● {esc(status)}</span>'


def stat(label, value, hint="", icon="", terra=False) -> None:
    html(f'<div class="stat{" terra" if terra else ""}"><span class="ic">{icon}</span><div class="lbl">{esc(label)}</div>'
         f'<div class="val">{esc(value)}</div><div class="hint">{esc(hint)}</div></div>')


def stat_row(items: list[tuple]) -> None:
    cols = st.columns(len(items))
    for col, it in zip(cols, items):
        with col:
            stat(*it)
    st.write("")


def empty(icon, title, body) -> None:
    html(f'<div class="empty"><div class="ei">{icon}</div><div class="et">{esc(title)}</div><div>{esc(body)}</div></div>')


def tracker(status: str) -> str:
    if status not in FLOW:
        return ""
    i = FLOW.index(status)
    return '<div class="track">' + "".join(
        f'<div class="s{" on" if k <= i else ""}"><div class="dot"></div>{esc(s)}</div>' for k, s in enumerate(FLOW)
    ) + "</div>"


def diet_chip(diet: str) -> str:
    if diet == "Veg":
        return '<span class="chip" style="background:#E5F1E5;color:#2E7D32">🟢 Veg</span>'
    if diet == "Non-Veg":
        return '<span class="chip red">🔴 Non-Veg</span>'
    return '<span class="chip terra">🟢🔴 Veg &amp; Non-Veg</span>'


def money_df(df: pd.DataFrame, money_cols: list[str], date_cols: list[str] = (), height=None):
    cfg = {c: st.column_config.NumberColumn(format="₹%d") for c in money_cols}
    for c in date_cols:
        cfg[c] = st.column_config.DateColumn(format="ddd D MMM YYYY")
    extra = {"height": height} if height else {}
    st.dataframe(df, hide_index=True, width="stretch", column_config=cfg, **extra)


def sidebar_common(role_label: str, who: str, sub: str) -> None:
    with st.sidebar:
        html(f'<div class="sb-brand"><div class="logo">🍱</div><div><div class="name">Tiffin Connect Pro</div>'
             f'<div class="sub">{esc(role_label)} · demo access</div></div></div>'
             f'<div class="sb-box"><b style="font-size:.95rem">{esc(who)}</b><br><span style="opacity:.75">{esc(sub)}</span></div>')


def sidebar_footer() -> None:
    with st.sidebar:
        st.divider()
        html(f'<div class="sb-label">🕒 Demo clock</div><div class="sb-box" style="margin-bottom:.3rem">'
             f'<b>{DEMO_TODAY:%A, %d %B %Y}</b><br><span style="opacity:.75">Fixed demo date · change the time to test cutoffs</span></div>')
        st.session_state.clock_w = st.session_state.clock
        st.selectbox("Demo time", DEMO_TIMES, key="clock_w", on_change=cb_clock,
                     format_func=lambda x: f"🕒 Demo time {x}")
        st.divider()
        st.button("↩  Switch role / account", key="sb_switch", on_click=cb_role, args=(None,), width="stretch")
        with st.popover("⟲  Reset demo data", width="stretch"):
            st.write("Restore all sample records and the demo clock?")
            st.button("Yes, reset everything", key="sb_reset", type="primary", on_click=cb_reset)
        html('<div class="small" style="margin-top:.7rem;color:#DCE6D6;opacity:.75">Prototype · fictional data · '
             'stored only in this browser session</div>')


# =============================================================================
# 6. LANDING
# =============================================================================

def render_landing() -> None:
    show_flash()
    html("""
      <div class="hero">
        <div class="demo-label">Prototype 2 · Demonstration access</div>
        <div class="logo">🍱</div>
        <h1>Tiffin Connect Pro</h1>
        <div class="tag">Homely meals, hassle-free.</div>
        <p class="desc">One place for Pune's home tiffin kitchens and the students, professionals and people living
        alone who rely on them — menus, subscriptions, skips, deliveries, payments and monthly reports.</p>
      </div>
    """)
    _, c1, c2, _ = st.columns([0.35, 3, 3, 0.35], gap="large")
    with c1, st.container(key="role_customer"):
        html("""<div class="role-ic">🧑‍🎓</div><div class="role-t">Continue as Customer</div>
                <ul class="role-l"><li>Find home kitchens by locality, price and meal</li>
                <li>Order today's meal or subscribe for 1–12 months</li><li>Skip a meal before the cutoff</li></ul>""")
        ids = ["C1", "C3", "C7", "C9"]
        st.selectbox("Demo customer account", ids, key="land_cust",
                     format_func=lambda c: f"{cust(c)['name']} — {cust(c)['locality']}")
        st.button("Continue as Customer  →", key="go_customer", type="primary", on_click=cb_role,
                  args=("customer",), width="stretch")
    with c2, st.container(key="role_owner"):
        html("""<div class="role-ic" style="background:var(--terra-soft)">👩‍🍳</div><div class="role-t">Continue as Tiffin Owner</div>
                <ul class="role-l"><li>Publish daily menus and manage your profile</li>
                <li>Know exactly how many meals to cook</li><li>Track deliveries, payments and monthly reports</li></ul>""")
        st.selectbox("Demo kitchen account", list(D()["providers"]), key="land_owner",
                     format_func=lambda p: f"{prov(p)['name']} — {prov(p)['owner']}")
        st.button("Continue as Tiffin Owner  →", key="go_owner", type="primary", on_click=cb_role,
                  args=("owner",), width="stretch")
    html(f'<p class="small" style="text-align:center;margin-top:1.4rem">Demo accounts only — there is no real login. '
         f'All kitchens, people, ratings and payments are fictional. The app runs on a fixed demo date '
         f'(<b>{DEMO_TODAY:%a %d %b %Y}</b>). Data is kept only for this browser session.</p>')


# =============================================================================
# 7. CUSTOMER
# =============================================================================

CNAV = [("Dashboard", "🏠  My dashboard"), ("Discover", "🔍  Discover kitchens"),
        ("Subscriptions", "🔁  Subscriptions"), ("Skip", "⏭️  Skip a meal"), ("Profile", "👤  Profile & settings")]


def render_customer() -> None:
    c = me()
    sidebar_common("Customer", c["name"], f"📍 {c['locality']}, Pune")
    with st.sidebar:
        html('<div class="sb-label">Menu</div>')
        cur = st.session_state.cpage
        for page, label in CNAV:
            on = cur == page or (cur == "Kitchen" and page == "Discover")
            st.button(label, key=f"cn_{page}", type="primary" if on else "secondary", on_click=cb_cnav,
                      args=(page,), width="stretch")
    sidebar_footer()
    show_flash()
    {"Dashboard": c_dashboard, "Discover": c_discover, "Kitchen": c_kitchen, "Subscriptions": c_subscriptions,
     "Skip": c_skip, "Profile": c_profile}.get(st.session_state.cpage, c_dashboard)()


def my_orders() -> list[dict]:
    return [o for o in D()["orders"] if o["customer_id"] == st.session_state.cid]


def my_subs() -> list[dict]:
    return [s for s in D()["subs"] if s["customer_id"] == st.session_state.cid]


def c_dashboard() -> None:
    c = me()
    page_header(f"Welcome back, {c['name'].split()[0]}", "Your tiffin at a glance",
                f"{fmt_day(today())} · demo time {st.session_state.clock}")
    orders, subs = my_orders(), my_subs()
    active = [s for s in subs if sub_state(s) in ("Active", "Upcoming")]
    idx = payment_index(D())
    dues = [r for r in idx.values() if r["customer_id"] == c["id"] and r["outstanding"] > 0]
    upcoming = sorted([o for o in orders if o["date"] >= today() and o["status"] in ACTIVE],
                      key=lambda o: (o["date"], SLOTS.index(o["slot"])))
    main = active[0] if active else None
    stat_row([
        ("Active provider", prov(main["provider_id"])["name"] if main else "—",
         f"Plan {main['id']}" if main else "No active plan", "🏠"),
        ("Plan expires", f"{main['expiry']:%d %b %Y}" if main else "—",
         f"{(main['expiry'] - today()).days} days left" if main else "Subscribe to save up to 12%", "📅"),
        ("Meals remaining", sub_counts(main)["Remaining"] if main else 0,
         f"of {main['total_meals']} included" if main else "", "🍱"),
        ("Pending dues", rupees(sum(r["outstanding"] for r in dues)), f"{len(dues)} unpaid item(s)", "💳", bool(dues)),
    ])

    left, right = st.columns([1.35, 1], gap="large")
    with left:
        html('<div class="h2">Today\'s meals</div>')
        todays = [o for o in orders if o["date"] == today()]
        if not todays:
            empty("🍽️", "Nothing for today", "Order a one-day meal or activate a plan.")
            st.button("Discover kitchens →", key="cd_disc", on_click=cb_cnav, args=("Discover",))
        for o in sorted(todays, key=lambda o: SLOTS.index(o["slot"])):
            with st.container(key=f"row_today_{o['id']}"):
                html(f'<div style="display:flex;justify-content:space-between;gap:.5rem;flex-wrap:wrap">'
                     f'<div><b>{SLOT_ICON[o["slot"]]} {esc(o["meal_name"])}</b> × {o["qty"]}'
                     f'<div class="small">{esc(prov(o["provider_id"])["name"])} · {esc(o["order_type"])} · {esc(o["id"])}</div></div>'
                     f'{badge(o["status"])}</div>{tracker(o["status"])}')
        html('<div class="h2" style="margin-top:1rem">Upcoming meals</div>')
        later = [o for o in upcoming if o["date"] > today()]
        if not later:
            html('<p class="muted">No meals scheduled after today.</p>')
        for o in later:
            p = prov(o["provider_id"])
            html(f'<div class="feed"><div>{SLOT_ICON[o["slot"]]}</div><div style="flex:1"><b>{esc(fmt_day(o["date"]))} · {o["slot"]}</b>'
                 f'<div class="small">{esc(o["meal_name"])} · {esc(p["name"])} · skip before '
                 f'{cutoff_dt(p, o["date"], o["slot"]):%a %H:%M}</div></div>{badge(o["status"])}</div>')
        if any(o["status"] == "Confirmed" for o in upcoming):
            st.button("⏭️  Skip an upcoming meal", key="cd_skip", on_click=cb_cnav, args=("Skip",))
    with right:
        html('<div class="h2">Active subscription</div>')
        if active:
            for s in active:
                sub_card(s)
        else:
            empty("🔁", "No active plan", "Plans from 1 to 12 months — cheaper than ordering daily.")
            st.button("See subscription packages →", key="cd_subs", on_click=cb_cnav, args=("Subscriptions",))
        if dues:
            html('<div class="h2" style="margin-top:1rem">Pending dues</div>')
            for r in dues:
                with st.container(key=f"row_due_{r['ref_id']}"):
                    a, b = st.columns([2.2, 1], vertical_alignment="center")
                    a.markdown(f"**{rupees(r['outstanding'])}** · {r['ref_id']}  \n"
                               f"<span class='small'>{esc(r['desc'])} · {esc(prov(r['provider_id'])['name'])}</span>",
                               unsafe_allow_html=True)
                    b.button("Pay (demo)", key=f"paydue_{r['ref_id']}", on_click=cb_pay_due, args=(r["ref_id"],),
                             width="stretch")

    st.write("")
    t1, t2, t3 = st.tabs(["Recent orders", "Previous subscriptions", "Payment history"])
    with t1:
        if not orders:
            empty("🧾", "No orders yet", "Your orders will appear here.")
        else:
            rows = [{"Order ID": o["id"], "Meal date": o["date"], "Slot": o["slot"], "Kitchen": prov(o["provider_id"])["name"],
                     "Meal": o["meal_name"], "Qty": o["qty"], "Type": o["order_type"], "Amount": o["amount"],
                     "Payment": order_pay_status(o, idx), "Status": o["status"],
                     "Last update": f"{o['history'][-1]['at']:%d %b %H:%M} by {o['history'][-1]['by']}"}
                    for o in sorted(orders, key=lambda o: (o["date"], o["id"]), reverse=True)[:40]]
            money_df(pd.DataFrame(rows), ["Amount"], ["Meal date"], height=320)
            html('<p class="small">Showing the latest 40. Plan meals show ₹0 because they are covered by the subscription price.</p>')
    with t2:
        prev = [s for s in subs if sub_state(s) in ("Expired", "Cancelled")]
        if not prev:
            empty("📜", "No previous subscriptions", "Expired plans will be listed here.")
        else:
            money_df(pd.DataFrame([{"Plan ID": s["id"], "Kitchen": prov(s["provider_id"])["name"], "Package": s["package"],
                                    "Meals": " + ".join(s["slots"]), "Start": s["start"], "Expiry": s["expiry"],
                                    "Delivered": sub_counts(s)["Delivered"], "Price": s["price"],
                                    "Payment": idx[s["id"]]["status"], "Status": sub_state(s)} for s in prev]),
                     ["Price"], ["Start", "Expiry"])
    with t3:
        pays = sorted([p for p in D()["payments"] if p["customer_id"] == c["id"]], key=lambda p: p["at"], reverse=True)
        if not pays:
            empty("💳", "No payments yet", "Simulated payments will appear here.")
        else:
            money_df(pd.DataFrame([{"Payment ID": p["id"], "Date": p["at"].strftime("%d %b %Y, %H:%M"),
                                    "Kitchen": prov(p["provider_id"])["name"], "For": p["ref_id"], "Type": p["kind"],
                                    "Method": p["method"], "Amount": p["amount"]} for p in pays]), ["Amount"], height=300)
            html('<p class="small">All payments are simulated. Refunds appear as negative amounts.</p>')


def sub_card(s: dict) -> None:
    p, c = prov(s["provider_id"]), sub_counts(s)
    pay = payment_index(D())[s["id"]]
    used = c["Delivered"] + c["Scheduled"]
    pct = int(100 * used / s["total_meals"]) if s["total_meals"] else 0
    with st.container(key=f"card_sub_{s['id']}"):
        html(f"""
          <div class="pc-head"><div class="pc-icon">{p['icon']}</div>
            <div style="flex:1"><div class="pc-name">{esc(s['package'])} · {esc(' + '.join(s['slots']))}</div>
            <div class="pc-meta">{esc(p['name'])} · {esc(s['id'])} · {rupees(s['price'])}</div></div>
            {badge(sub_state(s))}</div>
          <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:.5rem;margin:.8rem 0 .55rem">
            <div><div class="small">Valid from</div><b>{s['start']:%d %b %Y}</b></div>
            <div><div class="small">Expires</div><b>{s['expiry']:%d %b %Y}</b></div>
            <div><div class="small">Meals remaining</div><b style="color:var(--terra);font-size:1.12rem">{c['Remaining']}</b>
              <span class="small">/ {s['total_meals']}</span></div></div>
          <div style="background:var(--sage);border-radius:99px;height:8px;overflow:hidden">
            <div style="width:{pct}%;background:var(--forest-2);height:8px"></div></div>
          <div class="small" style="margin-top:.35rem">{c['Delivered']} delivered · {c['Scheduled']} scheduled ·
            {c['Skipped']} skipped (not deducted) · Payment: {badge(pay['status'])}</div>
        """)
        if pay["outstanding"] > 0 and s["customer_id"] == st.session_state.get("cid") and st.session_state.role == "customer":
            st.button(f"Pay {rupees(pay['outstanding'])} now (simulated)", key=f"paysub_{s['id']}",
                      on_click=cb_pay_due, args=(s["id"],))


def provider_card(p: dict) -> None:
    c = me()
    tm = pub_menu(p["id"], today())
    price_from = min(p["prices"][s] for s in p["slots"])
    delivers = c["locality"] in p["delivers_to"]
    menu_chip = ('<span class="chip">📋 Today&#39;s menu published</span>' if tm
                 else '<span class="chip grey">🕒 Menu not published</span>')
    area_chip = (f'<span class="chip">🛵 Delivers to {esc(c["locality"])}</span>' if delivers
                 else f'<span class="chip red">Doesn&#39;t deliver to {esc(c["locality"])}</span>')
    with st.container(key=f"card_prov_{p['id']}"):
        html(f"""
          <div class="pc-head"><div class="pc-icon">{p['icon']}</div>
            <div><div class="pc-name">{esc(p['name'])}</div>
            <div class="pc-meta">📍 {esc(p['locality'])} · {esc(p['cuisine'])} · ⭐ {p['rating']} <span title="Demo rating">(demo)</span></div></div>
            <div class="pc-price"><b>from {rupees(price_from)}</b><span>per meal</span></div></div>
          <div class="pc-desc">{esc(p['description'])}</div>
          <div>{diet_chip(p['diet'])}{''.join(f'<span class="chip grey">{SLOT_ICON[s]} {s} {rupees(p["prices"][s])}</span>' for s in p['slots'])}</div>
          <div style="margin-top:.15rem">
            {menu_chip}
            {'<span class="chip">🔁 Subscriptions open</span>' if p['accepting_subs'] else '<span class="chip red">🔁 Subscriptions full</span>'}
            {area_chip}
            {'' if p['accepting_orders'] else '<span class="chip red">Not taking orders</span>'}
          </div>
        """)
        st.button("View kitchen & menu  →", key=f"open_{p['id']}", on_click=cb_open_provider, args=(p["id"],),
                  width="stretch")


def c_discover() -> None:
    page_header("Discover", "Home tiffin services near you",
                "Filter by locality, price and meal. Ratings are demo values, not verified reviews; no live GPS is used.")
    provs = list(D()["providers"].values())
    with st.container(key="soft_filters"):
        f1, f2, f3, f4 = st.columns([1.6, 1.4, 1.1, 1.1])
        with f1:
            locs = st.multiselect("Locality", LOCALITIES, key="f_loc", placeholder="All localities")
        with f2:
            pr = st.slider("Price per meal (₹)", 50, 200, (50, 200), step=10, key="f_price")
        with f3:
            meal = st.selectbox("Meal type", ["Any", "Lunch", "Dinner"], key="f_meal")
        with f4:
            food = st.selectbox("Food", ["Any", "Veg only", "Non-veg available"], key="f_food")
        g1, g2 = st.columns([1, 3])
        subs_only = g1.toggle("Subscriptions open", key="f_subs")
        near = g2.toggle(f"Delivers to {me()['locality']}", key="f_near")

    res = []
    for p in provs:
        served = [s for s in p["slots"] if meal in ("Any", s)]
        if not served:
            continue
        if locs and p["locality"] not in locs:
            continue
        if not any(pr[0] <= p["prices"][s] <= pr[1] for s in served):
            continue
        if food == "Veg only" and p["diet"] != "Veg":
            continue
        if food == "Non-veg available" and p["diet"] == "Veg":
            continue
        if subs_only and not p["accepting_subs"]:
            continue
        if near and me()["locality"] not in p["delivers_to"]:
            continue
        res.append(p)
    html(f'<p class="muted" style="margin:.6rem 0 .6rem">{len(res)} kitchen{"s" if len(res) != 1 else ""} found</p>')
    if not res:
        empty("🔎", "No kitchens match these filters", "Widen the price range or clear a filter.")
        return
    for i in range(0, len(res), 2):
        cols = st.columns(2, gap="medium")
        for col, p in zip(cols, res[i:i + 2]):
            with col:
                provider_card(p)
        st.write("")


def c_kitchen() -> None:
    pid = st.session_state.sel_provider
    if pid not in D()["providers"]:
        cb_cnav("Discover")
        st.rerun()
    p, c = prov(pid), me()
    st.button("←  All kitchens", key="k_back", on_click=cb_cnav, args=("Discover",))
    html(f"""
      <div style="display:flex;gap:1rem;align-items:center;margin:.5rem 0 .3rem;flex-wrap:wrap">
        <div class="pc-icon" style="width:68px;height:68px;font-size:2.1rem;border-radius:20px">{p['icon']}</div>
        <div style="flex:1;min-width:230px"><div class="eyebrow">{esc(p['cuisine'])} home kitchen · since {p['since']}</div>
          <h1 class="ptitle">{esc(p['name'])}</h1>
          <div class="pc-meta" style="font-size:.9rem">📍 {esc(p['locality'])}, Pune · ⭐ {p['rating']} ({p['reviews']} demo reviews) · run by {esc(p['owner'])}</div></div>
      </div>
      <p class="pc-desc" style="font-size:.97rem;max-width:860px">{esc(p['description'])}</p>
      <div>{diet_chip(p['diet'])}{''.join(f'<span class="chip grey">{SLOT_ICON[s]} {s} · {rupees(p["prices"][s])} · delivered by {SLOT_TIME[s]:%H:%M}</span>' for s in p['slots'])}
        <span class="chip grey">🛵 Delivers to {esc(', '.join(p['delivers_to']))}</span>
        <span class="chip grey">📞 {esc(p['phone'])}</span>
        <span class="chip terra">⏱️ Order/skip until {p['cutoff_hours']}h before delivery</span></div>
    """)
    if c["locality"] not in p["delivers_to"]:
        callout("warning", f"This kitchen doesn't deliver to {c['locality']}",
                "You can browse the menu, but ordering and subscribing are unavailable for your address.")
    if not p["accepting_orders"]:
        callout("info", "Not taking one-day orders right now", "Subscriptions may still be available below.")

    days = [today(), today() + timedelta(days=1)]
    ensure_valid(f"kday_{pid}", [d.isoformat() for d in days])
    day_iso = st.segmented_control("Menu for", [d.isoformat() for d in days], default=days[0].isoformat(),
                                   format_func=lambda x: fmt_day(date.fromisoformat(x)), key=f"kday_{pid}") or days[0].isoformat()
    day = date.fromisoformat(day_iso)
    menu = pub_menu(pid, day)
    entry = D()["menus"].get(mkey(pid, day))

    left, right = st.columns([1.5, 1], gap="large")
    with left:
        if not menu:
            empty("🕒", f"Menu for {fmt_day(day)} isn't published yet",
                  f"{p['owner'].split()[0]} usually publishes by the evening before. Check back later.")
        else:
            html(f'<p class="small">Published {entry["published_at"]:%a %d %b, %H:%M}</p>')
            sel = st.session_state.get(f"sel_{pid}")
            for slot in p["slots"]:
                items = [i for i in menu if i["slot"] == slot]
                ok, why = can_order(pid, c["id"], day, slot)
                cut = cutoff_dt(p, day, slot)
                html(f'<div class="h2">{SLOT_ICON[slot]} {slot} <span class="small" style="font-family:var(--sans);font-weight:400">'
                     f'· order by {cut:%H:%M} · {max(p["capacity"] - booked(pid, day, slot), 0)} tiffins left</span></div>')
                if not items:
                    html('<p class="muted">No items for this meal.</p>')
                    continue
                if not ok:
                    html(f'<p class="small" style="color:var(--terra-2)">⚠️ {esc(why)}</p>')
                for it in items:
                    is_sel = sel == (day_iso, slot, it["id"])
                    with st.container(key=f"{'sel' if is_sel else 'row'}_item_{it['id']}"):
                        a, b = st.columns([3.2, 1], vertical_alignment="center")
                        with a:
                            html(f'<div class="mi"><div><div class="n">{esc(it["name"])}</div>'
                                 f'<div class="d">{esc(it["desc"])}</div></div><div class="p">{rupees(it["price"])}</div></div>')
                        with b:
                            st.button("Selected ✓" if is_sel else "Choose", key=f"pick_{it['id']}", disabled=not ok or is_sel,
                                      on_click=cb_select_item, args=(pid, day_iso, slot, it["id"]), width="stretch")
                st.write("")
    with right:
        with st.container(key=f"card_order_{pid}"):
            order_panel(p)

    st.write("")
    html('<div class="eyebrow" style="margin-top:.6rem">Subscription packages</div>'
         f'<div class="h2">Get {esc(p["name"])} every day</div>')
    if not p["accepting_subs"]:
        callout("info", "Subscriptions are full this month", "You can still order one-day meals.")
    else:
        subscribe_form("ks", pid)


def order_panel(p: dict) -> None:
    pid = p["id"]
    html('<div class="eyebrow">One-day order</div><div class="h2">Your order</div>')
    last = st.session_state.get(f"last_{pid}")
    if last and find_order(last):
        o = find_order(last)
        callout("success", "Order placed — the kitchen can see it now",
                f"<b>{o['id']}</b> · {o['qty']} × {esc(o['meal_name'])} · {o['slot']} · {fmt_day(o['date'])} · "
                f"{rupees(o['amount'])} · {'paid (simulated UPI)' if o['pay_mode'] == PAY_NOW else 'pay on delivery'}")
    sel = st.session_state.get(f"sel_{pid}")
    if not sel:
        html('<p class="muted">Choose a meal from the menu to order it for one day.</p>')
        return
    day_iso, slot, item_id = sel
    day = date.fromisoformat(day_iso)
    item = next((i for i in (pub_menu(pid, day) or []) if i["id"] == item_id), None)
    if item is None:
        st.session_state.pop(f"sel_{pid}", None)
        callout("warning", "That meal is no longer on the menu")
        return
    html(f'<div class="mi" style="margin:.2rem 0 .6rem"><div><div class="n">{SLOT_ICON[slot]} {esc(item["name"])}</div>'
         f'<div class="d">{esc(fmt_day(day))} · {slot} · delivered by {SLOT_TIME[slot]:%H:%M}</div></div>'
         f'<div class="p">{rupees(item["price"])}</div></div>')
    qty = st.number_input("Tiffins", 1, 3, 1, key=f"oq_{pid}")
    pays = [PAY_NOW, PAY_LATER_ORDER]
    st.radio("Payment (simulated)", pays, key=f"op_{pid}",
             index=pays.index(me()["default_pay"]) if me().get("default_pay") in pays else 0)
    st.text_input("Delivery note (optional)", key=f"on_{pid}", max_chars=80, placeholder="e.g. Less spicy, call at gate")
    html(f'<div style="display:flex;justify-content:space-between;margin:.3rem 0"><span class="muted">Total</span>'
         f'<b style="font-size:1.1rem">{rupees(item["price"] * qty)}</b></div>'
         f'<p class="small">Deliver to {esc(me()["address"])}, {esc(me()["locality"])} · '
         f'skip free until {cutoff_dt(p, day, slot):%a %H:%M}</p>')
    ok, why = can_order(pid, me()["id"], day, slot)
    if not ok:
        callout("warning", "Can't order this meal", esc(why))
    with st.container(key=f"cta_order_{pid}"):
        st.button(f"🍱  Place order · {rupees(item['price'] * qty)}", key=f"place_{pid}", disabled=not ok,
                  on_click=cb_place_order, args=(pid,), width="stretch")


def disc_txt(pk: dict) -> str:
    return "No discount" if not pk["discount"] else f"Save {int(pk['discount'] * 100)}%"


def subscribe_form(prefix: str, fixed_pid: str | None = None) -> None:
    c = me()
    if fixed_pid:
        pid = fixed_pid
    else:
        opts = [p["id"] for p in D()["providers"].values() if p["accepting_subs"]]
        ensure_valid(f"{prefix}_pid", opts)
        pid = st.selectbox("Tiffin service", opts, key=f"{prefix}_pid",
                           format_func=lambda x: f"{prov(x)['icon']} {prov(x)['name']} — {prov(x)['locality']}"
                                                 f"{'' if c['locality'] in prov(x)['delivers_to'] else ' (doesn’t deliver to you)'}")
    p = prov(pid)
    meal_opts = list(p["slots"]) + (["Lunch + Dinner"] if len(p["slots"]) == 2 else [])
    ensure_valid(f"{prefix}_meals_{pid}", meal_opts)
    a, b = st.columns([1.3, 1])
    with a:
        meal_opt = st.radio("Meals", meal_opts, key=f"{prefix}_meals_{pid}", horizontal=True)
    with b:
        start = st.date_input("Start date", value=today(), min_value=today(), max_value=today() + timedelta(days=30),
                              key=f"{prefix}_start", format="DD/MM/YYYY")
    slots = list(p["slots"]) if meal_opt == "Lunch + Dinner" else [meal_opt]
    months_sel = st.session_state.get(f"{prefix}_months", 3)
    cols = st.columns(5)
    for col, pk in zip(cols, PACKAGES):
        price = sub_price(p, pk["months"], slots)
        meals = sub_total_meals(pk["months"], slots)
        with col:
            html(f'<div class="pkg{" on" if pk["months"] == months_sel else ""}"><div class="m">{pk["label"]}</div>'
                 f'<div class="pr">{rupees(price)}</div><div class="small">{meals} meals · {rupees(price / meals)}/meal<br>'
                 f'{disc_txt(pk)} · valid till '
                 f'{sub_expiry(start, pk["months"]):%d %b %y}</div></div>')
    a, b = st.columns([1.3, 1])
    with a:
        months = st.radio("Package", [pk["months"] for pk in PACKAGES], key=f"{prefix}_months", horizontal=True,
                          index=1, format_func=lambda m: f"{m} mo")
    with b:
        st.radio("Payment (simulated)", [PAY_NOW, PAY_LATER_SUB], key=f"{prefix}_pay")
    price, meals, expiry = sub_price(p, months, slots), sub_total_meals(months, slots), sub_expiry(start, months)
    html(f'<div class="callout info"><div class="ci">🧾</div><div><div class="ct">{months}-month plan · '
         f'{esc(" + ".join(slots))} · {rupees(price)}</div><div class="cb">Valid <b>{start:%d %b %Y} → {expiry:%d %b %Y}</b> · '
         f'{meals} meals included ({MEALS_PER_MONTH} × {months} month(s) × {len(slots)} meal slot(s)). '
         f'No real payment is taken.</div></div></div>')
    with st.expander("How plan prices, validity and meals are calculated"):
        html(f"""<ul class="small" style="margin:0">
          <li><b>Validity:</b> starts on the chosen date and ends the day before the same date N months later
              (e.g. 20 Oct + 3 months → valid until 19 Jan).</li>
          <li><b>Included meals:</b> {MEALS_PER_MONTH} meals per month for each meal slot (Monday–Saturday delivery, Sundays off).
              Lunch-only for 3 months = {MEALS_PER_MONTH * 3} meals; Lunch + Dinner = {MEALS_PER_MONTH * 6}.</li>
          <li><b>Price:</b> per-meal price × included meals, minus a duration discount
              (1 mo 0%, 3 mo 5%, 6 mo 8%, 9 mo 10%, 12 mo 12%), rounded to the nearest ₹10.</li>
          <li><b>Remaining meals</b> = included − delivered − scheduled. Skipped meals are not deducted; unused meals lapse at expiry.</li>
          <li>Plan meals are scheduled {SCHEDULE_DAYS_AHEAD} days ahead. If you start today after a meal's cutoff, that meal starts tomorrow.</li>
        </ul>""")
    clash = next((s for s in D()["subs"] if s["customer_id"] == c["id"] and s["provider_id"] == pid
                  and sub_state(s) in ("Active", "Upcoming") and s["start"] <= expiry and s["expiry"] >= start), None)
    if clash:
        callout("warning", f"You already have a plan with {p['name']}",
                f"{clash['id']} runs until {clash['expiry']:%d %b %Y}. Choose another kitchen, or a start date after it ends.")
    ok = p["accepting_subs"] and c["locality"] in p["delivers_to"] and not clash
    with st.container(key=f"cta_sub_{prefix}"):
        st.button(f"Activate {months}-month plan · {rupees(price)}", key=f"{prefix}_go", disabled=not ok,
                  on_click=cb_activate_sub, args=(prefix, fixed_pid))
    if not ok and not clash:
        html(f'<p class="small">{"Subscriptions are closed for this kitchen." if not p["accepting_subs"] else "This kitchen does not deliver to your locality."}</p>')


def c_subscriptions() -> None:
    page_header("Subscriptions", "Monthly tiffin plans",
                "Choose 1, 3, 6, 9 or 12 months. Payments are simulated — no real money is charged.")
    subs = my_subs()
    cur = [s for s in subs if sub_state(s) in ("Active", "Upcoming")]
    t1, t2 = st.tabs([f"My plans ({len(cur)})", "➕ New subscription"])
    with t1:
        if cur:
            cols = st.columns(2, gap="medium")
            for i, s in enumerate(cur):
                with cols[i % 2]:
                    sub_card(s)
        else:
            empty("🔁", "No active subscription", "Open the 'New subscription' tab to start a plan.")
        prev = [s for s in subs if sub_state(s) in ("Expired", "Cancelled")]
        html('<div class="h2" style="margin-top:1rem">Previous and expired plans</div>')
        if prev:
            idx = payment_index(D())
            money_df(pd.DataFrame([{"Plan ID": s["id"], "Kitchen": prov(s["provider_id"])["name"], "Package": s["package"],
                                    "Meals": " + ".join(s["slots"]), "Start": s["start"], "Expired on": s["expiry"],
                                    "Delivered": sub_counts(s)["Delivered"], "Skipped": sub_counts(s)["Skipped"],
                                    "Price": s["price"], "Payment": idx[s["id"]]["status"]} for s in prev]),
                     ["Price"], ["Start", "Expired on"])
        else:
            html('<p class="muted">None yet.</p>')
    with t2:
        with st.container(key="card_newsub"):
            subscribe_form("ns")


def c_skip() -> None:
    page_header("Skip a meal", "Not eating in?",
                "Skip before the cutoff so your kitchen doesn't cook a meal that goes to waste.")
    cutoffs = ", ".join(f"{p['name']}: {p['cutoff_hours']}h" for p in D()["providers"].values()
                        if any(o["provider_id"] == p["id"] for o in my_orders()))
    callout("info", f"Cutoff rule · demo time is {fmt_day(today())}, {st.session_state.clock}",
            f"A meal can be skipped while it is <b>Confirmed</b> and before the kitchen's cutoff "
            f"(lunch is delivered at {SLOT_TIME['Lunch']:%H:%M}, dinner at {SLOT_TIME['Dinner']:%H:%M}; "
            f"cutoff = delivery time minus the kitchen's notice hours{' — ' + esc(cutoffs) if cutoffs else ''}). "
            "Plan meals stay in your balance; prepaid one-day orders are refunded (simulated). "
            "Change the demo time in the sidebar to see the cutoff in action.")
    upcoming = sorted([o for o in my_orders() if o["date"] >= today() and o["status"] in ACTIVE],
                      key=lambda o: (o["date"], SLOTS.index(o["slot"])))
    if not upcoming:
        empty("🍽️", "No upcoming meals", "Order a meal or activate a plan first.")
        st.button("Discover kitchens →", key="sk_disc", on_click=cb_cnav, args=("Discover",))
    pending = st.session_state.skip_pending
    for o in upcoming:
        p = prov(o["provider_id"])
        cut = cutoff_dt(p, o["date"], o["slot"])
        if o["status"] != "Confirmed":
            reason, ok = f"🔒 Kitchen has marked it {o['status']}", False
        elif now() >= cut:
            reason, ok = f"🔒 Cutoff passed at {cut:%H:%M}", False
        else:
            mins = int((cut - now()).total_seconds() // 60)
            reason, ok = f"✅ Eligible · {mins // 60}h {mins % 60:02d}m left", True
        if pending == o["id"] and ok:
            with st.container(key=f"confirm_{o['id']}"):
                html(f'<div class="ct" style="font-weight:700;font-size:1.05rem">Skip {o["slot"].lower()} on {esc(fmt_day(o["date"]))}?</div>'
                     f'<div style="font-size:.92rem;margin:.25rem 0 .7rem">{esc(o["meal_name"])} × {o["qty"]} from {esc(p["name"])} ({o["id"]}). '
                     f'{"The meal stays in your plan balance." if o["order_type"] == "Subscription" else "Prepaid amounts are refunded (simulated)." if o["pay_mode"] == PAY_NOW else "You will not be charged."} '
                     f'This can\'t be undone.</div>')
                a, b, _ = st.columns([1.2, 1, 1.4])
                a.button("Yes, skip this meal", key=f"skyes_{o['id']}", type="primary", on_click=cb_confirm_skip,
                         args=(o["id"],), width="stretch")
                b.button("Keep my meal", key=f"skno_{o['id']}", on_click=cb_cancel_skip, width="stretch")
            st.write("")
            continue
        with st.container(key=f"row_skip_{o['id']}"):
            a, b = st.columns([3.2, 1], vertical_alignment="center")
            with a:
                html(f'<div style="display:flex;gap:.75rem;align-items:center;flex-wrap:wrap">'
                     f'<div class="pc-icon" style="width:42px;height:42px;font-size:1.2rem">{SLOT_ICON[o["slot"]]}</div>'
                     f'<div style="flex:1;min-width:200px"><b>{esc(fmt_day(o["date"]))} · {o["slot"]}</b> · {esc(o["meal_name"])} × {o["qty"]}'
                     f'<div class="small">{esc(p["name"])} · {esc(o["order_type"])} · {o["id"]} · cutoff {cut:%a %d %b, %H:%M}</div>'
                     f'<div class="small" style="color:{"var(--forest)" if ok else "var(--terra-2)"}">{esc(reason)}</div></div>'
                     f'{badge(o["status"])}</div>')
            with b:
                st.button("Skip meal", key=f"sk_{o['id']}", disabled=not ok, on_click=cb_request_skip, args=(o["id"],),
                          width="stretch")
        st.write("")
    skipped = sorted([o for o in my_orders() if o["status"] == "Skipped"], key=lambda o: o["history"][-1]["at"], reverse=True)[:6]
    if skipped:
        html('<div class="h2" style="margin-top:.6rem">Recently skipped</div>')
        for o in skipped:
            html(f'<div class="feed"><div>⏭️</div><div style="flex:1">{esc(fmt_day(o["date"]))} · {o["slot"]} · {esc(o["meal_name"])}'
                 f'<div class="small">{esc(prov(o["provider_id"])["name"])} · {o["id"]} · skipped {o["history"][-1]["at"]:%d %b %H:%M}</div></div>'
                 f'{badge("Skipped")}</div>')


def c_profile() -> None:
    c = me()
    page_header("Profile & settings", "Your details", "Used by kitchens for delivery. Demo account — no password needed.")
    with st.container(key="card_profile"):
        a, b = st.columns(2)
        with a:
            st.text_input("Full name", value=c["name"], key="pf_name")
            st.text_input("Phone (fictional)", value=c["phone"], key="pf_phone")
            st.text_input("Email", value=c["email"], key="pf_email")
            st.selectbox("Locality", LOCALITIES, index=LOCALITIES.index(c["locality"]), key="pf_loc")
        with b:
            st.text_area("Delivery address", value=c["address"], key="pf_addr", height=100)
            diets = ["Vegetarian", "Non-vegetarian", "Eggetarian", "Jain"]
            st.selectbox("Food preference", diets, index=diets.index(c["diet"]) if c["diet"] in diets else 0, key="pf_diet")
            pays = [PAY_NOW, PAY_LATER_ORDER]
            st.radio("Default payment for one-day orders", pays,
                     index=pays.index(c["default_pay"]) if c["default_pay"] in pays else 0, key="pf_pay")
        st.button("Save profile", key="pf_save", type="primary", on_click=cb_save_profile)
    html('<p class="small" style="margin-top:.6rem">Changing your locality changes which kitchens can deliver to you. '
         'Existing orders keep the address they were placed with.</p>')


# =============================================================================
# 8. OWNER
# =============================================================================

ONAV = [("Dashboard", "📊  Dashboard"), ("Orders", "🧾  Orders & deliveries"), ("Menu", "📝  Menu"),
        ("Subscriptions", "🔁  Subscriptions"), ("Customers", "👥  Customers"), ("Payments", "💰  Payments & income"),
        ("Reports", "📈  Reports & CSV"), ("Profile", "🏠  Kitchen profile")]


def render_owner() -> None:
    p = prov(st.session_state.pid)
    sidebar_common("Tiffin owner", p["owner"], f"{p['icon']} {p['name']} · {p['locality']}")
    with st.sidebar:
        st.session_state.kitchen_w = p["id"]
        st.selectbox("Demo: switch kitchen", list(D()["providers"]), key="kitchen_w", on_change=cb_kitchen,
                     format_func=lambda x: prov(x)["name"])
        html('<div class="sb-label">Manage</div>')
        for page, label in ONAV:
            st.button(label, key=f"on_{page}", type="primary" if st.session_state.opage == page else "secondary",
                      on_click=cb_onav, args=(page,), width="stretch")
    sidebar_footer()
    show_flash()
    {"Dashboard": o_dashboard, "Orders": o_orders, "Menu": o_menu, "Subscriptions": o_subscriptions,
     "Customers": o_customers, "Payments": o_payments, "Reports": o_reports,
     "Profile": o_profile}.get(st.session_state.opage, o_dashboard)(p)


def k_orders(pid, day=None) -> list[dict]:
    return [o for o in D()["orders"] if o["provider_id"] == pid and (day is None or o["date"] == day)]


def k_payments(pid) -> list[dict]:
    return [p for p in D()["payments"] if p["provider_id"] == pid]


def income(pid, start: date, end: date) -> int:
    return sum(p["amount"] for p in k_payments(pid) if start <= p["at"].date() <= end)


def o_dashboard(p: dict) -> None:
    pid, t = p["id"], today()
    page_header(f"Good to see you, {p['owner'].split()[0]}", f"{p['name']} — today",
                f"{fmt_day(t)} · demo time {st.session_state.clock} · every number below is calculated from the order and payment records.")
    todays = k_orders(pid, t)
    confirmed = [o for o in todays if o["status"] in COUNTED]
    m0, m1 = month_bounds(t.strftime("%Y-%m"))
    subs_active = {s["customer_id"] for s in D()["subs"] if s["provider_id"] == pid and sub_state(s) == "Active"}
    stat_row([
        ("Today's confirmed orders", len(confirmed), "Excludes skipped & cancelled", "🧾"),
        ("Meals to prepare", sum(o["qty"] for o in todays if o["status"] in ("Confirmed", "Preparing")),
         "Confirmed + preparing", "👩‍🍳"),
        ("Skipped meals", sum(o["qty"] for o in todays if o["status"] == "Skipped"), "Removed from cooking", "⏭️", True),
        ("Active subscribers", len(subs_active), "Customers with a live plan", "🔁"),
    ])
    stat_row([
        ("Pending deliveries", sum(1 for o in todays if o["status"] in ACTIVE), "Not yet delivered", "🛵"),
        ("Completed deliveries", sum(1 for o in todays if o["status"] == "Delivered"), "Delivered today", "📦"),
        ("Income today", rupees(income(pid, t, t)), "Recorded payments (simulated)", "💰"),
        ("Income this month", rupees(income(pid, m0, m1)), f"{t:%B} · net of refunds", "📈"),
    ])

    left, right = st.columns([1.25, 1], gap="large")
    with left, st.container(key="card_dash_prep"):
        html('<div class="eyebrow">Preparation plan</div><div class="h2">What to cook today</div>')
        prep_table(pid, t, compact=True)
        a, b = st.columns(2)
        a.button("Open orders & deliveries →", key="d_orders", on_click=cb_onav, args=("Orders",), width="stretch")
        b.button("Manage menu", key="d_menu", on_click=cb_onav, args=("Menu",), width="stretch")
    with right, st.container(key="card_dash_feed"):
        html('<div class="eyebrow">Live activity</div><div class="h2">Recent updates</div>')
        feed = sorted([a for a in D()["activity"] if a["pid"] == pid and a["at"].date() == t], key=lambda a: a["at"])[-8:][::-1]
        if feed:
            html("".join(f'<div class="feed"><div class="t">{a["at"]:%H:%M}</div><div>{a["icon"]}</div><div>{esc(a["text"])}</div></div>' for a in feed))
        else:
            html('<p class="muted">No activity yet today.</p>')
        tm = D()["menus"].get(mkey(pid, t + timedelta(days=1)))
        if not tm or not tm["published"]:
            callout("warning", "Tomorrow's menu isn't published",
                    "Customers can't place one-day orders for tomorrow until you publish it.")
            st.button("Publish tomorrow's menu →", key="d_tm", on_click=cb_onav, args=("Menu",))
        dues = [r for r in payment_index(D()).values() if r["provider_id"] == pid and r["outstanding"] > 0]
        if dues:
            html(f'<p class="small" style="margin-top:.6rem">💳 {len(dues)} unpaid item(s) · {rupees(sum(r["outstanding"] for r in dues))} '
                 f'outstanding — see Payments.</p>')


def prep_table(pid: str, day: date, actions: bool = False, compact: bool = False) -> None:
    orders = k_orders(pid, day)
    if not orders:
        empty("🧾", f"No orders for {fmt_day(day)}", "New orders appear here automatically.")
        return
    rows = []
    for slot in SLOTS:
        meals = sorted({o["meal_name"] for o in orders if o["slot"] == slot})
        for meal in meals:
            os_ = [o for o in orders if o["slot"] == slot and o["meal_name"] == meal]
            q = lambda *sts: sum(o["qty"] for o in os_ if o["status"] in sts)
            rows.append({"slot": slot, "meal": meal, "conf": q("Confirmed"), "prep": q("Preparing"),
                         "ready": q("Prepared", "Out for delivery", "Delivered"), "total": q(*COUNTED),
                         "skip": q("Skipped"), "cancel": q("Cancelled")})
    if compact:
        body = "".join(
            f'<tr><td>{SLOT_ICON[r["slot"]]} <b>{esc(r["meal"])}</b></td><td class="num"><b style="color:var(--forest)">{r["total"]}</b></td>'
            f'<td class="num">{r["ready"]}</td><td class="num" style="color:var(--muted)">{r["skip"] + r["cancel"]}</td>'
            f'<td>{"✅" if r["total"] and r["conf"] == 0 and r["prep"] == 0 else ("⬜" if r["total"] else "—")}</td></tr>' for r in rows)
        tt = sum(r["total"] for r in rows)
        html(f'<table class="tbl"><tr><th>Item</th><th class="num">To cook</th><th class="num">Ready</th><th class="num">Skipped</th><th></th></tr>'
             f'{body}<tr class="tot"><td>Total</td><td class="num">{tt}</td><td class="num">{sum(r["ready"] for r in rows)}</td>'
             f'<td class="num">{sum(r["skip"] + r["cancel"] for r in rows)}</td><td></td></tr></table>'
             f'<p class="small" style="margin-top:.4rem">To cook excludes skipped and cancelled meals.</p>')
        return
    body = "".join(
        f'<tr><td>{SLOT_ICON[r["slot"]]} {r["slot"]}</td><td><b>{esc(r["meal"])}</b></td>'
        f'<td class="num">{r["conf"]}</td><td class="num">{r["prep"]}</td><td class="num">{r["ready"]}</td>'
        f'<td class="num"><b style="color:var(--forest)">{r["total"]}</b></td>'
        f'<td class="num" style="color:var(--muted)">{r["skip"]} / {r["cancel"]}</td>'
        f'<td>{"✅ done" if r["total"] and r["conf"] == 0 and r["prep"] == 0 else ("⬜ to cook" if r["total"] else "—")}</td></tr>'
        for r in rows)
    tot = {k: sum(r[k] for r in rows) for k in ("conf", "prep", "ready", "total", "skip", "cancel")}
    html(f'<table class="tbl"><tr><th>Meal</th><th>Item</th><th class="num">Confirmed</th><th class="num">Preparing</th>'
         f'<th class="num">Ready / out / delivered</th><th class="num">Total to cook</th><th class="num">Skipped / cancelled</th><th>Checklist</th></tr>'
         f'{body}<tr class="tot"><td colspan="2">Total</td><td class="num">{tot["conf"]}</td><td class="num">{tot["prep"]}</td>'
         f'<td class="num">{tot["ready"]}</td><td class="num">{tot["total"]}</td><td class="num">{tot["skip"]} / {tot["cancel"]}</td><td></td></tr></table>'
         f'<p class="small" style="margin-top:.4rem">Total to cook = confirmed + preparing + ready/out/delivered. '
         f'Skipped and cancelled meals are excluded.</p>')
    if actions:
        for r in rows:
            if r["conf"] or r["prep"]:
                a, b, c = st.columns([2, 1, 1], vertical_alignment="center")
                a.markdown(f"{SLOT_ICON[r['slot']]} **{r['meal']}**")
                if r["conf"]:
                    b.button(f"Start preparing ({r['conf']})", key=f"bp_{r['slot']}_{r['meal']}", width="stretch",
                             on_click=cb_batch, args=(pid, day.isoformat(), r["slot"], r["meal"], "Confirmed", "Preparing"))
                if r["prep"]:
                    c.button(f"Mark prepared ({r['prep']})", key=f"bd_{r['slot']}_{r['meal']}", width="stretch",
                             on_click=cb_batch, args=(pid, day.isoformat(), r["slot"], r["meal"], "Preparing", "Prepared"))


def o_orders(p: dict) -> None:
    pid = p["id"]
    page_header("Orders & deliveries", "Orders, preparation and delivery",
                "Move each tiffin along as you cook and dispatch it — customers see the status immediately.")
    opts = [(today() + timedelta(days=k)).isoformat() for k in (-1, 0, 1, 2)]
    ensure_valid("oo_day", opts)
    day = date.fromisoformat(st.segmented_control("Meal date", opts, default=opts[1], key="oo_day",
                                                  format_func=lambda x: fmt_day(date.fromisoformat(x))) or opts[1])
    orders = k_orders(pid, day)
    idx = payment_index(D())
    stat_row([
        ("Confirmed orders", sum(1 for o in orders if o["status"] in COUNTED), "Excl. skipped & cancelled", "🧾"),
        ("Meals to prepare", sum(o["qty"] for o in orders if o["status"] in ("Confirmed", "Preparing")), "Confirmed + preparing", "👩‍🍳"),
        ("Pending deliveries", sum(1 for o in orders if o["status"] in ACTIVE), "Not delivered yet", "🛵"),
        ("Delivered", sum(1 for o in orders if o["status"] == "Delivered"), "Completed", "📦"),
        ("Skipped / cancelled", f"{sum(o['qty'] for o in orders if o['status'] == 'Skipped')} / "
                                f"{sum(o['qty'] for o in orders if o['status'] == 'Cancelled')}", "Not cooked", "⏭️", True),
    ])
    with st.container(key="card_prep"):
        html('<div class="eyebrow">Preparation checklist</div>')
        prep_table(pid, day, actions=True)
    st.write("")

    active = sorted([o for o in orders if o["status"] in ACTIVE],
                    key=lambda o: (SLOTS.index(o["slot"]), FLOW.index(o["status"]), o["id"]))
    html(f'<div class="h2">Update status · {len(active)} in progress</div>')
    if not active:
        html('<p class="muted">Nothing in progress for this date. 🎉</p>')
    for o in active:
        c = cust(o["customer_id"])
        pay = order_pay_status(o, idx)
        with st.container(key=f"row_o_{o['id']}"):
            a, b, m = st.columns([3.3, 1.25, 0.45], vertical_alignment="center")
            with a:
                html(f'<div style="display:flex;gap:.45rem;align-items:center;flex-wrap:wrap"><b>{esc(c["name"])}</b>{badge(o["status"])}'
                     f'<span class="chip grey">{SLOT_ICON[o["slot"]]} {esc(o["meal_name"])} × {o["qty"]}</span>'
                     f'<span class="chip{" terra" if o["order_type"] == "Subscription" else ""}">{esc(o["order_type"])}</span>{badge(pay)}</div>'
                     f'<div class="small" style="margin-top:.2rem">{o["id"]} · {rupees(o["amount"]) if o["amount"] else "plan"} · '
                     f'📍 {esc(o["delivery_locality"])} — {esc(c["address"])} · 📞 {esc(c["phone"])}'
                     f'{" · 📝 " + esc(o["note"]) if o["note"] else ""}</div>')
            nxt = [s for s in TRANSITIONS[o["status"]] if s in FLOW]
            with b:
                if nxt:
                    out = idx.get(o["id"], {}).get("outstanding", 0)
                    if nxt[0] == "Delivered" and o["order_type"] == "One-day" and out > 0:
                        st.button("📦 Delivered + cash", key=f"st_{o['id']}", type="primary", width="stretch",
                                  on_click=cb_status, args=(o["id"], "Delivered", True), help=f"Also records {rupees(out)} received")
                    else:
                        st.button(NEXT_LABEL[nxt[0]], key=f"st_{o['id']}", type="primary", width="stretch",
                                  on_click=cb_status, args=(o["id"], nxt[0]))
            with m:
                others = [s for s in TRANSITIONS[o["status"]] if s not in nxt[:1]]
                if o["status"] == "Out for delivery" and o["order_type"] == "One-day" and idx.get(o["id"], {}).get("outstanding", 0) > 0:
                    others = ["Delivered (payment pending)"]
                if others:
                    with st.popover("⋯", width="stretch"):
                        html(f'<div class="small">Other actions for {o["id"]}</div>')
                        for s in others:
                            if s == "Delivered (payment pending)":
                                st.button("📦 Delivered — payment still pending", key=f"alt_{o['id']}_dp",
                                          on_click=cb_status, args=(o["id"], "Delivered"))
                            else:
                                st.button({"Skipped": "⏭️ Mark skipped (customer asked)", "Cancelled": "✖️ Cancel order"}.get(s, s),
                                          key=f"alt_{o['id']}_{s}", on_click=cb_status, args=(o["id"], s))
                        if "Cancelled" in others and pay == "Paid":
                            html('<div class="small">Cancelling refunds the simulated payment.</div>')
        html('<div style="height:.35rem"></div>')

    st.write("")
    html('<div class="h2">Order-management table</div>')
    a, b, c = st.columns([2, 1, 1.4])
    sts = a.multiselect("Status", STATUSES, default=STATUSES, key="ot_status")
    typ = b.selectbox("Order type", ["All", "One-day", "Subscription"], key="ot_type")
    q = c.text_input("Search customer / order ID", key="ot_q").strip().lower()
    rows = []
    for o in sorted(orders, key=lambda o: (SLOTS.index(o["slot"]), o["id"])):
        cn = cust(o["customer_id"])["name"]
        if o["status"] not in sts or (typ != "All" and o["order_type"] != typ):
            continue
        if q and q not in cn.lower() and q not in o["id"].lower():
            continue
        rows.append({"Order ID": o["id"], "Customer": cn, "Meal date": o["date"], "Slot": o["slot"], "Meal": o["meal_name"],
                     "Qty": o["qty"], "Order type": o["order_type"], "Amount": o["amount"],
                     "Payment": order_pay_status(o, idx), "Status": o["status"], "Delivery locality": o["delivery_locality"]})
    if rows:
        money_df(pd.DataFrame(rows), ["Amount"], ["Meal date"])
        html('<p class="small">Plan meals show ₹0: their value is in the subscription price, so revenue is not counted twice.</p>')
    else:
        empty("🧾", "No orders match", "Change the filters or the date.")


def o_menu(p: dict) -> None:
    pid = p["id"]
    page_header("Menu", "Daily menu management",
                "Edit a draft, then publish it for the selected date. Customers only see published menus.")
    opts = [(today() + timedelta(days=k)).isoformat() for k in range(0, 7)]
    ensure_valid("m_day", opts)
    day_iso = st.segmented_control("Menu date", opts, default=opts[1], key="m_day",
                                   format_func=lambda x: fmt_day(date.fromisoformat(x))) or opts[1]
    day = date.fromisoformat(day_iso)
    entry = menu_entry(pid, day)
    draft, pub = entry["draft"], entry["published"]
    sig = lambda items: sorted((i["slot"], i["name"], i["desc"], i["price"]) for i in (items or []))
    if pub and sig(draft) == sig(pub):
        callout("success", f"Published for {fmt_day(day)}", f"Live since {entry['published_at']:%a %d %b, %H:%M}. "
                                                            "Customers see exactly what's below.")
    elif pub:
        callout("warning", "Draft has unpublished changes", "Customers still see the previously published menu (right). "
                                                            "Publish to update it.")
    else:
        callout("info", f"Not published for {fmt_day(day)}", "Customers see 'menu not published' and can't place "
                                                              "one-day orders for this date.")
    left, right = st.columns([1.5, 1], gap="large")
    with left:
        if not draft:
            prev = (day - timedelta(days=1)).isoformat()
            empty("📝", "No items in the draft yet", "Add items below, or copy the previous day's menu.")
            st.button(f"Copy {fmt_day(day - timedelta(days=1))}'s menu", key="m_copy", on_click=cb_copy_menu,
                      args=(pid, day_iso, prev))
        for slot in SLOTS:
            items = [i for i in draft if i["slot"] == slot]
            if not items and slot not in p["slots"]:
                continue
            html(f'<div class="h2">{SLOT_ICON[slot]} {slot}{"" if slot in p["slots"] else " <span class=small>(not served — update profile)</span>"}</div>')
            if not items:
                html('<p class="muted">No items yet.</p>')
            for it in items:
                with st.container(key=f"row_mi_{it['id']}"):
                    if st.session_state.edit_item == it["id"]:
                        a, b = st.columns([2, 1])
                        a.text_input("Meal name", value=it["name"], key=f"ei_name_{it['id']}")
                        b.number_input("Price (₹)", 1, 1000, int(it["price"]), step=5, key=f"ei_price_{it['id']}")
                        a2, b2 = st.columns([2, 1])
                        a2.text_input("Description", value=it["desc"], key=f"ei_desc_{it['id']}")
                        b2.selectbox("Meal", p["slots"] if it["slot"] in p["slots"] else SLOTS,
                                     index=(p["slots"] if it["slot"] in p["slots"] else SLOTS).index(it["slot"]),
                                     key=f"ei_slot_{it['id']}")
                        x, y, _ = st.columns([1, 1, 2])
                        x.button("Save", key=f"eis_{it['id']}", type="primary", on_click=cb_save_item,
                                 args=(pid, day_iso, it["id"]), width="stretch")
                        y.button("Cancel", key=f"eic_{it['id']}", on_click=cb_edit_item, args=(None,), width="stretch")
                    else:
                        a, b, c = st.columns([3.4, 0.8, 0.8], vertical_alignment="center")
                        a.markdown(f'<div class="mi"><div><div class="n">{esc(it["name"])}</div><div class="d">{esc(it["desc"]) or "—"}</div></div>'
                                   f'<div class="p">{rupees(it["price"])}</div></div>', unsafe_allow_html=True)
                        b.button("Edit", key=f"ie_{it['id']}", on_click=cb_edit_item, args=(it["id"],), width="stretch")
                        c.button("Delete", key=f"id_{it['id']}", on_click=cb_delete_item, args=(pid, day_iso, it["id"]),
                                 width="stretch")
                html('<div style="height:.3rem"></div>')
        st.write("")
        with st.form(f"add_item_{pid}_{day_iso}", clear_on_submit=False, border=True):
            html('<div class="eyebrow">Add menu item</div>')
            a, b, c = st.columns([2, 1, 1])
            a.text_input("Meal name", key="ni_name", placeholder="e.g. Sabudana Khichdi Plate")
            b.selectbox("Meal", p["slots"], key="ni_slot")
            c.number_input("Price (₹)", 1, 1000, int(p["prices"][p["slots"][0]]), step=5, key="ni_price")
            st.text_input("Description", key="ni_desc", placeholder="What's in the tiffin")
            st.form_submit_button("➕ Add to draft", on_click=cb_add_item, args=(pid, day_iso))
        x, y = st.columns(2)
        with x, st.container(key="cta_publish"):
            st.button(f"✅ Publish menu for {fmt_day(day, False)}", key="m_pub", on_click=cb_publish,
                      args=(pid, day_iso), width="stretch", disabled=not draft)
        y.button("Discard draft changes", key="m_discard", on_click=cb_discard_draft, args=(pid, day_iso),
                 width="stretch", disabled=not pub or sig(draft) == sig(pub))
    with right, st.container(key="card_menu_preview"):
        html('<div class="eyebrow">What customers see</div>')
        if pub:
            html(f'<div class="pc-name">{esc(p["name"])}</div><div class="small">{esc(fmt_day(day))} · published {entry["published_at"]:%H:%M}</div>')
            for slot in p["slots"]:
                its = [i for i in pub if i["slot"] == slot]
                html(f'<div style="font-weight:700;margin:.7rem 0 .3rem">{SLOT_ICON[slot]} {slot}</div>'
                     + ("".join(f'<div class="mi" style="padding:.35rem 0;border-bottom:1px solid #F0EBE2"><div><div class="n">{esc(i["name"])}</div>'
                                f'<div class="d">{esc(i["desc"])}</div></div><div class="p">{rupees(i["price"])}</div></div>' for i in its)
                        or '<p class="small">No items — customers can\'t order this meal.</p>'))
            html('<p class="small" style="margin-top:.6rem">Booked: ' +
                 " · ".join(f"{s} {booked(pid, day, s)}/{p['capacity']}" for s in p["slots"]) + '</p>')
        else:
            empty("👀", "Not visible yet", "Publish the draft to show it to customers.")


def o_subscriptions(p: dict) -> None:
    pid = p["id"]
    page_header("Subscriptions", "Subscription management", "Plans, validity, meal balances and simulated payment status.")
    subs = [s for s in D()["subs"] if s["provider_id"] == pid]
    idx = payment_index(D())
    soon = [s for s in subs if sub_state(s) == "Active" and (s["expiry"] - today()).days <= 7]
    stat_row([
        ("Active plans", sum(1 for s in subs if sub_state(s) == "Active"), "Valid today", "🔁"),
        ("Upcoming", sum(1 for s in subs if sub_state(s) == "Upcoming"), "Start later", "🗓️"),
        ("Expiring in 7 days", len(soon), ", ".join(cust(s["customer_id"])["name"].split()[0] for s in soon) or "None", "⏳", bool(soon)),
        ("Unpaid plan amount", rupees(sum(idx[s["id"]]["outstanding"] for s in subs)), "Pending + partial", "💳", True),
    ])
    sts = st.multiselect("Status", ["Active", "Upcoming", "Expired"], default=["Active", "Upcoming"], key="os_status")
    rows = []
    for s in sorted(subs, key=lambda s: s["start"], reverse=True):
        if sub_state(s) not in sts:
            continue
        c = sub_counts(s)
        rows.append({"Plan ID": s["id"], "Customer": cust(s["customer_id"])["name"], "Plan": f"{s['package']} · {' + '.join(s['slots'])}",
                     "Start": s["start"], "Expiry": s["expiry"], "Total meals": s["total_meals"], "Delivered": c["Delivered"],
                     "Scheduled": c["Scheduled"], "Skipped": c["Skipped"], "Remaining": c["Remaining"], "Price": s["price"],
                     "Paid": idx[s["id"]]["paid"], "Payment": idx[s["id"]]["status"], "Status": sub_state(s)})
    if rows:
        money_df(pd.DataFrame(rows), ["Price", "Paid"], ["Start", "Expiry"])
    else:
        empty("🔁", "No subscriptions match", "Change the status filter.")
    unpaid = [s for s in subs if idx[s["id"]]["outstanding"] > 0]
    if unpaid:
        html('<div class="h2" style="margin-top:1rem">Record a plan payment</div>')
        st.selectbox("Received via", ["Cash", "UPI (simulated)", "Bank transfer (simulated)"], key="rec_method")
        for s in unpaid:
            r = idx[s["id"]]
            with st.container(key=f"row_sp_{s['id']}"):
                a, b = st.columns([3, 1], vertical_alignment="center")
                a.markdown(f"**{cust(s['customer_id'])['name']}** · {s['id']} · {s['package']} · paid {rupees(r['paid'])} of "
                           f"{rupees(r['charge'])} &nbsp; {badge(r['status'])}", unsafe_allow_html=True)
                b.button(f"Record {rupees(r['outstanding'])}", key=f"rsp_{s['id']}", on_click=cb_pay_due,
                         args=(s["id"], "Kitchen"), width="stretch")


def o_customers(p: dict) -> None:
    pid = p["id"]
    page_header("Customers", "Customer management", "Everyone who has ordered or subscribed. Contact details are fictional placeholders.")
    idx = payment_index(D())
    ids = {o["customer_id"] for o in k_orders(pid)} | {s["customer_id"] for s in D()["subs"] if s["provider_id"] == pid}
    q = st.text_input("Search by name, locality, phone or plan", key="cu_q", placeholder="e.g. Wakad, Rahul, SUB-").strip().lower()
    rows = []
    for cid in sorted(ids, key=lambda c: cust(c)["name"]):
        c = cust(cid)
        act = [s for s in D()["subs"] if s["provider_id"] == pid and s["customer_id"] == cid and sub_state(s) in ("Active", "Upcoming")]
        os_ = [o for o in k_orders(pid) if o["customer_id"] == cid]
        due = sum(r["outstanding"] for r in idx.values() if r["provider_id"] == pid and r["customer_id"] == cid)
        row = {"Customer": c["name"], "Contact": c["phone"], "Email": c["email"], "Locality": c["locality"],
               "Active plan": f"{act[0]['id']} · {act[0]['package']} · {' + '.join(act[0]['slots'])}" if act else "—",
               "Orders": sum(1 for o in os_ if o["order_type"] == "One-day"),
               "Plan meals": sum(1 for o in os_ if o["order_type"] == "Subscription"),
               "Last meal": max((o["date"] for o in os_), default=None),
               "Outstanding": due, "Payment status": "Dues pending" if due > 0 else "Clear"}
        if q and q not in " ".join(str(v) for v in row.values()).lower():
            continue
        rows.append(row)
    html(f'<p class="muted">{len(rows)} customer(s)</p>')
    if rows:
        money_df(pd.DataFrame(rows), ["Outstanding"], ["Last meal"])
    else:
        empty("👥", "No customers match", "Try another search.")


def o_payments(p: dict) -> None:
    pid, t = p["id"], today()
    page_header("Payments & income", "Payments and dues (simulated)",
                "Order value, recorded payments and outstanding amounts are kept separate.")
    idx = payment_index(D())
    mine = [r for r in idx.values() if r["provider_id"] == pid]
    m0, m1 = month_bounds(t.strftime("%Y-%m"))
    month_rows = [r for r in mine if m0 <= r["billed_on"] <= m1 and r["charge"] > 0]
    dues = sorted([r for r in mine if r["outstanding"] > 0], key=lambda r: r["billed_on"])
    stat_row([
        ("Daily income", rupees(income(pid, t, t)), f"Payments recorded {t:%d %b}", "💰"),
        ("Monthly income", rupees(income(pid, m0, m1)), f"{t:%B} · net of refunds", "📈"),
        ("Paid orders", f"{sum(1 for r in month_rows if r['kind'] == 'One-day order' and r['status'] == 'Paid')}",
         f"of {sum(1 for r in month_rows if r['kind'] == 'One-day order')} one-day orders billed in {t:%b}", "✅"),
        ("Pending dues", rupees(sum(r["outstanding"] for r in dues)), f"{len(dues)} unpaid item(s), all dates", "⏳", True),
    ])
    with st.expander("How these figures are calculated", expanded=False):
        html("""<ul class="small" style="margin:0">
          <li><b>Order value / billed</b> — one-day orders (excluding skipped and cancelled) plus subscription package prices.
              Plan meals carry ₹0 because their value is already in the subscription price, so nothing is counted twice.</li>
          <li><b>Recorded payments (income)</b> — money received, by payment date. Refunds are negative entries.</li>
          <li><b>Outstanding</b> — billed amount minus payments recorded against that order or plan.</li></ul>""")
    t1, t2 = st.tabs([f"Outstanding dues ({len(dues)})", "Payment records"])
    with t1:
        if not dues:
            empty("🎉", "No pending dues", "Every billed order and plan is fully paid.")
        else:
            st.selectbox("Received via", ["Cash", "UPI (simulated)", "Bank transfer (simulated)"], key="rec_method")
            for r in dues:
                with st.container(key=f"row_due_{r['ref_id']}"):
                    a, b = st.columns([3.2, 1], vertical_alignment="center")
                    a.markdown(f"**{cust(r['customer_id'])['name']}** · {r['ref_id']} · {r['kind']} · billed {r['billed_on']:%d %b}  \n"
                               f"<span class='small'>{esc(r['desc'])} · billed {rupees(r['charge'])}, paid {rupees(r['paid'])}</span> "
                               f"{badge(r['status'])}", unsafe_allow_html=True)
                    b.button(f"Record {rupees(r['outstanding'])}", key=f"rdue_{r['ref_id']}", on_click=cb_pay_due,
                             args=(r["ref_id"], "Kitchen"), width="stretch")
    with t2:
        months = sorted({p_["at"].strftime("%Y-%m") for p_ in k_payments(pid)}, reverse=True) or [t.strftime("%Y-%m")]
        ym = st.selectbox("Month", months, key="pay_month", format_func=lambda m: datetime.strptime(m, "%Y-%m").strftime("%B %Y"))
        a0, a1 = month_bounds(ym)
        pays = sorted([x for x in k_payments(pid) if a0 <= x["at"].date() <= a1], key=lambda x: x["at"], reverse=True)
        if pays:
            money_df(pd.DataFrame([{"Payment ID": x["id"], "Date": x["at"].strftime("%d %b %Y, %H:%M"),
                                    "Customer": cust(x["customer_id"])["name"], "For": x["ref_id"],
                                    "Type": x["kind"], "Method": x["method"], "Amount": x["amount"]} for x in pays]),
                     ["Amount"], height=360)
            html(f'<p class="small">{len(pays)} records · net {rupees(sum(x["amount"] for x in pays))}</p>')
        else:
            empty("💳", "No payments this month", "")


def report_frames(pid: str, ym: str) -> dict:
    """Build every monthly report table from the live records."""
    m0, m1 = month_bounds(ym)
    idx = payment_index(D())
    orders = sorted([o for o in k_orders(pid) if m0 <= o["date"] <= m1], key=lambda o: (o["date"], SLOTS.index(o["slot"]), o["id"]))
    order_df = pd.DataFrame([{
        "Order ID": o["id"], "Meal date": o["date"].isoformat(), "Slot": o["slot"],
        "Customer": cust(o["customer_id"])["name"], "Customer contact": cust(o["customer_id"])["phone"],
        "Delivery locality": o["delivery_locality"], "Meal": o["meal_name"], "Order type": o["order_type"],
        "Plan ID": o["sub_id"] or "", "Qty": o["qty"], "Unit price (INR)": o["unit_price"] if o["order_type"] == "One-day" else 0,
        "Order value (INR)": o["amount"], "Status": o["status"], "Payment status": order_pay_status(o, idx),
        "Ordered at": o["created_at"].strftime("%Y-%m-%d %H:%M"),
        "Last update": f"{o['history'][-1]['at']:%Y-%m-%d %H:%M} ({o['history'][-1]['by']})",
    } for o in orders], columns=["Order ID", "Meal date", "Slot", "Customer", "Customer contact", "Delivery locality",
                                 "Meal", "Order type", "Plan ID", "Qty", "Unit price (INR)", "Order value (INR)",
                                 "Status", "Payment status", "Ordered at", "Last update"])
    pays = sorted([x for x in k_payments(pid) if m0 <= x["at"].date() <= m1], key=lambda x: x["at"])
    pay_df = pd.DataFrame([{
        "Payment ID": x["id"], "Payment date": x["at"].strftime("%Y-%m-%d %H:%M"), "Customer": cust(x["customer_id"])["name"],
        "Source": "Refund" if x["kind"] == "Refund" else ("Subscription" if x["ref_type"] == "Subscription" else "One-day order"),
        "Reference ID": x["ref_id"], "Description": idx.get(x["ref_id"], {}).get("desc", ""), "Method": x["method"],
        "Amount (INR)": x["amount"], "Note": x["note"],
    } for x in pays], columns=["Payment ID", "Payment date", "Customer", "Source", "Reference ID", "Description",
                               "Method", "Amount (INR)", "Note"])
    subs = sorted([s for s in D()["subs"] if s["provider_id"] == pid and s["start"] <= m1 and s["expiry"] >= m0],
                  key=lambda s: s["start"])
    sub_df = pd.DataFrame([{
        "Subscription ID": s["id"], "Customer": cust(s["customer_id"])["name"], "Customer contact": cust(s["customer_id"])["phone"],
        "Plan": s["package"], "Meals": " + ".join(s["slots"]), "Purchased on": s["purchased_at"].strftime("%Y-%m-%d"),
        "Start date": s["start"].isoformat(), "Expiry date": s["expiry"].isoformat(), "Status (as of demo date)": sub_state(s),
        "Total meals": s["total_meals"], "Delivered": sub_counts(s)["Delivered"], "Scheduled": sub_counts(s)["Scheduled"],
        "Skipped": sub_counts(s)["Skipped"], "Remaining meals": sub_counts(s)["Remaining"], "Price (INR)": s["price"],
        "Paid to date (INR)": idx[s["id"]]["paid"], "Outstanding (INR)": idx[s["id"]]["outstanding"],
        "Payment status": idx[s["id"]]["status"],
    } for s in subs], columns=["Subscription ID", "Customer", "Customer contact", "Plan", "Meals", "Purchased on",
                               "Start date", "Expiry date", "Status (as of demo date)", "Total meals", "Delivered",
                               "Scheduled", "Skipped", "Remaining meals", "Price (INR)", "Paid to date (INR)",
                               "Outstanding (INR)", "Payment status"])
    billed = [r for r in idx.values() if r["provider_id"] == pid and m0 <= r["billed_on"] <= m1]
    one_b = [r for r in billed if r["kind"] == "One-day order"]
    sub_b = [r for r in billed if r["kind"] == "Subscription"]
    rec = lambda src: sum(x["amount"] for x in pays if (x["kind"] != "Refund") and
                          (x["ref_type"] == "Subscription") == (src == "Subscription"))
    refunds = sum(x["amount"] for x in pays if x["kind"] == "Refund")
    summary = {
        "orders_total": len(orders), "orders_oneday": sum(1 for o in orders if o["order_type"] == "One-day"),
        "orders_plan": sum(1 for o in orders if o["order_type"] == "Subscription"),
        "meals_done": sum(o["qty"] for o in orders if o["status"] in ("Prepared", "Out for delivery", "Delivered")),
        "meals_delivered": sum(o["qty"] for o in orders if o["status"] == "Delivered"),
        "meals_open": sum(o["qty"] for o in orders if o["status"] in ("Confirmed", "Preparing")),
        "skipped": sum(o["qty"] for o in orders if o["status"] == "Skipped"),
        "cancelled": sum(o["qty"] for o in orders if o["status"] == "Cancelled"),
        "sub_count": len(sub_b), "sub_value": sum(r["charge"] for r in sub_b),
        "payments": sum(x["amount"] for x in pays),
        "due_oneday": sum(r["outstanding"] for r in one_b), "due_sub": sum(r["outstanding"] for r in sub_b),
        "billed_oneday": sum(r["charge"] for r in one_b), "rec_oneday": rec("One-day"),
        "rec_sub": rec("Subscription"), "refunds": refunds,
    }
    summary["dues"] = summary["due_oneday"] + summary["due_sub"]
    return {"orders": order_df, "payments": pay_df, "subs": sub_df, "summary": summary, "raw_orders": orders,
            "raw_pays": pays, "bounds": (m0, m1)}


def to_csv(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8-sig")   # BOM so Excel opens it cleanly


def o_reports(p: dict) -> None:
    pid = p["id"]
    page_header("Reports", "Monthly report & CSV downloads", "Every figure and file is generated from the current demo records.")
    months = sorted({o["date"].strftime("%Y-%m") for o in k_orders(pid)} | {today().strftime("%Y-%m")}, reverse=True)
    a, b = st.columns([1, 2])
    ym = a.selectbox("Reporting month", months, key="rep_month",
                     format_func=lambda m: datetime.strptime(m, "%Y-%m").strftime("%B %Y"))
    R = report_frames(pid, ym)
    S, (m0, m1) = R["summary"], R["bounds"]
    with b:
        html(f'<div style="padding-top:1.9rem" class="small">Period: <b>{m0:%d %b %Y} – {m1:%d %b %Y}</b> · orders by meal date, '
             f'payments by payment date, subscriptions by purchase date'
             f'{" · includes meals scheduled up to " + format(today() + timedelta(days=SCHEDULE_DAYS_AHEAD), "%d %b") if m0 <= today() <= m1 else ""}.</div>')
    stat_row([
        ("Total orders", S["orders_total"], f"{S['orders_oneday']} one-day · {S['orders_plan']} plan meals", "🧾"),
        ("Meals prepared / delivered", S["meals_done"], f"{S['meals_delivered']} delivered · {S['meals_open']} still open", "🍱"),
        ("Skipped / cancelled", f"{S['skipped']} / {S['cancelled']}", "Meals not cooked", "⏭️", True),
        ("Subscription sales", rupees(S["sub_value"]), f"{S['sub_count']} plan(s) purchased", "🔁"),
    ])
    stat_row([
        ("Recorded payments", rupees(S["payments"]), "Net of refunds", "💰"),
        ("Outstanding dues", rupees(S["dues"]), "On this month's billing", "⏳", True),
        ("One-day order value", rupees(S["billed_oneday"]), "Billed (excl. skipped/cancelled)", "🛒"),
        ("Collection rate", f"{(100 * (S['billed_oneday'] + S['sub_value'] - S['dues']) / max(S['billed_oneday'] + S['sub_value'], 1)):.0f}%",
         "Of this month's billing, paid so far", "📊"),
    ])

    left, right = st.columns([1.3, 1], gap="large")
    with left, st.container(key="card_income"):
        html('<div class="eyebrow">Monthly income summary</div>')
        html(f"""<table class="tbl">
          <tr><th>Source</th><th class="num">Billed in period</th><th class="num">Received in period</th><th class="num">Outstanding</th></tr>
          <tr><td>One-day orders</td><td class="num">{rupees(S['billed_oneday'])}</td><td class="num">{rupees(S['rec_oneday'])}</td><td class="num">{rupees(S['due_oneday'])}</td></tr>
          <tr><td>Subscriptions</td><td class="num">{rupees(S['sub_value'])}</td><td class="num">{rupees(S['rec_sub'])}</td><td class="num">{rupees(S['due_sub'])}</td></tr>
          <tr><td>Refunds</td><td class="num">—</td><td class="num">{rupees(S['refunds'])}</td><td class="num">—</td></tr>
          <tr class="tot"><td>Total</td><td class="num">{rupees(S['billed_oneday'] + S['sub_value'])}</td>
            <td class="num">{rupees(S['payments'])}</td><td class="num">{rupees(S['dues'])}</td></tr></table>
          <p class="small" style="margin-top:.5rem">Income = money received in the month. "Received" can include payments for
          earlier billing; "Outstanding" is what is still unpaid on this month's billing. Plan meals are not billed separately.</p>""")
    with right, st.container(key="card_downloads"):
        html('<div class="eyebrow">CSV downloads</div><div class="h2">Export this month</div>')
        tag = f"{p['name'].lower().replace(' ', '_').replace(chr(39), '').replace('.', '')}_{ym}"
        st.download_button(f"⬇  Monthly order report ({len(R['orders'])} rows)", to_csv(R["orders"]),
                           file_name=f"orders_{tag}.csv", mime="text/csv", key="dl_orders", width="stretch")
        st.download_button(f"⬇  Income / payment report ({len(R['payments'])} rows)", to_csv(R["payments"]),
                           file_name=f"income_payments_{tag}.csv", mime="text/csv", key="dl_pay", width="stretch")
        st.download_button(f"⬇  Customer subscription report ({len(R['subs'])} rows)", to_csv(R["subs"]),
                           file_name=f"subscriptions_{tag}.csv", mime="text/csv", key="dl_subs", width="stretch")
        html('<p class="small" style="margin-top:.4rem">UTF-8 CSV with headers · opens in Excel or Google Sheets. '
             'Subscriptions included = plans valid at any point in the month.</p>')

    st.write("")
    html('<div class="eyebrow">Analytics</div><div class="h2">Trends for the month</div>')
    last = min(m1, today() + timedelta(days=SCHEDULE_DAYS_AHEAD))
    days = [m0 + timedelta(days=k) for k in range((last - m0).days + 1)] if last >= m0 else []
    if days:
        g = {"Delivered / ready": ("Prepared", "Out for delivery", "Delivered"), "Open": ("Confirmed", "Preparing"),
             "Skipped": ("Skipped",), "Cancelled": ("Cancelled",)}
        daily = pd.DataFrame({"Day": [f"{d:%d %b}" for d in days], **{
            k: [sum(o["qty"] for o in R["raw_orders"] if o["date"] == d and o["status"] in v) for d in days] for k, v in g.items()}})
        rev = pd.DataFrame({"Day": [f"{d:%d %b}" for d in days],
                            "Income (₹)": [sum(x["amount"] for x in R["raw_pays"] if x["at"].date() == d) for d in days]})
        c1, c2 = st.columns(2, gap="large")
        with c1, st.container(key="card_ch1"):
            html('<div style="font-weight:700">Daily meals by status</div>')
            st.bar_chart(daily, x="Day", y=list(g), color=["#2B6A4F", "#8FB39B", "#D9A27F", "#B5603F"], stack=True,
                         height=260, x_label="", y_label="Meals", sort=False)
        with c2, st.container(key="card_ch2"):
            html('<div style="font-weight:700">Income by day (recorded payments)</div>')
            st.bar_chart(rev, x="Day", y="Income (₹)", color="#B5603F", height=260, x_label="", y_label="₹", sort=False)
        counts = pd.DataFrame({"Status": STATUSES, "Orders": [sum(1 for o in R["raw_orders"] if o["status"] == s) for s in STATUSES]})
        with st.container(key="card_ch3"):
            html('<div style="font-weight:700">Order status breakdown</div>')
            st.bar_chart(counts, x="Status", y="Orders", color="#1F4D3A", height=230, x_label="", sort=False)
    with st.expander("Preview the order report"):
        st.dataframe(R["orders"], hide_index=True, width="stretch", height=300)


def o_profile(p: dict) -> None:
    pid = p["id"]
    page_header("Kitchen profile", "Your public profile",
                "Changes appear immediately on your customer-facing page and in Discover.")
    v = st.session_state.ver
    left, right = st.columns([1.5, 1], gap="large")
    with left, st.container(key=f"card_kp_{pid}_{v}"):
        st.text_area("Service description", p["description"], key="kp_desc", height=90)
        a, b, c = st.columns(3)
        a.selectbox("Locality", LOCALITIES, index=LOCALITIES.index(p["locality"]), key="kp_loc")
        b.text_input("Cuisine", p["cuisine"], key="kp_cuisine")
        diets = ["Veg", "Non-Veg", "Veg & Non-Veg"]
        c.selectbox("Food type", diets, index=diets.index(p["diet"]), key="kp_diet")
        a, b = st.columns(2)
        a.multiselect("Meals served", SLOTS, default=p["slots"], key="kp_slots")
        b.multiselect("Delivers to", LOCALITIES, default=p["delivers_to"], key="kp_delivers")
        a, b = st.columns(2)
        a.number_input("Lunch price per meal (₹)", 0, 1000, int(p["prices"]["Lunch"]), step=5, key="kp_price_Lunch")
        b.number_input("Dinner price per meal (₹)", 0, 1000, int(p["prices"]["Dinner"]), step=5, key="kp_price_Dinner")
        a, b = st.columns(2)
        a.text_input("Contact phone (fictional)", p["phone"], key="kp_phone")
        b.text_input("Contact email", p["email"], key="kp_email")
        html('<div class="eyebrow" style="margin-top:.5rem">Availability</div>')
        a, b = st.columns(2)
        a.toggle("Accepting one-day orders", p["accepting_orders"], key="kp_orders")
        b.toggle("Accepting new subscriptions", p["accepting_subs"], key="kp_subs")
        a, b = st.columns(2)
        a.number_input("Capacity per meal (tiffins)", 1, 300, int(p["capacity"]), key="kp_cap")
        b.number_input("Order & skip cutoff (hours before delivery)", 1, 12, int(p["cutoff_hours"]), key="kp_cutoff")
        st.button("Save profile", key="kp_save", type="primary", on_click=cb_save_kitchen, args=(pid,))
        html('<p class="small">Price changes apply to new menu items and new subscriptions. Existing orders and plans keep '
             'their original price.</p>')
    with right:
        html('<div class="eyebrow">Customer view preview</div>')
        provider_card_preview(p)


def provider_card_preview(p: dict) -> None:
    price_from = min((p["prices"][s] for s in p["slots"]), default=0)
    with st.container(key=f"card_prev_{p['id']}"):
        html(f"""<div class="pc-head"><div class="pc-icon">{p['icon']}</div>
            <div><div class="pc-name">{esc(p['name'])}</div><div class="pc-meta">📍 {esc(p['locality'])} · {esc(p['cuisine'])} · ⭐ {p['rating']} (demo)</div></div>
            <div class="pc-price"><b>from {rupees(price_from)}</b><span>per meal</span></div></div>
          <div class="pc-desc">{esc(p['description'])}</div>
          <div>{diet_chip(p['diet'])}{''.join(f'<span class="chip grey">{SLOT_ICON[s]} {s} {rupees(p["prices"][s])}</span>' for s in p['slots'])}</div>
          <div class="small" style="margin-top:.4rem">🛵 {esc(', '.join(p['delivers_to']))} · 📞 {esc(p['phone'])}<br>
          {'✅ Taking orders' if p['accepting_orders'] else '⛔ Not taking orders'} · {'✅ Subscriptions open' if p['accepting_subs'] else '⛔ Subscriptions full'}
          · ⏱️ cutoff {p['cutoff_hours']}h</div>""")


# =============================================================================
# 9. MAIN
# =============================================================================

def main() -> None:
    init_state()
    st.markdown(CSS, unsafe_allow_html=True)
    if st.session_state.role == "customer":
        render_customer()
    elif st.session_state.role == "owner":
        render_owner()
    else:
        render_landing()


main()
