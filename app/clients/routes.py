from flask import render_template, redirect, url_for, flash, abort, request
from flask_login import login_required, current_user

from ..extensions import db
from ..models import Client, Booking, Document, Payment, ActivityLog
from . import clients_bp
from .forms import ClientEditForm


def get_client_or_404(client_id: int) -> Client:
    c = Client.query.get_or_404(client_id)
    if current_user.role != "admin" and c.agent_id != current_user.id:
        abort(403)
    return c


def log_action(action, entity_type, entity_id=None, meta=None):
    db.session.add(
        ActivityLog(
            user_id=current_user.id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            meta=meta or {},
        )
    )


@clients_bp.route("", methods=["GET"])
@login_required
def list_clients():
    # Base query: only active (not archived)
    q = Client.query.filter(Client.is_archived.is_(False))

    # Scope: admin all, agent only own
    if current_user.role != "admin":
        q = q.filter(Client.agent_id == current_user.id)

    # Optional search
    term = (request.args.get("q") or "").strip()
    if term:
        like = f"%{term}%"
        q = q.filter(
            (Client.first_name.ilike(like))
            | (Client.last_name.ilike(like))
            | (Client.email.ilike(like))
            | (Client.phone.ilike(like))
        )

    clients = q.order_by(Client.created_at.desc()).all()
    return render_template("clients/list.html", clients=clients, q=term)


@clients_bp.route("/<int:client_id>", methods=["GET"])
@login_required
def detail(client_id):
    client = get_client_or_404(client_id)

    # History (bookings)
    bookings = (
        Booking.query.filter_by(client_id=client.id)
        .order_by(Booking.created_at.desc())
        .all()
    )

    # Documents (all for this client)
    docs = (
        Document.query.filter_by(client_id=client.id, is_archived=False)
        .order_by(Document.created_at.desc())
        .all()
    )

    # Payments (via booking ids)
    booking_ids = [b.id for b in bookings]
    payments = []
    if booking_ids:
        payments = (
            Payment.query.filter(Payment.booking_id.in_(booking_ids), Payment.is_archived.is_(False))
            .order_by(Payment.paid_at.desc())
            .all()
        )

    # Recent logs (simple)
    logs_q = ActivityLog.query.filter(ActivityLog.entity_type.in_(["Client", "Booking", "Document", "Payment"]))
    if current_user.role != "admin":
        logs_q = logs_q.filter(ActivityLog.user_id == current_user.id)
    recent_logs = logs_q.order_by(ActivityLog.created_at.desc()).limit(15).all()

    return render_template(
        "clients/detail.html",
        client=client,
        bookings=bookings,
        docs=docs,
        payments=payments,
        recent_logs=recent_logs,
    )


@clients_bp.route("/<int:client_id>/edit", methods=["GET", "POST"])
@login_required
def edit(client_id):
    client = get_client_or_404(client_id)
    form = ClientEditForm(obj=client)

    if form.validate_on_submit():
        client.first_name = form.first_name.data.strip()
        client.last_name = form.last_name.data.strip()
        client.email = form.email.data.strip()
        client.phone = form.phone.data.strip()

        client.birth_date = form.birth_date.data
        client.passport_no = form.passport_no.data.strip() if form.passport_no.data else None
        client.passport_expiry = form.passport_expiry.data
        client.nationality = form.nationality.data.strip() if form.nationality.data else None
        client.address = form.address.data.strip() if form.address.data else None
        client.notes = form.notes.data.strip() if form.notes.data else None

        log_action("Updated client", "Client", client.id, {"email": client.email, "phone": client.phone})
        db.session.commit()

        flash("Client updated successfully.", "success")
        return redirect(url_for("clients.detail", client_id=client.id))

    if request.method == "POST":
        flash("Form has errors. Please fix highlighted fields.", "danger")

    return render_template("clients/edit.html", form=form, client=client)
