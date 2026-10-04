import os
from flask import Flask, render_template
from config import Config
from database.db import db

from routes.setup_routes import setup_bp
from routes.admin_routes import admin_bp
from routes.waiter_routes import waiter_bp
from routes.customer_routes import customer_bp


def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)

    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["QR_FOLDER"], exist_ok=True)

    db.init_app(app)

    app.register_blueprint(setup_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(waiter_bp)
    app.register_blueprint(customer_bp)

    with app.app_context():
        db.create_all()

    @app.errorhandler(404)
    def not_found(e):
        return render_template("base.html", message="Sayfa bulunamadı"), 404

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host="0.0.0.0", port=8000)