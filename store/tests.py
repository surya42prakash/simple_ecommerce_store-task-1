from decimal import Decimal
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Category, Order, OrderItem, Product

User = get_user_model()

CHECKOUT_DATA = {
    "customer_name": "Asha Verma",
    "email": "asha@example.com",
    "phone": "9876543210",
    "address": "12 MI Road",
    "city": "Jaipur",
    "state": "Rajasthan",
    "postal_code": "302001",
}


class BaseTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cat = Category.objects.create(name="Electronics")
        cls.cat2 = Category.objects.create(name="Books")
        cls.p1 = Product.objects.create(
            name="Earbuds", description="Wireless audio", price=Decimal("1999.00"),
            stock=5, category=cls.cat, is_featured=True,
        )
        cls.p2 = Product.objects.create(
            name="Python Book", description="Learn coding", price=Decimal("549.50"),
            stock=10, category=cls.cat2,
        )
        cls.hidden = Product.objects.create(
            name="Hidden Item", description="inactive", price=Decimal("10"), stock=5, is_active=False
        )
        cls.user = User.objects.create_user("alice", "alice@example.com", "S3cure-pass-123")
        cls.other = User.objects.create_user("bob", "bob@example.com", "S3cure-pass-123")

    def add(self, product, qty=1):
        return self.client.post(reverse("cart_add", args=[product.pk]), {"quantity": qty})


class CatalogueTests(BaseTestCase):
    def test_homepage_loads(self):
        r = self.client.get(reverse("home"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Earbuds")
        self.assertNotContains(r, "Hidden Item")

    def test_product_list_and_rupee_prices(self):
        r = self.client.get(reverse("product_list"))
        self.assertContains(r, "₹1,999.00")
        self.assertContains(r, "Python Book")

    def test_product_detail_and_inactive_404(self):
        self.assertContains(self.client.get(self.p1.get_absolute_url()), "left in stock")
        self.assertEqual(self.client.get(self.hidden.get_absolute_url()).status_code, 404)
        self.assertEqual(self.client.get("/products/nope/").status_code, 404)

    def test_search_by_name_and_description(self):
        r = self.client.get(reverse("product_list"), {"q": "wireless"})
        self.assertContains(r, "Earbuds")
        self.assertNotContains(r, "Python Book")
        r = self.client.get(reverse("product_list"), {"q": "zzz-nothing"})
        self.assertContains(r, "No products found")

    def test_category_filter(self):
        r = self.client.get(reverse("product_list"), {"category": "books"})
        self.assertContains(r, "Python Book")
        self.assertNotContains(r, "Earbuds")
        r = self.client.get(reverse("product_list"), {"category": "unknown"})
        self.assertContains(r, "No products found")

    def test_out_of_stock_label_and_missing_image(self):
        Product.objects.create(name="Gone", description="d", price=1, stock=0)
        r = self.client.get(reverse("product_list"))
        self.assertContains(r, "Out of stock")
        self.assertContains(r, "placeholder")  # graceful missing-image handling

    def test_slug_is_unique(self):
        a = Product.objects.create(name="Same Name", description="x", price=1)
        b = Product.objects.create(name="Same Name", description="x", price=1)
        self.assertNotEqual(a.slug, b.slug)


class AuthTests(BaseTestCase):
    def test_registration_logs_in_and_hashes_password(self):
        r = self.client.post(reverse("register"), {
            "username": "newuser", "email": "new@example.com",
            "password1": "Tr1cky-Passw0rd!", "password2": "Tr1cky-Passw0rd!",
        }, follow=True)
        self.assertContains(r, "Registration successful")
        user = User.objects.get(username="newuser")
        self.assertNotEqual(user.password, "Tr1cky-Passw0rd!")
        self.assertTrue(user.password.startswith("pbkdf2_"))

    def test_registration_validation(self):
        r = self.client.post(reverse("register"), {
            "username": "x", "email": "alice@example.com", "password1": "123", "password2": "456",
        })
        self.assertContains(r, "Please correct the errors")
        self.assertFalse(User.objects.filter(username="x").exists())

    def test_login_logout(self):
        r = self.client.post(reverse("login"), {"username": "alice", "password": "S3cure-pass-123"}, follow=True)
        self.assertContains(r, "Login successful")
        r = self.client.post(reverse("logout"), follow=True)
        self.assertNotContains(r, "Logout (alice)")

    def test_login_failure(self):
        r = self.client.post(reverse("login"), {"username": "alice", "password": "wrong"})
        self.assertContains(r, "Invalid username or password")


class CartTests(BaseTestCase):
    def test_add_and_totals(self):
        self.add(self.p1, 2)
        self.add(self.p2, 1)
        r = self.client.get(reverse("cart_detail"))
        self.assertContains(r, "₹4,547.50")  # 2*1999 + 549.50
        self.assertEqual(r.context["total"], Decimal("4547.50"))

    def test_cart_count_in_navbar_and_persistence(self):
        self.add(self.p1, 3)
        r = self.client.get(reverse("home"))
        self.assertEqual(r.context["cart_count"], 3)
        r = self.client.get(reverse("product_list"))  # still there on another page
        self.assertEqual(r.context["cart_count"], 3)

    def test_add_same_product_accumulates(self):
        self.add(self.p1, 2)
        self.add(self.p1, 2)
        self.assertEqual(self.client.session["cart"][str(self.p1.pk)], 4)

    def test_update_and_remove(self):
        self.add(self.p1, 1)
        self.client.post(reverse("cart_update", args=[self.p1.pk]), {"quantity": 4})
        self.assertEqual(self.client.session["cart"][str(self.p1.pk)], 4)
        self.client.post(reverse("cart_update", args=[self.p1.pk]), {"quantity": 0})
        self.assertNotIn(str(self.p1.pk), self.client.session.get("cart", {}))
        self.add(self.p2, 1)
        self.client.post(reverse("cart_remove", args=[self.p2.pk]))
        self.assertEqual(self.client.session.get("cart", {}), {})

    def test_invalid_quantities(self):
        for bad in ["abc", "0", "-3", "", "1.5", "99999"]:
            r = self.add(self.p1, bad)
            self.assertEqual(r.status_code, 302)
        self.assertEqual(self.client.session.get("cart", {}), {})
        self.add(self.p1, 1)
        r = self.client.post(reverse("cart_update", args=[self.p1.pk]), {"quantity": "x"}, follow=True)
        self.assertContains(r, "valid whole-number")
        self.assertEqual(self.client.session["cart"][str(self.p1.pk)], 1)

    def test_stock_validation(self):
        r = self.client.post(reverse("cart_add", args=[self.p1.pk]), {"quantity": 6}, follow=True)
        self.assertContains(r, "Only 5 unit(s)")
        self.assertEqual(self.client.session.get("cart", {}), {})
        self.add(self.p1, 5)
        r = self.client.post(reverse("cart_add", args=[self.p1.pk]), {"quantity": 1}, follow=True)
        self.assertContains(r, "Only 5 unit(s)")
        r = self.client.post(reverse("cart_update", args=[self.p1.pk]), {"quantity": 9}, follow=True)
        self.assertContains(r, "Only 5 unit(s)")

    def test_cannot_add_inactive_or_out_of_stock(self):
        self.assertEqual(self.add(self.hidden).status_code, 404)
        oos = Product.objects.create(name="Empty", description="d", price=5, stock=0)
        r = self.client.post(reverse("cart_add", args=[oos.pk]), {"quantity": 1}, follow=True)
        self.assertContains(r, "out of stock")

    def test_empty_cart_page_and_get_not_allowed(self):
        self.assertContains(self.client.get(reverse("cart_detail")), "Your cart is empty")
        self.assertEqual(self.client.get(reverse("cart_add", args=[self.p1.pk])).status_code, 405)

    def test_tampered_session_is_ignored(self):
        s = self.client.session
        s["cart"] = {"abc": 3, str(self.p1.pk): -4, "99999": 2, str(self.p2.pk): 1}
        s.save()
        r = self.client.get(reverse("cart_detail"))
        self.assertEqual(r.context["total"], Decimal("549.50"))

    def test_open_redirect_blocked(self):
        r = self.client.post(reverse("cart_add", args=[self.p1.pk]),
                             {"quantity": 1, "next": "https://evil.example.com/"})
        self.assertEqual(r.url, reverse("cart_detail"))


class CheckoutTests(BaseTestCase):
    def setUp(self):
        self.client.login(username="alice", password="S3cure-pass-123")

    def test_checkout_requires_login(self):
        self.client.logout()
        r = self.client.get(reverse("checkout"))
        self.assertRedirects(r, f"{reverse('login')}?next={reverse('checkout')}")

    def test_order_pages_require_login(self):
        self.client.logout()
        for url in [reverse("order_history"), "/orders/ORD-XXXX/"]:
            self.assertEqual(self.client.get(url).status_code, 302)

    def test_empty_cart_redirects(self):
        self.assertRedirects(self.client.get(reverse("checkout")), reverse("cart_detail"))

    def test_successful_checkout(self):
        self.add(self.p1, 2)
        self.add(self.p2, 1)
        r = self.client.post(reverse("checkout"), CHECKOUT_DATA, follow=True)
        order = Order.objects.get()
        self.assertRedirects(r, reverse("order_confirmation", args=[order.order_number]))
        self.assertContains(r, "placed successfully")
        self.assertEqual(order.user, self.user)
        self.assertEqual(order.total, Decimal("4547.50"))
        self.assertEqual(order.status, Order.Status.PENDING)
        self.assertTrue(order.order_number.startswith("ORD-"))
        items = {i.product_name: i for i in order.items.all()}
        self.assertEqual(items["Earbuds"].unit_price, Decimal("1999.00"))
        self.assertEqual(items["Earbuds"].line_subtotal, Decimal("3998.00"))
        self.assertEqual(items["Python Book"].quantity, 1)
        # stock reduced, cart cleared
        self.p1.refresh_from_db(); self.p2.refresh_from_db()
        self.assertEqual((self.p1.stock, self.p2.stock), (3, 9))
        self.assertEqual(self.client.session.get("cart", {}), {})
        # appears in history
        self.assertContains(self.client.get(reverse("order_history")), order.order_number)

    def test_snapshot_survives_price_change(self):
        self.add(self.p1, 1)
        self.client.post(reverse("checkout"), CHECKOUT_DATA)
        self.p1.price = Decimal("1.00"); self.p1.name = "Renamed"; self.p1.save()
        item = OrderItem.objects.get()
        self.assertEqual((item.product_name, item.unit_price), ("Earbuds", Decimal("1999.00")))

    def test_browser_cannot_set_total(self):
        self.add(self.p1, 1)
        self.client.post(reverse("checkout"), {**CHECKOUT_DATA, "total": "1", "status": "delivered"})
        order = Order.objects.get()
        self.assertEqual(order.total, Decimal("1999.00"))
        self.assertEqual(order.status, "pending")

    def test_invalid_form_creates_nothing(self):
        self.add(self.p1, 1)
        r = self.client.post(reverse("checkout"), {**CHECKOUT_DATA, "postal_code": "12", "phone": "abc"})
        self.assertContains(r, "Please correct the errors")
        self.assertEqual(Order.objects.count(), 0)
        self.p1.refresh_from_db()
        self.assertEqual(self.p1.stock, 5)
        self.assertEqual(self.client.session["cart"][str(self.p1.pk)], 1)

    def test_insufficient_stock_at_checkout(self):
        self.add(self.p1, 4)
        Product.objects.filter(pk=self.p1.pk).update(stock=2)  # someone else bought some
        r = self.client.post(reverse("checkout"), CHECKOUT_DATA, follow=True)
        self.assertContains(r, "Insufficient stock")
        self.assertEqual(Order.objects.count(), 0)
        self.p1.refresh_from_db()
        self.assertEqual(self.p1.stock, 2)
        self.assertEqual(self.client.session["cart"][str(self.p1.pk)], 4)  # cart kept

    def test_rollback_on_failure_mid_order(self):
        self.add(self.p1, 2)
        self.add(self.p2, 1)
        real_create = OrderItem.objects.create
        calls = {"n": 0}

        def flaky(*a, **kw):
            calls["n"] += 1
            if calls["n"] == 2:
                raise RuntimeError("simulated crash")
            return real_create(*a, **kw)

        with mock.patch.object(OrderItem.objects, "create", side_effect=flaky):
            with self.assertLogs("store.views", level="ERROR"):
                r = self.client.post(reverse("checkout"), CHECKOUT_DATA, follow=True)
        self.assertContains(r, "order was not placed")
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(OrderItem.objects.count(), 0)
        self.p1.refresh_from_db(); self.p2.refresh_from_db()
        self.assertEqual((self.p1.stock, self.p2.stock), (5, 10))
        self.assertEqual(len(self.client.session["cart"]), 2)  # cart not cleared

    def test_cannot_view_other_users_orders(self):
        order = Order.objects.create(user=self.other, total=10, **CHECKOUT_DATA)
        self.assertEqual(self.client.get(order.get_absolute_url()).status_code, 404)
        confirm = reverse("order_confirmation", args=[order.order_number])
        self.assertEqual(self.client.get(confirm).status_code, 404)
        self.assertNotContains(self.client.get(reverse("order_history")), order.order_number)

    def test_order_detail_shows_items_and_shipping(self):
        self.add(self.p2, 2)
        self.client.post(reverse("checkout"), CHECKOUT_DATA)
        order = Order.objects.get()
        r = self.client.get(order.get_absolute_url())
        self.assertContains(r, "Python Book")
        self.assertContains(r, "12 MI Road")
        self.assertContains(r, "₹1,099.00")


class AdminTests(BaseTestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("root", "root@example.com", "Adm1n-pass-123")
        self.client.login(username="root", password="Adm1n-pass-123")

    def test_admin_changelists_load(self):
        for model in ["category", "product", "order", "orderitem"]:
            self.assertEqual(self.client.get(reverse(f"admin:store_{model}_changelist")).status_code, 200, model)
        self.assertEqual(self.client.get(reverse("admin:auth_user_changelist")).status_code, 200)

    def test_admin_can_create_product(self):
        r = self.client.post(reverse("admin:store_product_add"), {
            "name": "Admin Made", "slug": "admin-made", "description": "d", "price": "99.00",
            "stock": 3, "is_active": "on",
        })
        self.assertEqual(r.status_code, 302)
        self.assertTrue(Product.objects.filter(slug="admin-made").exists())

    def test_orders_are_protected_in_admin(self):
        order = Order.objects.create(user=self.user, total=50, **CHECKOUT_DATA)
        self.assertEqual(self.client.get(reverse("admin:store_order_add")).status_code, 403)
        self.assertEqual(self.client.get(reverse("admin:store_order_delete", args=[order.pk])).status_code, 403)
        self.client.post(reverse("admin:store_order_change", args=[order.pk]), {
            "status": "shipped", "total": "1.00", "customer_name": "Hacked",
            "items-TOTAL_FORMS": "0", "items-INITIAL_FORMS": "0",
            "items-MIN_NUM_FORMS": "0", "items-MAX_NUM_FORMS": "1000",
        })
        order.refresh_from_db()
        self.assertEqual(order.status, "shipped")
        self.assertEqual(order.total, Decimal("50.00"))
        self.assertEqual(order.customer_name, "Asha Verma")


class ImageValidationTests(BaseTestCase):
    def test_model_rejects_wrong_extension(self):
        p = Product(name="Bad", description="d", price=1,
                    image=SimpleUploadedFile("evil.exe", b"MZ", content_type="application/octet-stream"))
        with self.assertRaises(Exception) as ctx:
            p.full_clean()
        self.assertIn("image", ctx.exception.message_dict)

    def test_admin_rejects_fake_image_content(self):
        User.objects.create_superuser("root", "r@example.com", "Adm1n-pass-123")
        self.client.login(username="root", password="Adm1n-pass-123")
        r = self.client.post(reverse("admin:store_product_add"), {
            "name": "Fake", "slug": "fake", "description": "d", "price": "5", "stock": 1,
            "is_active": "on",
            "image": SimpleUploadedFile("fake.png", b"not really a png", content_type="image/png"),
        })
        self.assertEqual(r.status_code, 200)  # form redisplayed with an error
        self.assertFalse(Product.objects.filter(slug="fake").exists())


class SeedCommandTests(TestCase):
    def test_seed_is_idempotent(self):
        with override_settings(MEDIA_ROOT=__import__("tempfile").mkdtemp()):
            call_command("seed_demo_data", verbosity=0)
            first = Product.objects.count()
            call_command("seed_demo_data", verbosity=0)
        self.assertGreaterEqual(first, 10)
        self.assertEqual(Product.objects.count(), first)
        self.assertGreaterEqual(Category.objects.count(), 3)
        self.assertTrue(all(p.image for p in Product.objects.all()))
