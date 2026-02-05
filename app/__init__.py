from flask import Flask, redirect, url_for
from .config import Config
from .extensions import db, migrate, login_manager


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Init extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    # Import models (kritike për migrations)
    from . import models  # noqa: F401

    # Import blueprints
    from .auth.routes import auth_bp
    from .dashboard.routes import dashboard_bp
    from .bookings.routes import bookings_bp
    from .clients import clients_bp  
    from .reports import reports_bp
    




    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(bookings_bp)
    app.register_blueprint(clients_bp)
    app.register_blueprint(reports_bp)
     

    # Root → login
    @app.route("/")
    def index():
        return redirect(url_for("auth.login"))

    return app
