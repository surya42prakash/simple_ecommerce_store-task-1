import uuid
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, MinValueValidator, RegexValidator
from django.db import models
from django.urls import reverse
from django.utils.text import slugify

MAX_IMAGE_BYTES = 2 * 1024 * 1024  # 2 MB


def validate_image_size(image):
    if image.size > MAX_IMAGE_BYTES:
        raise ValidationError("Image file too large (maximum is 2 MB).")


def _unique_slug(model, value, instance_pk=None):
    base = slugify(value) or "item"
    slug, n = base, 2
    qs = model.objects.all()
    if instance_pk:
        qs = qs.exclude(pk=instance_pk)
    while qs.filter(slug=slug).exists():
        slug = f"{base}-{n}"
        n += 1
    return slug


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=110, unique=True, blank=True)
    description = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name_plural = "categories"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = _unique_slug(Category, self.name, self.pk)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return f"{reverse('product_list')}?category={self.slug}"


class Product(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    description = models.TextField()
    price = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))]
    )
    image = models.ImageField(
        upload_to="products/",
        blank=True,
        validators=[
            FileExtensionValidator(["jpg", "jpeg", "png", "webp", "gif"]),
            validate_image_size,
        ],
    )
    category = models.ForeignKey(
        Category, null=True, blank=True, on_delete=models.SET_NULL, related_name="products"
    )
    stock = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True, help_text="Untick to hide from the store.")
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["is_active", "-created_at"]),
            models.Index(fields=["name"]),
        ]
        constraints = [
            models.CheckConstraint(condition=models.Q(price__gte=0), name="product_price_non_negative"),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = _unique_slug(Product, self.name, self.pk)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("product_detail", kwargs={"slug": self.slug})

    @property
    def in_stock(self):
        return self.stock > 0

    @property
    def low_stock(self):
        return 0 < self.stock <= 5


phone_validator = RegexValidator(
    r"^\+?[0-9][0-9\s\-]{8,14}$", "Enter a valid phone number (9-15 digits)."
)
postal_validator = RegexValidator(r"^[1-9][0-9]{5}$", "Enter a valid 6-digit PIN code.")


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CONFIRMED = "confirmed", "Confirmed"
        SHIPPED = "shipped", "Shipped"
        DELIVERED = "delivered", "Delivered"
        CANCELLED = "cancelled", "Cancelled"

    order_number = models.CharField(max_length=20, unique=True, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders"
    )
    customer_name = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=20, validators=[phone_validator])
    address = models.CharField("shipping address", max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=6, validators=[postal_validator])
    total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["user", "-created_at"])]
        constraints = [
            models.CheckConstraint(condition=models.Q(total__gte=0), name="order_total_non_negative"),
        ]

    def __str__(self):
        return self.order_number

    def save(self, *args, **kwargs):
        if not self.order_number:
            while True:
                candidate = f"ORD-{uuid.uuid4().hex[:8].upper()}"
                if not Order.objects.filter(order_number=candidate).exists():
                    self.order_number = candidate
                    break
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("order_detail", kwargs={"order_number": self.order_number})


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(
        Product, null=True, blank=True, on_delete=models.SET_NULL, related_name="order_items"
    )
    product_name = models.CharField(max_length=200)  # snapshot
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)  # snapshot
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    line_subtotal = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(quantity__gte=1), name="orderitem_quantity_positive"),
        ]

    def __str__(self):
        return f"{self.quantity} x {self.product_name}"
