# 🍱 Tiffin Connect Pro — Prototype 2

**Homely meals, hassle-free.**

A working Streamlit prototype for a Design Thinking project. It connects Pune's home tiffin kitchens with the students, working professionals and people living alone who depend on them.

> **Demonstration prototype, not a production app.** All kitchens, people, ratings, prices, orders and payments are fictional. The app has no real login, no real payments, no GPS and no messaging. Data lives in the Streamlit session: it resets when the browser session ends or when you press **Reset demo data**. Nothing is stored permanently.

---

## Install and run

You need **Python 3.10 or newer**.

```bash
cd tiffin-connect-pro

# optional but recommended: a virtual environment
python -m venv .venv
.venv\Scripts\activate            # Windows
source .venv/bin/activate         # macOS / Linux

pip install -r requirements.txt
streamlit run app.py
```

The app opens at **http://localhost:8501**. If `streamlit` isn't found, run `python -m streamlit run app.py`.

Keep the `.streamlit/` folder next to `app.py`. It locks the light theme so the colours look right even on a laptop in dark mode.

---

## The demo clock

The app runs on a **fixed demo date: Tuesday 20 October 2026**. The default demo time is **09:30**, and you can change it from the sidebar ("Demo time"). Because of this, cutoffs, "today", reports and expiry dates behave the same way in every presentation, whatever the real date or time.

- Lunch is delivered at 13:00 and dinner at 20:00.
- **Cutoff** = delivery time minus the kitchen's notice hours (set in Kitchen profile; 3 hours for most kitchens). Aaji's Kitchen's lunch cutoff is therefore 10:00 and its dinner cutoff is 17:00.
- At 09:30 today's lunch can still be skipped. Change the time to 10:30 and the Skip button for that lunch locks.

---

## 10-step presentation script

| # | Role | What to do | What it shows |
|---|---|---|---|
| 1 | Customer (Riya, Wakad) | **Discover kitchens.** Try the Locality, Price and Meal type filters. Open **Aaji's Kitchen**. | Discovery and filters |
| 2 | Customer | View **today's menu**, with lunch and dinner listed separately, prices and cutoff times. | Daily menu |
| 3 | Customer | Scroll to **Subscription packages**. Keep *Lunch · 3 months · start today · UPI (simulated)* and click **Activate**. | 78 meals, valid 20 Oct 2026 → 19 Jan 2027, ₹7,410 |
| 4 | Customer | Go back to the kitchen. Today's lunch is now blocked because the plan covers it (duplicate protection). Choose a **dinner** item and click **Place order**. | One-day order |
| 5 | Customer | **Skip a meal** → skip tomorrow's plan lunch → confirm. | Cutoff check, confirmation, plan balance kept |
| 6 | Owner (Aaji's Kitchen) | **Switch role** → Continue as Tiffin Owner. The dashboard and live activity feed show Riya's order and her skip. **Orders & deliveries** → *Tomorrow* shows the skip and a lower cooking count. | Owner sees changes immediately |
| 7 | Owner | **Menu** opens on tomorrow (not published). Add an item, edit a price and delete an item, then click **Publish menu**. | Menu management |
| 8 | Customer | Switch back → Aaji's Kitchen → **Tomorrow**. The new menu is visible and orderable. | Published changes reach customers |
| 9 | Owner | **Orders & deliveries** → today → move Riya's dinner through *Start preparing → Mark prepared → Send out → Delivered*. Riya's dashboard tracker follows. | Delivery status updates |
| 10 | Owner | **Reports & CSV** → October 2026 → download the **order report** and the **income/payment report**. | Monthly reporting and CSV export |

Optional extras:
- Set the demo time to 10:30 to show the skip cutoff locking today's lunch.
- Record a due on **Payments & income** and watch the dashboard, payments page and reports update together.
- Turn off "Accepting new subscriptions" in **Kitchen profile** and watch the customer side update.

Press **⟲ Reset demo data** (sidebar) before presenting to start clean.

---

## What's included

### Customer
- **Discover:** 6 fictional kitchens across Wakad, Hinjawadi, Baner, Aundh and Pimple Saudagar. Filters for locality, price range, meal type (lunch/dinner), food type, "subscriptions open" and "delivers to me". Ratings are labelled as demo values.
- **Kitchen page:** profile, contact, delivery areas, cutoff rule, and menus for today and tomorrow (lunch and dinner listed separately with prices). One-day ordering with quantity, simulated payment choice and a delivery note.
- **Subscriptions:** 1, 3, 6, 9 and 12-month packages with price, included meals, discount and validity. Shows active, upcoming and expired plans, remaining meals and payment status.
- **Skip a meal:** eligibility and cutoff time on every meal, a confirmation step, duplicate-skip protection, and locks for meals already being prepared or past the cutoff.
- **Dashboard:** active provider, plan expiry, remaining meals, today's status tracker, upcoming meals, pending dues (with a simulated "Pay" button), recent orders, previous subscriptions and payment history.
- **Profile & settings.**

### Owner
- **Dashboard:** today's confirmed orders, meals to prepare, skipped meals, pending and completed deliveries, active subscribers, daily and monthly income, a preparation plan and a live activity feed. All of it is calculated from the records.
- **Orders & deliveries:**
  - Preparation checklist per meal item, with batch "Start preparing" and "Mark prepared" buttons.
  - A status card for each order with only the valid next steps.
  - "Delivered + cash" records the payment in the same step.
  - Cancel or mark-skipped actions sit in the ⋯ menu.
  - A filterable order-management table.
- **Menu:** add, edit and delete items, set lunch or dinner and the price, copy the previous day's menu, then publish for a chosen date. The draft and the published menu are kept separate, so customers only see published menus.
- **Subscriptions:** plan, start, expiry, total, delivered, scheduled, skipped and remaining meals, plus payment status and a "Record payment" button.
- **Customers:** searchable table with contact placeholder, active plan, orders, outstanding amount and payment status.
- **Payments & income:** daily and monthly income, paid orders, pending dues, a list of outstanding items with "Record payment", and payment records by month.
- **Reports & CSV:** monthly totals, an income summary table, **three CSV downloads**, and charts (daily meals by status, income by day, order status breakdown).
- **Kitchen profile:** description, locality, cuisine, food type, meals served, prices, contact details, delivery areas, availability toggles, capacity and cutoff hours.

---

## Business rules

**Subscriptions**
- Validity runs from the start date to the day before the same date N months later (e.g. 20 Oct + 3 months → 19 Jan).
- Included meals = 26 per month per meal slot (Monday–Saturday delivery, Sundays off).
- Price = per-meal price × included meals − duration discount (0% / 5% / 8% / 10% / 12%), rounded to the nearest ₹10.
- Remaining meals = included − delivered − scheduled. Skipped meals are not deducted, and unused meals lapse at expiry.
- Plan meals are scheduled up to 2 days ahead.

**Order status flow**
`Confirmed → Preparing → Prepared → Out for delivery → Delivered`, with `Confirmed → Skipped / Cancelled` and `Preparing → Cancelled`. Any other transition is rejected. Skipped and cancelled meals never count toward cooking totals.

**Money (no double counting)**
- **Charge (order value):**
  - A one-day order is charged its order value, unless it was skipped or cancelled.
  - A subscription is charged its package price.
  - Plan meals carry ₹0 because their value is already in the subscription price.
- **Payment:** a recorded receipt linked to one charge. Refunds are negative payments; a prepaid order that is skipped or cancelled is refunded automatically.
- **Outstanding** = charge − payments against it.
- **Income** for a period = payments recorded in that period.

**Monthly report period**
- Orders count by meal date.
- Payments count by payment date.
- Subscription sales count by purchase date.
- The subscription CSV lists plans that were valid at any point in the month.

---

## CSV files (Reports & CSV)

| File | Contents |
|---|---|
| `orders_<kitchen>_<YYYY-MM>.csv` | Every order with a meal date in the month: ID, date, slot, customer, contact, locality, meal, type, plan ID, qty, unit price, order value, status, payment status, timestamps |
| `income_payments_<kitchen>_<YYYY-MM>.csv` | Every payment and refund recorded in the month: ID, date, customer, source, reference, description, method, amount |
| `subscriptions_<kitchen>_<YYYY-MM>.csv` | Plans valid during the month: dates, status, meal balances, price, paid to date, outstanding, payment status |

Files are UTF-8 with headers and open in Excel or Google Sheets.

---

## Project structure

```
tiffin-connect-pro/
├── app.py                  # the whole app, in clearly numbered sections
├── requirements.txt        # streamlit, pandas
├── README.md
└── .streamlit/config.toml  # light theme + brand colours
```

Inside `app.py`:
1. Constants and sample data
2. Business rules (pure functions for dates, plans and money)
3. Seed-data builder (deterministic)
4. State helpers and actions (every data change happens in a callback)
5. Styling and UI helpers
6. Landing page
7. Customer pages
8. Owner pages
9. `main()`

To change sample data, edit `PROVIDERS`, `MENU_LIB`, `CUSTOMERS` or `SEED_SUBS` near the top. To move the demo date, change `DEMO_TODAY`.

## Troubleshooting
- **`AttributeError` mentioning `segmented_control` or `width`:** upgrade Streamlit with `pip install -U streamlit`. Version 1.50 or newer is required.
- **Colours look wrong or dark:** make sure `.streamlit/config.toml` sits next to `app.py`, then restart.
- **Everything reset:** session data is cleared when you close the tab or restart Streamlit. This is expected for the prototype.
