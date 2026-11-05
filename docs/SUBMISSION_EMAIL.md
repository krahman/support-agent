# Submission Email Draft — Not Sent

> Submitted by Khalilur Rahman (khal.rahman@gmail.com)

Review and rewrite this draft in your own words before sending it yourself.

To: hiring@gomaxify.ai
Subject: Apparel customer-support agent assessment
Attachment: apparel-support-agent.zip

Hello,

Attached is my fictional apparel customer-support agent, including data, source, evals, retained run evidence, README, and assumptions.

The worst failure I found was an unauthorized sale-item refund. The customer said the hoodie was **not defective**, but the model proposed a quote containing just “defective.” My initial executor checked that this substring appeared in the message, then checked the shortened quote for negation. That discarded the word “not” and allowed a $32 refund. I fixed the evidence check to require the full original customer sentence, then added a regression test. The original failing and subsequent passing eval reports are included; details are in docs/FAILURE_ANALYSIS.md.

Refunds are actually executed as a local simulation in `support/executor.py`, in `execute`, at the `REFUND EXECUTION` comment. The code computes the amount from stored paid unit values, marks those units consumed, and appends a receipt atomically through `Store.transaction`. The model only proposes arguments. Application checks enforce ownership, delivery window, sale/defect policy, quantities, stock, and prior processing; it cannot directly change balances or supply prices.

The ordinary CLI uses OpenRouter. Offline tests pass (55/55) and the live OpenRouter suite passes (6/6). Live testing also exposed a model quirk: it sometimes copied a prompt example as its defect quote, which the executor safely denied; I removed the example from the prompt. See docs/VERIFICATION.md and docs/FAILURE_ANALYSIS.md.

Thank you,
[Your name]
