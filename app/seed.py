from app import create_app
from app.extensions import db
from app.models import User

app = create_app()

with app.app_context():
    admin_email = "admin@outgoingcrm.com"

    existing = User.query.filter_by(email=admin_email).first()
    if existing:
        print("Admin user already exists.")
    else:
        admin = User(
            full_name="System Admin",
            email=admin_email,
            role="admin",
            default_commission_percent=0
        )
        admin.set_password("admin123")

        db.session.add(admin)
        db.session.commit()

        print("Admin user created:")
        print("Email: admin@outgoingcrm.com")
        print("Password: admin123")
