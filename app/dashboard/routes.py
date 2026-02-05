from flask import Blueprint, render_template
from flask_login import login_required, current_user
from sqlalchemy import func
from ..extensions import db
from ..models import Booking, Client, Payment, ActivityLog

dashboard_bp = Blueprint("dashboard", __name__)

BASE = "EUR"

@dashboard_bp.route("/dashboard")
@login_required
def home():
    # Scope (admin sees all, agent sees own)
    bookings_q = Booking.query.filter_by(is_archived=False)
    clients_q = Client.query.filter_by(is_archived=False)
    payments_q = Payment.query.filter_by(is_archived=False)

    if current_user.role != "admin":
        bookings_q = bookings_q.filter(Booking.agent_id == current_user.id)
        clients_q = clients_q.filter(Client.agent_id == current_user.id)
        payments_q = payments_q.filter(Payment.agent_id == current_user.id)

    total_bookings = bookings_q.count()
    active_bookings = bookings_q.filter(Booking.status != "completed").count()

    total_clients = clients_q.count()
    archived_clients = Client.query.filter_by(is_archived=True).count() if current_user.role == "admin" else \
        Client.query.filter_by(is_archived=True, agent_id=current_user.id).count()

    # Payments converted to BASE using a simple rule:
    # For now: assume amount already entered in base currency if currency != base.
    # We'll add fx_rate field later if you want strict conversion per payment.
    # (We can improve in Sprint 2)
    collected_eur = float(payments_q.with_entities(func.coalesce(func.sum(Payment.amount), 0)).scalar() or 0)
    total_payments = payments_q.count()

    # Outstanding (base) = sum(total_price) - sum(payments)
    revenue_eur = float(bookings_q.with_entities(func.coalesce(func.sum(Booking.total_price), 0)).scalar() or 0)
    outstanding_eur = max(0.0, revenue_eur - collected_eur)

    pending_payment = bookings_q.filter(Booking.status == "pending_payment").count()

    recent_bookings = bookings_q.order_by(Booking.created_at.desc()).limit(10).all()

    top_destinations = (
        bookings_q.with_entities(Booking.destination, func.count(Booking.id))
        .group_by(Booking.destination)
        .order_by(func.count(Booking.id).desc())
        .limit(6)
        .all()
    )

    logs_q = ActivityLog.query
    if current_user.role != "admin":
        logs_q = logs_q.filter(ActivityLog.user_id == current_user.id)

    recent_logs = logs_q.order_by(ActivityLog.created_at.desc()).limit(8).all()

    kpi = {
        "total_bookings": total_bookings,
        "active_bookings": active_bookings,
        "total_clients": total_clients,
        "archived_clients": archived_clients,
        "collected_eur": collected_eur,
        "total_payments": total_payments,
        "outstanding_eur": outstanding_eur,
        "pending_payment": pending_payment,
    }

    return render_template(
        "dashboard/home.html",
        kpi=kpi,
        recent_bookings=recent_bookings,
        top_destinations=top_destinations,
        recent_logs=recent_logs,
    )
