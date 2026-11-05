# Assessment Assumptions

> Submitted by Khalilur Rahman (khal.rahman@gmail.com)

- This is a fictional USD store, Thread & Harbor. Refunds, exchanges, cancellations, and human escalations are local simulations; no payments, shipping, or email are sent.
- The CLI customer ID or guest email represents identity verified upstream. It is not authentication. Messages cannot change identity; emails match case-insensitively. Unknown identities receive no order information.
- Returns include refunds and exchanges. Eligibility is delivery day through day 30 inclusive, using UTC calendar dates. Undelivered items cannot return. Defects do not extend the window.
- A customer's explicit affirmative defect description is sufficient in this simulation. A complete verbatim customer sentence containing a supported defect term (defective, damaged, torn, ripped, broken, hole, stain, or faulty) is required for sale refunds. It must name the targeted product/type or unit ID and affirm its condition (for example, “My hoodie is torn.”); policy questions and other-product defects do not qualify. Negated, hypothetical, or unclear descriptions require clarification/human review. This is not independent defect verification.
- Refunds use each unit's actual net paid price after discounts, in integer cents. Shipping is not refundable; no separate tax or restocking fee is modeled. A return request authorizes a simulated immediate refund without warehouse inspection.
- Exchanges use another in-stock size of the same product, with no price difference. Stock is reserved atomically; returned stock is not immediately resellable. Same-size replacements require human review. Exchanged units consume the original entitlement and cannot be refunded again.
- Cancellation is whole-order and unshipped only. It refunds remaining paid item value. Cancelled orders cannot be cancelled/refunded twice.
- Each purchased unit has a stable ID, allowing partial returns. Multiple ambiguous items/units require clarification. After a prior action on an identical line, an additional return must name the remaining unit ID explicitly; a vague retry must not consume another unit.
- Orders and fixtures use fixed dates around 2026-11-04. Production uses actual UTC today; SUPPORT_TODAY is an operator-only evaluation clock. Customers cannot set it through messages.
- SQLite state and action receipts persist across processes. A serialized write transaction covers validation, stock/entitlement changes, and ledger insertion. There is no real payment-provider failure boundary.
- One structured model proposal per message bounds cost and avoids speculative multi-action execution. Ask the customer to submit distinct actions separately. Last 12 history entries and last 12 receipts are provided as context; the complete ledger is retained locally.
- OpenRouter is the selected provider; OPENROUTER_MODEL defaults to openai/gpt-4o-mini. Requests force one support_response tool proposal. Keys are read from environment variables (optionally loaded from ignored .env). No credentials are included in artifacts. Offline scripted checks verify application safeguards, not unseen-message model quality.
- Human escalation means a durable local queue receipt; no actual human notification or SLA is provided.
