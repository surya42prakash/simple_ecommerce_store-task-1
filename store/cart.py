"""Session-based shopping cart. Only product ids and quantities are stored in the
session; prices and totals are always read from the database."""
from decimal import Decimal

from .models import Product

SESSION_KEY = "cart"
MAX_PER_LINE = 999


class CartError(Exception):
    """Raised for user-facing cart problems (stock, availability)."""


class Cart:
    def __init__(self, request):
        self.session = request.session
        raw = self.session.get(SESSION_KEY)
        self.data = {}
        if isinstance(raw, dict):
            for key, qty in raw.items():
                if str(key).isdigit() and isinstance(qty, int) and qty > 0:
                    self.data[str(key)] = qty

    # -- helpers -----------------------------------------------------------
    def _save(self):
        self.session[SESSION_KEY] = self.data
        self.session.modified = True

    def quantity_of(self, product):
        return self.data.get(str(product.pk), 0)

    # -- mutations ---------------------------------------------------------
    def add(self, product, quantity=1):
        if not product.is_active:
            raise CartError(f"{product.name} is not available.")
        if product.stock <= 0:
            raise CartError(f"{product.name} is out of stock.")
        new_qty = self.quantity_of(product) + quantity
        if new_qty > product.stock:
            raise CartError(
                f"Only {product.stock} unit(s) of {product.name} available "
                f"(you already have {self.quantity_of(product)} in your cart)."
            )
        self.data[str(product.pk)] = new_qty
        self._save()

    def set_quantity(self, product, quantity):
        if quantity <= 0:
            self.remove(product)
            return
        if quantity > product.stock:
            raise CartError(f"Only {product.stock} unit(s) of {product.name} available.")
        self.data[str(product.pk)] = quantity
        self._save()

    def remove(self, product):
        self.data.pop(str(product.pk), None)
        self._save()

    def clear(self):
        self.data = {}
        self.session.pop(SESSION_KEY, None)
        self.session.modified = True

    # -- reading -----------------------------------------------------------
    def items(self):
        """List of dicts with product, quantity, unit_price, subtotal (from the DB)."""
        products = Product.objects.filter(pk__in=[int(k) for k in self.data], is_active=True)
        by_id = {str(p.pk): p for p in products}
        rows = []
        for key, qty in self.data.items():
            product = by_id.get(key)
            if product is None:
                continue  # product deleted/deactivated since it was added
            rows.append(
                {
                    "product": product,
                    "quantity": qty,
                    "unit_price": product.price,
                    "subtotal": product.price * qty,
                    "over_stock": qty > product.stock,
                }
            )
        return rows

    def total(self):
        return sum((row["subtotal"] for row in self.items()), Decimal("0.00"))

    def __len__(self):
        return sum(self.data.values())
