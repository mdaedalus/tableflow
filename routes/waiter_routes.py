from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from database.db import db
from models.models import Restaurant, Table, Staff, Order, OrderItem, Product, Category

waiter_bp = Blueprint("waiter", __name__, url_prefix="/waiter")


@waiter_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        pw = request.form.get("password", "")
        r = Restaurant.query.first()
        if not r:
            return redirect(url_for("setup.step1"))
        staff = Staff.query.filter_by(restaurant_id=r.id, name=name, is_active=True).first()
        if staff and staff.check_password(pw):
            session["role"] = "waiter"
            session["staff_id"] = staff.id
            session["restaurant_id"] = r.id
            return redirect(url_for("waiter.dashboard"))
        flash("Hatalı giriş.", "error")
    return render_template("waiter/login.html")


@waiter_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("waiter.login"))


@waiter_bp.route("/")
def dashboard():
    if session.get("role") not in ("waiter", "admin"):
        return redirect(url_for("waiter.login"))
    rid = session["restaurant_id"]
    sid = session.get("staff_id")

    tables = Table.query.filter_by(restaurant_id=rid).order_by(Table.id).all()
    open_orders = {
        o.table_id: o for o in Order.query.filter_by(restaurant_id=rid, status="open").all()
    }
    categories = Category.query.filter_by(restaurant_id=rid).all()
    products = Product.query.filter_by(restaurant_id=rid, is_available=True).all()

    # ✅ JSON'a çevrilebilir hale getir
    categories_json = [
        {"id": c.id, "name_tr": c.name_tr, "name_en": c.name_en}
        for c in categories
    ]
    products_json = [
        {
            "id": p.id,
            "category_id": p.category_id,
            "name_tr": p.name_tr,
            "name_en": p.name_en,
            "price": p.price,
            "image": p.image,
        }
        for p in products
    ]

    return render_template(
        "waiter/dashboard.html",
        tables=tables, orders=open_orders,
        categories=categories_json,
        products=products_json,
        staff_id=sid,
    )


@waiter_bp.route("/table/<int:tid>/open", methods=["POST"])
def open_table(tid):
    if session.get("role") not in ("waiter", "admin"):
        return jsonify({"error": "auth"}), 401
    t = Table.query.get_or_404(tid)
    if t.is_occupied:
        return jsonify({"error": "occupied"}), 400
    o = Order(restaurant_id=t.restaurant_id, table_id=t.id, waiter_id=session.get("staff_id"))
    t.is_occupied = True
    t.assigned_waiter_id = session.get("staff_id")
    db.session.add(o)
    db.session.commit()
    return jsonify({"order_id": o.id})


@waiter_bp.route("/order/<int:oid>/add", methods=["POST"])
def add_item(oid):
    if session.get("role") not in ("waiter", "admin"):
        return jsonify({"error": "auth"}), 401
    data = request.get_json()
    product_id = data.get("product_id")
    qty = int(data.get("quantity", 1))
    p = Product.query.get_or_404(product_id)
    o = Order.query.get_or_404(oid)

    item = OrderItem(order_id=o.id, product_id=p.id, quantity=qty, price_at_time=p.price)
    db.session.add(item)
    o.total = sum(i.price_at_time * i.quantity for i in o.items) + p.price * qty
    db.session.commit()
    return jsonify({"ok": True, "total": o.total})


@waiter_bp.route("/order/<int:oid>/items")
def order_items(oid):
    o = Order.query.get_or_404(oid)
    return jsonify({
        "items": [
            {"id": i.id, "name": i.product.name_tr, "qty": i.quantity,
             "price": i.price_at_time, "status": i.status}
            for i in o.items
        ],
        "total": o.total,
    })


@waiter_bp.route("/item/<int:iid>/serve", methods=["POST"])
def serve_item(iid):
    i = OrderItem.query.get_or_404(iid)
    i.status = "served"
    db.session.commit()
    return jsonify({"ok": True})


@waiter_bp.route("/table/<int:tid>/close", methods=["POST"])
def close_table(tid):
    if session.get("role") not in ("waiter", "admin"):
        return jsonify({"error": "auth"}), 401
    o = Order.query.filter_by(table_id=tid, status="open").first()
    if o:
        o.status = "closed"   # garson kapattı, kasa onayı bekleniyor
    t = Table.query.get_or_404(tid)
    t.is_occupied = False
    t.assigned_waiter_id = None
    db.session.commit()
    return jsonify({"ok": True})