from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from database.db import db


class Restaurant(db.Model):
    __tablename__ = "restaurants"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    owner_password = db.Column(db.String(255), nullable=False)  # yönetici şifresi
    language = db.Column(db.String(5), default="tr")
    is_setup_complete = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, pw):
        self.owner_password = generate_password_hash(pw)

    def check_password(self, pw):
        return check_password_hash(self.owner_password, pw)


class Table(db.Model):
    __tablename__ = "tables"
    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey("restaurants.id"), nullable=False)
    number = db.Column(db.String(20), nullable=False)     # masa no
    name = db.Column(db.String(80))                       # opsiyonel isim
    capacity = db.Column(db.Integer, default=4)
    qr_token = db.Column(db.String(64), unique=True, nullable=False)
    is_occupied = db.Column(db.Boolean, default=False)
    assigned_waiter_id = db.Column(db.Integer, db.ForeignKey("staff.id"), nullable=True)


class Staff(db.Model):
    __tablename__ = "staff"
    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey("restaurants.id"), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), default="waiter")  # waiter / admin
    password_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, pw):
        self.password_hash = generate_password_hash(pw)

    def check_password(self, pw):
        return check_password_hash(self.password_hash, pw)


class Category(db.Model):
    __tablename__ = "categories"
    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey("restaurants.id"), nullable=False)
    name_tr = db.Column(db.String(80), nullable=False)
    name_en = db.Column(db.String(80))
    order = db.Column(db.Integer, default=0)


class Product(db.Model):
    __tablename__ = "products"
    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey("restaurants.id"), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("categories.id"), nullable=False)
    name_tr = db.Column(db.String(120), nullable=False)
    name_en = db.Column(db.String(120))
    description_tr = db.Column(db.Text)
    description_en = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    image = db.Column(db.String(255))
    is_available = db.Column(db.Boolean, default=True)


class Order(db.Model):
    __tablename__ = "orders"
    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey("restaurants.id"), nullable=False)
    table_id = db.Column(db.Integer, db.ForeignKey("tables.id"), nullable=False)
    waiter_id = db.Column(db.Integer, db.ForeignKey("staff.id"), nullable=True)
    status = db.Column(db.String(20), default="open")  # open / paid / closed
    total = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    closed_at = db.Column(db.DateTime)

    items = db.relationship("OrderItem", backref="order", cascade="all, delete-orphan")


class OrderItem(db.Model):
    __tablename__ = "order_items"
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    price_at_time = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default="pending")  # pending / served
    note = db.Column(db.String(255))

    product = db.relationship("Product")