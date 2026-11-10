import logging

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.contrib.messages.views import SuccessMessageMixin
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .cart import MAX_PER_LINE, Cart, CartError
from .forms import CheckoutForm, RegistrationForm
from .models import Category, Order, Product
from .services import place_order

logger = logging.getLogger(__name__)


def _active_products():
    return Product.objects.filter(is_active=True).select_related("category")


def _parse_quantity(raw, minimum=1):
    try:
        qty = int(raw)
    except (TypeError, ValueError):
        raise ValueError("Please enter a valid whole-number quantity.")
    if qty < minimum or qty > MAX_PER_LINE:
        raise ValueError(f"Quantity must be between {minimum} and {MAX_PER_LINE}.")
    return qty


def _safe_next(request, default):
    target = request.POST.get("next") or request.GET.get("next") or ""
    if target and url_has_allowed_host_and_scheme(
        target, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return target
    return default


# --------------------------------------------------------------- catalogue
def home(request):
    products = _active_products()
    context = {
        "featured": products.filter(is_featured=True)[:4],
        "latest": products[:8],
        "categories": Category.objects.all(),
    }
    return render(request, "home.html", context)


def product_list(request):
    products = _active_products()
    q = request.GET.get("q", "").strip()
    category_slug = request.GET.get("category", "").strip()
    sort = request.GET.get("sort", "")
    current_category = None

    if q:
        products = products.filter(Q(name__icontains=q) | Q(description__icontains=q))
    if category_slug:
        current_category = Category.objects.filter(slug=category_slug).first()
        products = products.filter(category=current_category) if current_category else products.none()
    products = products.order_by(
        {"price_asc": "price", "price_desc": "-price", "name": "name"}.get(sort, "-created_at")
    )

    page = Paginator(products, 12).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    context = {
        "page_obj": page,
        "q": q,
        "sort": sort,
        "current_category": current_category,
        "categories": Category.objects.all(),
        "querystring": params.urlencode(),
    }
    return render(request, "product_list.html", context)


def product_detail(request, slug):
    product = get_object_or_404(_active_products(), slug=slug)
    related = (
        _active_products().filter(category=product.category).exclude(pk=product.pk)[:4]
        if product.category_id
        else []
    )
    return render(
        request,
        "product_detail.html",
        {"product": product, "related": related, "in_cart": Cart(request).quantity_of(product)},
    )


# -------------------------------------------------------------------- cart
def cart_detail(request):
    cart = Cart(request)
    return render(request, "cart.html", {"items": cart.items(), "total": cart.total()})


@require_POST
def cart_add(request, pk):
    product = get_object_or_404(Product, pk=pk, is_active=True)
    try:
        qty = _parse_quantity(request.POST.get("quantity", 1))
        Cart(request).add(product, qty)
        messages.success(request, f"Added {qty} x {product.name} to your cart.")
    except (ValueError, CartError) as exc:
        messages.error(request, str(exc))
    return redirect(_safe_next(request, "cart_detail"))


@require_POST
def cart_update(request, pk):
    product = get_object_or_404(Product, pk=pk)
    try:
        qty = _parse_quantity(request.POST.get("quantity"), minimum=0)
        Cart(request).set_quantity(product, qty)
        messages.success(request, "Cart updated.")
    except (ValueError, CartError) as exc:
        messages.error(request, str(exc))
    return redirect("cart_detail")


@require_POST
def cart_remove(request, pk):
    product = get_object_or_404(Product, pk=pk)
    Cart(request).remove(product)
    messages.success(request, f"Removed {product.name} from your cart.")
    return redirect("cart_detail")


# -------------------------------------------------------------------- auth
def register(request):
    if request.user.is_authenticated:
        return redirect("home")
    form = RegistrationForm(request.POST or None)
    if request.method == "POST":
        if form.is_valid():
            user = form.save()
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
            messages.success(request, f"Registration successful. Welcome, {user.username}!")
            return redirect(_safe_next(request, "home"))
        messages.error(request, "Please correct the errors below.")
    return render(request, "register.html", {"form": form, "next": request.GET.get("next", "")})


class StoreLoginView(SuccessMessageMixin, auth_views.LoginView):
    template_name = "registration/login.html"
    redirect_authenticated_user = True
    success_message = "Login successful. Welcome back, %(username)s!"

    def form_invalid(self, form):
        messages.error(self.request, "Invalid username or password.")
        return super().form_invalid(form)


# ------------------------------------------------------------------ orders
@login_required
def checkout(request):
    cart = Cart(request)
    items = cart.items()
    if not items:
        messages.info(request, "Your cart is empty. Add something before checking out.")
        return redirect("cart_detail")

    if request.method == "POST":
        form = CheckoutForm(request.POST)
        if form.is_valid():
            try:
                order = place_order(request.user, cart, form)
            except CartError as exc:
                messages.error(request, str(exc))
                return redirect("cart_detail")
            except Exception:  # transaction already rolled back
                logger.exception("Unexpected error while placing an order")
                messages.error(
                    request, "Something went wrong and your order was not placed. Please try again."
                )
                return redirect("cart_detail")
            cart.clear()
            messages.success(request, f"Order {order.order_number} placed successfully!")
            return redirect("order_confirmation", order_number=order.order_number)
        messages.error(request, "Please correct the errors below.")
    else:
        form = CheckoutForm(
            initial={
                "email": request.user.email,
                "customer_name": request.user.get_full_name(),
            }
        )
    return render(request, "checkout.html", {"form": form, "items": items, "total": cart.total()})


def _own_order(request, order_number):
    return get_object_or_404(
        Order.objects.prefetch_related("items"), order_number=order_number, user=request.user
    )


@login_required
def order_confirmation(request, order_number):
    return render(request, "order_confirmation.html", {"order": _own_order(request, order_number)})


@login_required
def order_history(request):
    orders = request.user.orders.prefetch_related("items")
    page = Paginator(orders, 10).get_page(request.GET.get("page"))
    return render(request, "order_history.html", {"page_obj": page})


@login_required
def order_detail(request, order_number):
    return render(request, "order_detail.html", {"order": _own_order(request, order_number)})
