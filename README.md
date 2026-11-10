# Simple E-commerce Store (Django)

A complete, beginner-friendly **demo** online store built for a web-development internship project.
Customers can browse products, search and filter by category, fill a shopping cart, register / log in,
check out (demo checkout, pay on delivery) and review their order history. Staff manage everything
through the Django Admin.

> **Demo only.** No real payment gateway is integrated. Checkout is clearly labelled as a
> simulated "Cash on Delivery" order and no money is processed.

Full step-by-step guide with screenshots-free instructions, SQL examples and troubleshooting:
**[`docs/SETUP_AND_DATABASE_GUIDE.pdf`](docs/SETUP_AND_DATABASE_GUIDE.pdf)**

## Features

- Product catalogue with categories, featured / latest sections, search (name + description), category filter, sorting and pagination
- Prices in Indian rupees (₹), stock display ("Only 3 left", "Out of stock"), graceful placeholder when an image is missing
- Session-based cart: add, update, remove, live item count in the navbar, stock validation, server-side totals (the browser never sets prices)
- Registration, login, logout using Django's built-in authentication (PBKDF2 password hashing, password validators)
- Protected checkout and order history; customers can only open **their own** orders
- Transactional order processing: order + items created, stock reduced and cart cleared together, or nothing happens at all
- Django Admin for products, categories, orders (status editable; totals and item snapshots are read-only) and users
- Flash messages for every action, CSRF protection, template auto-escaping, responsive layout, keyboard-friendly and labelled forms
- 38 automated tests

## Technology stack

| Layer | Technology |
|---|---|
| Backend | Python 3 (3.10 – 3.13), Django 5.2 |
| Frontend | HTML5, CSS3, vanilla JavaScript (no frameworks) |
| Database | SQLite (`db.sqlite3`, created by migrations) |
| Images | Pillow |

Exact versions are pinned in `requirements.txt`.

## Install and run (Windows 11, Command Prompt)

Open the project folder in VS Code (`File > Open Folder`), open a terminal (`Terminal > New Terminal`) and run:

```bat
python --version
python -m pip --version
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py seed_demo_data
python manage.py runserver
```

PowerShell: activate with `.venv\Scripts\Activate.ps1` (if blocked, run
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once). The other commands are identical.

Prefer double-clicking? Use `scripts\setup_windows.bat`, then `scripts\create_admin.bat`, then `scripts\run_windows.bat`.
These scripts never delete files or databases.

| What | URL |
|---|---|
| Website | http://127.0.0.1:8000/ |
| Admin panel | http://127.0.0.1:8000/admin/ |

Stop the server with **Ctrl+C**. To start it again later: open a terminal in the project folder,
activate the virtual environment again (`.venv\Scripts\activate`) and run `python manage.py runserver`.

## Everyday commands

| Task | Command |
|---|---|
| Apply database migrations | `python manage.py migrate` |
| Create an administrator | `python manage.py createsuperuser` |
| Load demo products (safe to repeat) | `python manage.py seed_demo_data` |
| Load demo products without images | `python manage.py seed_demo_data --no-images` |
| Run the automated tests | `python manage.py test` |
| Django system check | `python manage.py check` |
| Show the SQL of a migration | `python manage.py sqlmigrate store 0001` |

## Database

- Engine: SQLite. The file `db.sqlite3` is created in the project root (next to `manage.py`) the first time you run `migrate`.
- It is **not** shipped in the ZIP: migrations + `seed_demo_data` create everything from scratch.
- Tables: `store_category`, `store_product`, `store_order`, `store_orderitem`, `auth_user` (plus Django's own tables).
- Inspect it in the Admin, or with the optional *DB Browser for SQLite*. Example queries are in the PDF guide.
- Uploaded product images live in `media/products/`. **Back up `db.sqlite3` and `media/` before deleting or resetting anything.**

## Project layout

```
simple_ecommerce_store/
  manage.py  requirements.txt  .env.example  .gitignore  README.md  LICENSE
  ecommerce_project/   settings.py, urls.py, wsgi.py, asgi.py
  store/               models.py, views.py, forms.py, cart.py, services.py, admin.py,
                       urls.py, tests.py, migrations/, management/commands/seed_demo_data.py
  templates/           base.html, home.html, product_*.html, cart.html, checkout.html, ...
  static/              css/style.css, js/main.js, images/logo.svg, images/placeholder.svg
  media/products/      uploaded / generated product images
  docs/                SETUP_AND_DATABASE_GUIDE.pdf
  scripts/             setup_windows.bat, run_windows.bat, create_admin.bat
```

## Troubleshooting (quick list)

| Problem | Fix |
|---|---|
| `'python' is not recognized` | Reinstall Python and tick **Add python.exe to PATH**, or try `py` instead of `python` |
| PowerShell: *running scripts is disabled* | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, or use Command Prompt |
| `No module named 'django'` | Activate the venv, then `python -m pip install -r requirements.txt` |
| `no such table: store_product` | Run `python manage.py migrate` |
| Port 8000 busy | `python manage.py runserver 8001` |
| Product images missing | Run `seed_demo_data`; images are only served while `DJANGO_DEBUG=True` |

The PDF guide has a longer troubleshooting section.

## Before deploying (this project is NOT production-ready as shipped)

Set `DJANGO_DEBUG=False`, a unique `DJANGO_SECRET_KEY` and your real `DJANGO_ALLOWED_HOSTS`; serve
static and media files through your web server; use HTTPS; move to PostgreSQL/MySQL for real traffic;
add a real payment provider, email confirmation and rate limiting. With `DJANGO_DEBUG=False` and no secret key
the app refuses to start on purpose.

## Tests

```bat
python manage.py test
```

Covers catalogue, search/filter, registration/login, cart add/update/remove/totals, invalid quantities,
stock validation, checkout, order + item creation, stock reduction, cart clearing, transaction rollback,
login protection, per-user order privacy, admin and image validation.
