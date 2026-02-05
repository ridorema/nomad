from datetime import datetime, date
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.dialects.sqlite import JSON
from .extensions import db, login_manager
from app.extensions import db



# =========================
# USER
# =========================
class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(180), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    role = db.Column(db.String(20), nullable=False, default="agent")  # admin / agent
    default_commission_percent = db.Column(db.Float, default=10.0)

    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# =========================
# CLIENT
# =========================
class Client(db.Model):
    __tablename__ = "clients"

    id = db.Column(db.Integer, primary_key=True)
    agent_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)

    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(180), nullable=False, index=True)
    phone = db.Column(db.String(50), nullable=False, index=True)

    birth_date = db.Column(db.Date, nullable=True)
    passport_no = db.Column(db.String(80), nullable=True)
    passport_expiry = db.Column(db.Date, nullable=True)
    nationality = db.Column(db.String(80), nullable=True)
    address = db.Column(db.String(255), nullable=True)

    notes = db.Column(db.Text, nullable=True)
    tags = db.Column(JSON, default=list)

    is_archived = db.Column(db.Boolean, default=False)
    archived_at = db.Column(db.DateTime, nullable=True)
    archived_by = db.Column(db.Integer, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    bookings = db.relationship("Booking", backref="client", lazy=True)


# =========================
# BOOKING
# =========================
class Booking(db.Model):
    __tablename__ = "bookings"

    id = db.Column(db.Integer, primary_key=True)
    reference = db.Column(db.String(30), unique=True, nullable=False, index=True)

    agent_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    client_id = db.Column(db.Integer, db.ForeignKey("clients.id"), nullable=False, index=True)

    booking_type = db.Column(db.String(50), default="combined")

    departure_city = db.Column(db.String(120), nullable=True)
    destination = db.Column(db.String(120), nullable=False)

    travel_date = db.Column(db.Date, nullable=True)
    return_date = db.Column(db.Date, nullable=True)

    num_pax = db.Column(db.Integer, default=1)
    adults = db.Column(db.Integer, default=1)
    children = db.Column(db.Integer, default=0)

    hotel_name = db.Column(db.String(150), nullable=True)
    flight_numbers = db.Column(db.String(255), nullable=True)
    pnr = db.Column(db.String(50), nullable=True)

    currency = db.Column(db.String(10), default="EUR")

    total_price = db.Column(db.Float, default=0)
    discount = db.Column(db.Float, default=0)
    service_fee = db.Column(db.Float, default=0)
    extras_total = db.Column(db.Float, default=0)

    internal_cost = db.Column(db.Float, default=0)

    commission_percent_override = db.Column(db.Float, nullable=True)

    status = db.Column(db.String(40), default="new")

    cancel_reason = db.Column(db.String(255), nullable=True)
    refund_amount = db.Column(db.Float, nullable=True)
    refund_date = db.Column(db.Date, nullable=True)

    invoice_no = db.Column(db.String(40), nullable=True)

    is_archived = db.Column(db.Boolean, default=False)
    archived_at = db.Column(db.DateTime, nullable=True)
    archived_by = db.Column(db.Integer, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    payments = db.relationship("Payment", backref="booking", lazy=True)
    documents = db.relationship("Document", backref="booking", lazy=True)

    def paid_amount(self):
        return sum(p.amount for p in self.payments)

    def due_amount(self):
        return max(0, self.total_price - self.paid_amount())

    def profit(self):
        return max(0, self.total_price - self.internal_cost)


# =========================
# PAYMENT
# =========================
class Payment(db.Model):
    __tablename__ = "payments"

    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey("bookings.id"), nullable=False)
    agent_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    currency = db.Column(db.String(10), default="EUR")
    amount = db.Column(db.Float, nullable=False)
    method = db.Column(db.String(20), default="cash")

    receipt_no = db.Column(db.String(40), nullable=True)
    paid_at = db.Column(db.DateTime, default=datetime.utcnow)
    note = db.Column(db.String(255), nullable=True)

    is_archived = db.Column(db.Boolean, default=False)


# =========================
# DOCUMENT
# =========================
class Document(db.Model):
    __tablename__ = "documents"

    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey("clients.id"), nullable=False)
    booking_id = db.Column(db.Integer, db.ForeignKey("bookings.id"), nullable=False)

    doc_type = db.Column(db.String(50), nullable=False)
    file_path = db.Column(db.String(400), nullable=False)
    original_name = db.Column(db.String(255), nullable=True)

    is_required = db.Column(db.Boolean, default=False)

    uploaded_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    is_archived = db.Column(db.Boolean, default=False)


# =========================
# ACTIVITY LOG
# =========================
class ActivityLog(db.Model):
    __tablename__ = "activity_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))

    action = db.Column(db.String(100), nullable=False)
    entity_type = db.Column(db.String(50), nullable=False)
    entity_id = db.Column(db.Integer, nullable=True)

    meta = db.Column(JSON, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)



@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
