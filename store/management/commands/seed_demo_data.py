"""Populate the store with demo categories and products.

Safe to run repeatedly: records are matched by slug and updated, never duplicated.
Product images are generated locally with Pillow (no downloads needed).
"""
import io
import textwrap
from decimal import Decimal

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from PIL import Image, ImageDraw, ImageFont

CATEGORIES = {
    "electronics": ("Electronics", "Gadgets and accessories", (37, 99, 235)),
    "fashion": ("Fashion", "Clothing and footwear", (219, 39, 119)),
    "home-kitchen": ("Home & Kitchen", "Everyday home essentials", (217, 119, 6)),
    "books": ("Books", "Learning and stories", (22, 163, 74)),
    "sports-fitness": ("Sports & Fitness", "Stay active", (124, 58, 237)),
}

# (slug, name, category slug, price, stock, featured, description)
PRODUCTS = [
    ("wireless-earbuds", "Wireless Earbuds", "electronics", "1999.00", 25, True,
     "Bluetooth 5.3 earbuds with noise isolation, 24-hour battery life with the charging case and a touch-control surface."),
    ("smart-fitness-band", "Smart Fitness Band", "electronics", "2499.00", 18, True,
     "Tracks steps, heart rate and sleep. Water resistant with a bright AMOLED display and 10-day battery."),
    ("power-bank-10000", "Power Bank 10000 mAh", "electronics", "1299.00", 40, False,
     "Compact 10000 mAh power bank with fast charging and dual USB output."),
    ("cotton-tshirt", "Classic Cotton T-Shirt", "fashion", "499.00", 60, False,
     "Soft 100% combed cotton t-shirt with a relaxed everyday fit. Machine washable."),
    ("denim-jacket", "Denim Jacket", "fashion", "2199.00", 12, True,
     "Timeless mid-wash denim jacket with a durable stitch and button-front closure."),
    ("running-shoes", "Lightweight Running Shoes", "fashion", "2799.00", 20, False,
     "Breathable mesh upper and cushioned sole designed for daily runs and gym sessions."),
    ("steel-water-bottle", "Insulated Steel Water Bottle", "home-kitchen", "699.00", 50, False,
     "750 ml double-wall stainless steel bottle that keeps drinks cold for 24 hours or hot for 12."),
    ("non-stick-cookware", "Non-Stick Cookware Set", "home-kitchen", "3499.00", 8, True,
     "Three-piece induction-friendly non-stick set with heat-resistant handles."),
    ("python-crash-course", "Python Programming for Beginners", "books", "549.00", 35, False,
     "A practical, project-based introduction to Python covering variables, functions, files and web basics."),
    ("web-dev-handbook", "Web Development Handbook", "books", "649.00", 3, False,
     "HTML, CSS and JavaScript explained step by step with small real-world projects."),
    ("yoga-mat", "Anti-Slip Yoga Mat", "sports-fitness", "899.00", 30, False,
     "6 mm cushioned, anti-slip yoga mat with a carry strap."),
    ("adjustable-dumbbells", "Adjustable Dumbbell Pair", "sports-fitness", "3999.00", 0, False,
     "Pair of adjustable dumbbells (2-10 kg each). Currently out of stock: used to demo the stock label."),
]


def _font(size):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # very old Pillow
        return ImageFont.load_default()


def make_image(name, colour):
    size = 600
    img = Image.new("RGB", (size, size), colour)
    draw = ImageDraw.Draw(img)
    for y in range(size):  # simple vertical fade to white
        t = y / size * 0.55
        c = tuple(int(v + (255 - v) * t) for v in colour)
        draw.line([(0, y), (size, y)], fill=c)
    draw.ellipse([180, 90, 420, 330], fill=(255, 255, 255))
    draw.text((300, 210), name[0].upper(), fill=colour, font=_font(150), anchor="mm")
    y = 400
    for line in textwrap.wrap(name, 20)[:3]:
        draw.text((300, y), line, fill=(255, 255, 255), font=_font(38), anchor="mm")
        y += 48
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


class Command(BaseCommand):
    help = "Create (or update) demo categories and products. Safe to run multiple times."

    def add_arguments(self, parser):
        parser.add_argument("--no-images", action="store_true", help="Skip image generation.")

    @transaction.atomic
    def handle(self, *args, **options):
        from store.models import Category, Product

        cats = {}
        for slug, (name, desc, _) in CATEGORIES.items():
            cats[slug], _ = Category.objects.update_or_create(
                slug=slug, defaults={"name": name, "description": desc}
            )

        created = updated = images = 0
        for slug, name, cat, price, stock, featured, desc in PRODUCTS:
            product, was_created = Product.objects.get_or_create(
                slug=slug,
                defaults={
                    "name": name, "category": cats[cat], "price": Decimal(price),
                    "stock": stock, "is_featured": featured, "description": desc,
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1  # existing records are left as the admin edited them
            if not options["no_images"] and not product.image:
                png = make_image(name, CATEGORIES[cat][2])
                product.image.save(f"{slug}.png", ContentFile(png), save=True)
                images += 1

        self.stdout.write(self.style.SUCCESS(
            f"Demo data ready: {created} product(s) created, {updated} already existed, "
            f"{images} image(s) generated."
        ))
