from .cart import Cart
from .models import Category


def store_globals(request):
    return {
        "cart_count": len(Cart(request)),
        "nav_categories": Category.objects.all(),
    }
