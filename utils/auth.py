from functools import wraps
from flask import session, redirect, url_for, flash

def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if session.get("role") != "admin":
            flash("Yönetici girişi gerekli.", "error")
            return redirect(url_for("admin.login"))
        return f(*args, **kwargs)
    return wrapper


def waiter_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if session.get("role") not in ("waiter", "admin"):
            flash("Giriş yapmalısınız.", "error")
            return redirect(url_for("waiter.login"))
        return f(*args, **kwargs)
    return wrapper