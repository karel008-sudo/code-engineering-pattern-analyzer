"""
Human-written service fixture — represents less structured, more organic code.

Expected: lower type coverage, fewer docstrings, more pragmatic style.
Expected score band: low (0.10–0.30 adjusted).
"""
import logging
from datetime import datetime

log = logging.getLogger(__name__)


class OrderSvc:
    def __init__(self, repo, notif=None):
        self.repo = repo
        self.notif = notif
        self._cache = {}
        self.last_error = None

    def create(self, cust_id, items, addr):
        # quick validation
        if not cust_id or not items:
            return None

        order = {
            'cust': cust_id,
            'items': items,
            'addr': addr,
            'created': datetime.now(),
            'status': 'pending'
        }

        try:
            res = self.repo.save(order)
            log.info('created order %s', res.get('id'))
            if self.notif:
                self.notif.notify(cust_id, res)
            return res
        except Exception as e:
            log.error('save failed: %s', e)
            self.last_error = str(e)
            return None

    def cancel(self, oid, reason=None):
        order = self.repo.find(oid)
        if not order:
            return False
        if order['status'] in ('shipped', 'delivered'):
            return False
        order['status'] = 'cancelled'
        if reason:
            order['cancel_reason'] = reason
        self.repo.save(order)
        return True

    def get_for_cust(self, cid, status=None):
        res = self.repo.find_by_cust(cid) or []
        if status:
            res = [o for o in res if o['status'] == status]
        return res

    def _refresh_cache(self, order_id):
        # TODO: implement proper cache invalidation
        if order_id in self._cache:
            del self._cache[order_id]
