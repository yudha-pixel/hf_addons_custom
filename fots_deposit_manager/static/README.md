# Heritage Foods — FOTS Field Sales Manager

## Overview

Lean **B2B wholesale ("Buy-and-Go")** module for Heritage Foods' Feet-On-The-Street
(FOTS) agents on Odoo 19 CE. FOTS agents are treated as independent wholesale
customers who come to the office, pay upfront (cash or transfer), and walk out
with the goods — no deposits, no reward system, no daily reconciliation.

## Scope

This module only does three things:

1. **Master data** — FOTS Teams and FOTS Agents (linked 1:1 to `res.partner`).
2. **Buy-and-Go action on `sale.order`** — a single button that confirms the
   order, validates the delivery, posts the customer invoice, and registers
   the payment in one click.
3. **Reporting** — reuses `sale.order` pivot/graph grouped by FOTS agent and
   team.

Returns, credit notes, and accounting corrections use **native Odoo** features
(no custom flow).

## Models

| Model | Purpose |
|---|---|
| `fots.team` | Group of agents under a manager, tied to one warehouse. |
| `fots.agent` | Agent profile; auto-creates its own `res.partner` and optionally carries a default `pricelist_id`. |
| `sale.order` (inherited) | Adds `fots_agent_id`, `fots_team_id`, and `action_fots_buy_and_go`. |

## Configuration

1. Install the module.
2. Create a pricelist for FOTS wholesale pricing (e.g. ₦20,000 per Dozen) —
   standard Odoo pricelist, no custom screen.
3. Set the G-Flakes product's default UoM to **Dozen**.
4. Create at least one `FOTS Team` (menu **FOTS → Master Data → Teams**) with
   the responsible warehouse.
5. Create `FOTS Agents` under that team. Assign the default pricelist on each
   agent.

## Buy-and-Go Flow

1. Admin opens **FOTS → Operations → Sales Orders** and creates a new quote.
2. Select the agent in `FOTS Agent` — the customer and pricelist fill
   automatically.
3. Add product lines in **Dozen** (quantity only).
4. Click **Buy & Go** in the header.

In one shot the system:

- Confirms the sale order.
- Validates every outgoing picking (no backorder).
- Creates and posts the customer invoice.
- Registers the full payment using the default company journal.

No follow-up action is required.

## Returns

Use native Odoo flows:

- **Credit Note** on the posted invoice to reverse the charge.
- **Return** on the delivery picking to bring stock back.

## Security

- `FOTS Manager` — full access to teams and agents.
- `FOTS User` — read-only on other agents, read-write on their own profile,
  and able to trigger Buy-and-Go on sale orders.

## Installation

```
Settings → Apps → Update Apps List → Install "Heritage Foods - FOTS Field Sales Manager"
```

Depends on core modules only: `base`, `mail`, `stock`, `uom`, `product`,
`sale`, `account`.

## License

LGPL-3
