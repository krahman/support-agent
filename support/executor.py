"""The sole authority for simulated monetary and stock changes."""
from datetime import date, datetime, timezone
import os
import re
import uuid


class PolicyError(Exception):
    pass


def today():
    return date.fromisoformat(os.environ['SUPPORT_TODAY']) if os.environ.get('SUPPORT_TODAY') else datetime.now(timezone.utc).date()


def lookup(state, customer, order_id=None):
    if os.environ.get('SUPPORT_LOOKUP_FAIL') == '1':
        raise PolicyError('Order lookup unavailable; human review is required.')
    orders = [o for o in state['orders'] if o['customer_id'] == customer]
    if order_id is None:
        return orders
    order = next((o for o in orders if o['id'] == order_id), None)
    if order is None:
        raise PolicyError('Order not found for this identity.')
    return order


def defect_claim(quote, customer_messages, target_labels=()):
    """Require verbatim customer evidence, rather than a model-supplied boolean."""
    if not isinstance(quote, str) or not quote.strip():
        return False
    # A substring can discard negation (e.g. quote 'defective' from 'not defective').
    # Require the complete original sentence, tolerating terminal punctuation only.
    normalized = quote.strip().rstrip('.!?').strip()
    sentences = [part.strip().rstrip('.!?').strip()
                 for message in customer_messages
                 for part in re.split(r'(?<=[.!?])\s+|[\r\n]+', message)]
    if normalized not in sentences:
        return False
    text = normalized.lower()
    if re.search(r'\b(not|no|never|isn.t|aren.t|wasn.t|weren.t|don.t|doesn.t|pretend|ignore|imagine|hypothetical|say|claim|if|unless|suppose|might|could)\b', text):
        return False
    if '?' in quote:
        return False
    if target_labels and not any(re.search(r'\b' + re.escape(label.lower()) + r'\b', text) for label in target_labels):
        return False
    # Require an affirmative report of an item's condition, not a policy mention.
    return bool(re.search(r'\b(is|has|was|arrived|came|received)\b.{0,100}\b(defective|damaged|torn|ripped|broken|hole|stain|faulty)\b', text))


def execute(store, customer, action, customer_messages):
    """Validate untrusted arguments; commit state and receipt atomically.

    No external payment is sent. The ledger append below executes the simulation.
    """
    try:
        if not isinstance(action, dict):
            raise PolicyError('Invalid action arguments.')
        allowed = {'kind', 'order_id', 'unit_ids', 'replacement_variant', 'defect_quote'}
        if set(action) - allowed:
            raise PolicyError('Unexpected action fields; prices and quantities come from order units.')
        kind = action.get('kind')
        if kind not in ('refund', 'exchange', 'cancellation'):
            raise PolicyError('Unsupported action.')
        if not isinstance(action.get('order_id'), str):
            raise PolicyError('Clarify the order to act on.')
        unit_ids = action.get('unit_ids', [])
        if not isinstance(unit_ids, list) or not all(isinstance(u, str) for u in unit_ids) or len(unit_ids) != len(set(unit_ids)):
            raise PolicyError('Unit identifiers must be a list of distinct strings.')
        with store.transaction() as state:
            order = lookup(state, customer, action['order_id'])
            if kind == 'cancellation':
                if unit_ids:
                    raise PolicyError('Cancellation is whole-order; omit unit identifiers.')
                if order['status'] == 'cancelled':
                    receipt = next(r for r in state['ledger'] if r['order_id'] == order['id'] and r['kind'] == kind)
                    return dict(receipt, status='already_processed')
                if order['status'] != 'unshipped':
                    raise PolicyError('Only unshipped orders can be cancelled.')
                units = [u for u in order['units'] if u['status'] == 'available']
            else:
                if not unit_ids:
                    raise PolicyError('Clarify the item and units to return.')
                units = [u for u in order['units'] if u['id'] in unit_ids]
                if len(units) != len(unit_ids):
                    raise PolicyError('An item does not belong to this order.')
                consumed = [u for u in units if u['status'] != 'available']
                if consumed:
                    prior = [r for r in state['ledger'] if set(unit_ids) <= set(r['unit_ids']) and r['order_id'] == order['id']]
                    if len(consumed) == len(units) and prior:
                        return dict(prior[-1], status='already_processed')
                    raise PolicyError('Some selected units were already processed; clarify the remaining units.')
                # A vague rephrasing must not silently consume a second identical unit.
                for unit in units:
                    siblings = [u for u in order['units'] if u['line_id'] == unit['line_id'] and u['status'] != 'available']
                    if siblings and unit['id'] not in customer_messages[-1]:
                        raise PolicyError('This line has a prior action. Specify the remaining unit ID explicitly to start a new return.')
                if order['status'] != 'delivered' or not order['delivered_on']:
                    raise PolicyError('Returns require delivery.')
                elapsed = (today() - date.fromisoformat(order['delivered_on'])).days
                if not 0 <= elapsed <= state['policies']['return_days']:
                    raise PolicyError('Return window is 30 days from delivery, inclusive.')
                if kind == 'refund' and any(u['sale'] for u in units):
                    for unit in (u for u in units if u['sale']):
                        product = next(p for p in state['products'] if p['id'] == unit['product_id'])
                        labels = (unit['id'], product['id'], product['name'], product['name'].split()[-1])
                        if not defect_claim(action.get('defect_quote', ''), customer_messages, labels):
                            raise PolicyError('Sale items are exchange-only unless explicitly reported defective. Describe the targeted product and defect in a complete affirmative sentence, or request an exchange.')
                if kind == 'exchange':
                    variant = action.get('replacement_variant')
                    if not isinstance(variant, str) or not variant:
                        raise PolicyError('Clarify the replacement size/variant.')
                    # Validate aggregate stock before modifying any product.
                    needed = {}
                    for unit in units:
                        if variant == unit['variant']:
                            raise PolicyError('Choose a different variant or escalate a same-size replacement.')
                        needed[unit['product_id']] = needed.get(unit['product_id'], 0) + 1
                    for pid, count in needed.items():
                        product = next(p for p in state['products'] if p['id'] == pid)
                        if product['variants'].get(variant, 0) < count:
                            raise PolicyError('Replacement variant unavailable; choose another variant or request human review.')
                    for pid, count in needed.items():
                        next(p for p in state['products'] if p['id'] == pid)['variants'][variant] -= count
            if not units:
                raise PolicyError('No remaining eligible units.')
            amount = sum(u['paid_cents'] for u in units) if kind != 'exchange' else 0
            if any(type(u['paid_cents']) is not int or u['paid_cents'] < 0 for u in units):
                raise PolicyError('Invalid stored paid value; human review required.')
            for unit in units:
                unit['status'] = kind
            if kind == 'cancellation':
                order['status'] = 'cancelled'
            receipt = {'id': str(uuid.uuid4()), 'kind': kind, 'status': 'executed',
                       'simulated': True, 'customer_id': customer, 'order_id': order['id'],
                       'unit_ids': [u['id'] for u in units], 'amount_cents': amount,
                       'currency': order['currency'], 'date': today().isoformat()}
            if kind == 'exchange':
                receipt['replacement_variant'] = action['replacement_variant']
            if action.get('defect_quote'):
                receipt['defect_quote'] = action['defect_quote'][:500]
            # REFUND EXECUTION: this ledger entry and consumed units commit together.
            state['ledger'].append(receipt)
            return receipt
    except PolicyError as exc:
        return {'kind': action.get('kind', 'unknown') if isinstance(action, dict) else 'unknown',
                'status': 'denied', 'reason': str(exc), 'amount_cents': 0}
