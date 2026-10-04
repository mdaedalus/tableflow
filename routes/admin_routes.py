import os
import uuid
from datetime import datetime, date
from flask import (
    Blueprint, render_template, request, redirect, url_for,
    session, flash, send_file, current_app, jsonify
)
from werkzeug.utils import secure_filename
from sqlalchemy import func
from database.db import db
from models.models import Restaurant, Table, Staff, Category, Product, Order, OrderItem
from utils.auth import admin_required
from utils.qr import generate_tables_pdf

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


# -------- GİRİŞ --------
@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        pw = request.form.get("password", "")
        r = Restaurant.query.first()
        if r and r.check_password(pw):
            session["role"] = "admin"
            session["restaurant_id"] = r.id
            return redirect(url_for("admin.dashboard"))
        flash("Hatalı şifre", "error")
    return render_template("admin/login.html")


@admin_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("admin.login"))


# -------- DASHBOARD --------
@admin_bp.route("/")
@admin_required
def dashboard():
    rid = session["restaurant_id"]
    today = date.today()

    open_orders = Order.query.filter_by(restaurant_id=rid, status="open").all()
    today_orders = Order.query.filter(
        Order.restaurant_id == rid,
        func.date(Order.created_at) == today.isoformat()
    ).all()

    total_today = sum(o.total for o in today_orders)

    # garson performansı
    staff_stats = (
        db.session.query(Staff.name, func.count(Order.id), func.coalesce(func.sum(Order.total), 0))
        .outerjoin(Order, Order.waiter_id == Staff.id)
        .filter(Staff.restaurant_id == rid)
        .group_by(Staff.id)
        .all()
    )

    tables = Table.query.filter_by(restaurant_id=rid).all()
    occupied = sum(1 for t in tables if t.is_occupied)

    return render_template(
        "admin/dashboard.html",
        open_orders=open_orders,
        today_count=len(today_orders),
        total_today=total_today,
        staff_stats=staff_stats,
        total_tables=len(tables),
        occupied=occupied,
    )


# -------- MASALAR --------
@admin_bp.route("/tables", methods=["GET", "POST"])
@admin_required
def tables():
    rid = session["restaurant_id"]

    if request.method == "POST":
        action = request.form.get("action")
        if action == "add":
            number = request.form.get("number", "").strip()
            capacity = int(request.form.get("capacity", 4))
            if number:
                t = Table(
                    restaurant_id=rid, number=number,
                    capacity=capacity, qr_token=uuid.uuid4().hex,
                )
                db.session.add(t)
                db.session.commit()
                flash("Masa eklendi.", "success")
        return redirect(url_for("admin.tables"))

    all_tables = Table.query.filter_by(restaurant_id=rid).order_by(Table.id).all()
    staff = Staff.query.filter_by(restaurant_id=rid, is_active=True).all()
    return render_template("admin/tables.html", tables=all_tables, staff=staff)


@admin_bp.route("/tables/<int:tid>/update", methods=["POST"])
@admin_required
def update_table(tid):
    t = Table.query.get_or_404(tid)
    t.number = request.form.get("number", t.number)
    t.capacity = int(request.form.get("capacity", t.capacity))
    t.name = request.form.get("name", t.name)
    db.session.commit()
    flash("Masa güncellendi.", "success")
    return redirect(url_for("admin.tables"))


@admin_bp.route("/tables/<int:tid>/delete", methods=["POST"])
@admin_required
def delete_table(tid):
    t = Table.query.get_or_404(tid)
    if t.is_occupied:
        flash("Dolu masa silinemez.", "error")
        return redirect(url_for("admin.tables"))
    db.session.delete(t)
    db.session.commit()
    return redirect(url_for("admin.tables"))


@admin_bp.route("/tables/<int:tid>/assign", methods=["POST"])
@admin_required
def assign_waiter(tid):
    t = Table.query.get_or_404(tid)
    wid = request.form.get("waiter_id")
    t.assigned_waiter_id = int(wid) if wid else None
    db.session.commit()
    return redirect(url_for("admin.tables"))


@admin_bp.route("/tables/qr-pdf")
@admin_required
def tables_qr_pdf():
    rid = session["restaurant_id"]
    r = Restaurant.query.get(rid)
    all_tables = Table.query.filter_by(restaurant_id=rid).order_by(Table.id).all()

    out_dir = current_app.config["QR_FOLDER"]
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"tables_{rid}.pdf")

    base_url = request.host_url.rstrip("/")
    generate_tables_pdf(r.name, all_tables, base_url, out_path)

    return send_file(out_path, as_attachment=True, download_name="masa_qr_kodlari.pdf")


# -------- ÇALIŞANLAR --------
@admin_bp.route("/staff", methods=["GET", "POST"])
@admin_required
def staff():
    rid = session["restaurant_id"]
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        pw = request.form.get("password", "").strip()
        if name and pw:
            s = Staff(restaurant_id=rid, name=name)
            s.set_password(pw)
            db.session.add(s)
            db.session.commit()
            flash("Çalışan eklendi.", "success")
        return redirect(url_for("admin.staff"))

    all_staff = Staff.query.filter_by(restaurant_id=rid).all()
    return render_template("admin/staff.html", staff=all_staff)


@admin_bp.route("/staff/<int:sid>/delete", methods=["POST"])
@admin_required
def delete_staff(sid):
    s = Staff.query.get_or_404(sid)
    s.is_active = False
    db.session.commit()
    flash("Çalışan pasife alındı.", "success")
    return redirect(url_for("admin.staff"))


@admin_bp.route("/staff/<int:sid>/password", methods=["POST"])
@admin_required
def update_staff_password(sid):
    s = Staff.query.get_or_404(sid)
    pw = request.form.get("password", "").strip()
    if pw:
        s.set_password(pw)
        db.session.commit()
        flash("Şifre güncellendi.", "success")
    return redirect(url_for("admin.staff"))


# -------- KATEGORİLER --------
@admin_bp.route("/categories", methods=["GET", "POST"])
@admin_required
def categories():
    rid = session["restaurant_id"]
    if request.method == "POST":
        name_tr = request.form.get("name_tr", "").strip()
        name_en = request.form.get("name_en", "").strip()
        if name_tr:
            c = Category(restaurant_id=rid, name_tr=name_tr, name_en=name_en)
            db.session.add(c)
            db.session.commit()
            flash("Kategori eklendi.", "success")
        return redirect(url_for("admin.categories"))

    cats = Category.query.filter_by(restaurant_id=rid).order_by(Category.order).all()
    return render_template("admin/categories.html", categories=cats)


@admin_bp.route("/categories/<int:cid>/delete", methods=["POST"])
@admin_required
def delete_category(cid):
    c = Category.query.get_or_404(cid)
    db.session.delete(c)
    db.session.commit()
    return redirect(url_for("admin.categories"))


# -------- ÜRÜNLER --------
@admin_bp.route("/products", methods=["GET", "POST"])
@admin_required
def products():
    rid = session["restaurant_id"]
    if request.method == "POST":
        name_tr = request.form.get("name_tr", "").strip()
        name_en = request.form.get("name_en", "").strip()
        desc_tr = request.form.get("description_tr", "").strip()
        desc_en = request.form.get("description_en", "").strip()
        price = float(request.form.get("price", 0))
        category_id = int(request.form.get("category_id"))
        image_file = request.files.get("image")

        filename = None
        if image_file and image_file.filename:
            filename = secure_filename(f"{uuid.uuid4().hex}_{image_file.filename}")
            image_file.save(os.path.join(current_app.config["UPLOAD_FOLDER"], filename))

        p = Product(
            restaurant_id=rid, category_id=category_id,
            name_tr=name_tr, name_en=name_en,
            description_tr=desc_tr, description_en=desc_en,
            price=price, image=filename,
        )
        db.session.add(p)
        db.session.commit()
        flash("Ürün eklendi.", "success")
        return redirect(url_for("admin.products"))

    cats = Category.query.filter_by(restaurant_id=rid).all()
    prods = Product.query.filter_by(restaurant_id=rid).all()
    return render_template("admin/products.html", categories=cats, products=prods)


@admin_bp.route("/products/<int:pid>/delete", methods=["POST"])
@admin_required
def delete_product(pid):
    p = Product.query.get_or_404(pid)
    db.session.delete(p)
    db.session.commit()
    return redirect(url_for("admin.products"))


# -------- CANLI TAKİP --------
@admin_bp.route("/live")
@admin_required
def live():
    rid = session["restaurant_id"]
    tables = Table.query.filter_by(restaurant_id=rid).order_by(Table.id).all()
    orders = Order.query.filter_by(restaurant_id=rid, status="open").all()
    by_table = {o.table_id: o for o in orders}
    staff = {s.id: s.name for s in Staff.query.filter_by(restaurant_id=rid).all()}
    return render_template("admin/live.html", tables=tables, orders=by_table, staff=staff)


@admin_bp.route("/order/<int:oid>/close", methods=["POST"])
@admin_required
def close_order(oid):
    o = Order.query.get_or_404(oid)
    o.status = "paid"
    o.closed_at = datetime.utcnow()
    t = Table.query.get(o.table_id)
    t.is_occupied = False
    t.assigned_waiter_id = None
    db.session.commit()
    flash("Masa kapatıldı.", "success")
    return redirect(url_for("admin.live"))