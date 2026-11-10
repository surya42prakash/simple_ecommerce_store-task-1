"""Order placement logic. Everything happens inside one database transaction, so a
failure at any step leaves no partial order and no changed stock."""
from decimal import Decimal

from django.db import transaction
from django.db.models import F

from .cart import CartError
from .models import Order, OrderItem, Product


@transaction.atomic
def place_order(user, cart, form):
    ids = [int(k) for k in cart.data]
    # select_for_update() locks the rows on databases that support it
    # (PostgreSQL/MySQL). SQLite serialises writers, so it is safe there too.
    products = {
        p.pk: p
        for p in Product.objects.select_for_update().filter(pk__in=ids, is_active=True)
    }

    lines = []
    for key, qty in cart.data.items():
        product = products.get(int(key))
        if product is None:
            raise CartError("An item in your cart is no longer available.")
        if qty > product.stock:
            raise CartError(
                f"Insufficient stock for {product.name} (only {product.stock} left)."
            )
        lines.append((product, qty))
    if not lines:
        raise CartError("Your cart is empty.")

    order = form.save(commit=False)
    order.user = user
    order.total = Decimal("0.00")
    order.save()

    total = Decimal("0.00")
    for product, qty in lines:
        subtotal = product.price * qty  # price comes from the database, never the browser
        OrderItem.objects.create(
            order=order,
            product=product,
            product_name=product.name,
            unit_price=product.price,
            quantity=qty,
            line_subtotal=subtotal,
        )
        updated = Product.objects.filter(pk=product.pk, stock__gte=qty).update(
            stock=F("stock") - qty
        )
        if not updated:
            raise CartError(f"Insufficient stock for {product.name}.")
        total += subtotal

    order.total = total
    order.save(update_fields=["total"])
    return order
