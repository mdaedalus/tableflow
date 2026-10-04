from flask import Blueprint, render_template, abort, request, jsonify, session
from models.models import Table, Restaurant, Category, Product, Order, OrderItem
from database.db import db

customer_bp = Blueprint("customer", __name__)


def _lang():
    return request.args.get("lang", "tr")


@customer_bp.route("/m/<token>")
def menu(token):
    t = Table.query.filter_by(qr_token=token).first_or_404()
    r = Restaurant.query.get(t.restaurant_id)
    lang = _lang()

    cats = Category.query.filter_by(restaurant_id=r.id).all()
    products = Product.query.filter_by(restaurant_id=r.id, is_available=True).all()
    grouped = {c.id: [] for c in cats}
    for p in products:
        grouped.setdefault(p.category_id, []).append(p)

    open_order = Order.query.filter_by(table_id=t.id, status="open").first()
    order_items = []
    if open_order:
        order_items = [
            {"name": i.product.name_tr, "qty": i.quantity,
             "price": i.price_at_time, "status": i.status}
            for i in open_order.items
        ]

    return render_template(
        "customer/menu.html",
        restaurant=r, table=t, categories=cats,
        grouped=grouped, lang=lang, open_order=open_order,
        order_items=order_items,
    )


@customer_bp.route("/m/<token>/order", methods=["POST"])
def place_order(token):
    t = Table.query.filter_by(qr_token=token).first_or_404()
    data = request.get_json()
    items = data.get("items", [])
    if not items:
        return jsonify({"error": "no items"}), 400

    o = Order.query.filter_by(table_id=t.id, status="open").first()
    if not o:
        o = Order(restaurant_id=t.restaurant_id, table_id=t.id)
        db.session.add(o)
        db.session.flush()
    t.is_occupied = True

    total = o.total or 0
    for it in items:
        p = Product.query.get(it["product_id"])
        if not p:
            continue
        qty = int(it.get("quantity", 1))
        oi = OrderItem(order_id=o.id, product_id=p.id, quantity=qty, price_at_time=p.price)
        db.session.add(oi)
        total += p.price * qty
    o.total = total
    db.session.commit()
    return jsonify({"ok": True, "order_id": o.id})