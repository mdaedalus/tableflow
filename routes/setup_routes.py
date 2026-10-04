import uuid
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from database.db import db
from models.models import Restaurant, Table, Staff

setup_bp = Blueprint("setup", __name__)


@setup_bp.route("/", methods=["GET"])
def index():
    r = Restaurant.query.first()
    if r and r.is_setup_complete:
        return redirect(url_for("admin.login"))
    return redirect(url_for("setup.step1"))


@setup_bp.route("/setup/step1", methods=["GET", "POST"])
def step1():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        password = request.form.get("password", "").strip()
        language = request.form.get("language", "tr")
        if not name or not password:
            flash("Restoran adı ve şifre zorunlu.", "error")
            return redirect(url_for("setup.step1"))
        session["setup_name"] = name
        session["setup_password"] = password
        session["setup_language"] = language
        return redirect(url_for("setup.step2"))
    return render_template("setup/step1.html")


@setup_bp.route("/setup/step2", methods=["GET", "POST"])
def step2():
    if "setup_name" not in session:
        return redirect(url_for("setup.step1"))
    if request.method == "POST":
        count = int(request.form.get("table_count", 0))
        if count < 1:
            flash("En az 1 masa olmalı.", "error")
            return redirect(url_for("setup.step2"))
        session["setup_table_count"] = count
        return redirect(url_for("setup.step3"))
    return render_template("setup/step2.html")


@setup_bp.route("/setup/step3", methods=["GET", "POST"])
def step3():
    if "setup_table_count" not in session:
        return redirect(url_for("setup.step1"))
    if request.method == "POST":
        staff_names = request.form.getlist("staff_name")
        staff_passwords = request.form.getlist("staff_password")

        r = Restaurant(
            name=session["setup_name"],
            language=session.get("setup_language", "tr"),
            is_setup_complete=True,
        )
        r.set_password(session["setup_password"])
        db.session.add(r)
        db.session.flush()

        # masalar
        for i in range(1, session["setup_table_count"] + 1):
            t = Table(
                restaurant_id=r.id,
                number=str(i),
                qr_token=uuid.uuid4().hex,
            )
            db.session.add(t)

        # çalışanlar
        for name, pw in zip(staff_names, staff_passwords):
            if name.strip() and pw.strip():
                s = Staff(restaurant_id=r.id, name=name.strip(), role="waiter")
                s.set_password(pw.strip())
                db.session.add(s)

        db.session.commit()
        session.pop("setup_name", None)
        session.pop("setup_password", None)
        session.pop("setup_table_count", None)
        flash("Restoran kuruldu! Giriş yapabilirsiniz.", "success")
        return redirect(url_for("admin.login"))
    return render_template("setup/step3.html")