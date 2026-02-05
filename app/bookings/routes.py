import os
from datetime import datetime
from werkzeug.utils import secure_filename

from flask import Blueprint, render_template, redirect, url_for, flash, current_app, abort, request
from flask_login import login_required, current_user
from sqlalchemy import or_

from ..extensions import db
from ..models import Client, Booking, Payment, Document, ActivityLog, User
from ..utils.reference import next_booking_reference, next_receipt_no
from .forms import BookingCreateForm, PaymentCreateForm, DocumentUploadForm, BookingFilterForm


bookings_bp = Blueprint("bookings", __name__, url_prefix="/bookings")

REQUIRED_DOCS_DEFAULT = ["passport", "ticket"]  # mund ta ndryshojmë më vonë


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


def get_booking_or_404(booking_id: int) -> Booking:
    b = Booking.query.get_or_404(booking_id)
    if current_user.role != "admin" and b.agent_id != current_user.id:
        abort(403)
    return b


@bookings_bp.route("/new", methods=["GET", "POST"])
@login_required
def create():
    form = BookingCreateForm()

    if form.validate_on_submit():
        assigned_agent_id = current_user.id

        email = form.email.data.strip()
        phone = form.phone.data.strip()

        # ✅ UPDATE vetëm nëse EMAIL + PHONE janë të njëjta
        client = Client.query.filter(
            Client.email == email,
            Client.phone == phone,
            Client.is_archived.is_(False),
        ).first()

        if client:
            # update client info
            client.first_name = form.first_name.data.strip()
            client.last_name = form.last_name.data.strip()
            client.birth_date = form.birth_date.data
            client.passport_no = form.passport_no.data.strip() if form.passport_no.data else None
            client.passport_expiry = form.passport_expiry.data
            client.nationality = form.nationality.data.strip() if form.nationality.data else None
            client.address = form.address.data.strip() if form.address.data else None
            client.notes = form.client_notes.data.strip() if form.client_notes.data else None

            log_action(
                "Client updated via booking",
                "Client",
                client.id,
                {"email": client.email, "phone": client.phone},
            )
        else:
            # create new client
            client = Client(
                agent_id=assigned_agent_id,
                first_name=form.first_name.data.strip(),
                last_name=form.last_name.data.strip(),
                email=email,
                phone=phone,
                birth_date=form.birth_date.data,
                passport_no=form.passport_no.data.strip() if form.passport_no.data else None,
                passport_expiry=form.passport_expiry.data,
                nationality=form.nationality.data.strip() if form.nationality.data else None,
                address=form.address.data.strip() if form.address.data else None,
                notes=form.client_notes.data.strip() if form.client_notes.data else None,
                tags=[],
            )
            db.session.add(client)
            db.session.flush()

            log_action(
                "Client created via booking",
                "Client",
                client.id,
                {"email": client.email, "phone": client.phone},
            )

        # booking
        booking = Booking(
            reference=next_booking_reference("OUT"),
            agent_id=assigned_agent_id,
            client_id=client.id,
            booking_type=form.booking_type.data,
            departure_city=form.departure_city.data.strip() if form.departure_city.data else None,
            destination=form.destination.data.strip(),
            travel_date=form.travel_date.data,
            return_date=form.return_date.data,
            num_pax=form.num_pax.data,
            adults=form.adults.data,
            children=form.children.data,
            hotel_name=form.hotel_name.data.strip() if form.hotel_name.data else None,
            flight_numbers=form.flight_numbers.data.strip() if form.flight_numbers.data else None,
            pnr=form.pnr.data.strip() if form.pnr.data else None,
            currency=form.currency.data,
            total_price=form.total_price.data or 0,
            discount=form.discount.data or 0,
            service_fee=form.service_fee.data or 0,
            extras_total=form.extras_total.data or 0,
            internal_cost=form.internal_cost.data or 0,
            status=form.status.data,
        )
        db.session.add(booking)
        db.session.flush()

        log_action("Created booking", "Booking", booking.id, {"reference": booking.reference, "status": booking.status})

        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print("COMMIT ERROR (UI create):", repr(e))
            flash("Database error while saving booking.", "danger")
            return render_template("bookings/new.html", form=form)

        flash(f"Booking created: {booking.reference}", "success")
        return redirect(url_for("bookings.detail", booking_id=booking.id))

    if request.method == "POST":
        print("FORM ERRORS:", form.errors)
        flash("Form has errors. Please check the fields highlighted below.", "danger")

    return render_template("bookings/new.html", form=form)



@bookings_bp.route("/<int:booking_id>")
@login_required
def detail(booking_id):
    b = get_booking_or_404(booking_id)
    client = Client.query.get(b.client_id)

    payments = (
        Payment.query.filter_by(booking_id=b.id, is_archived=False)
        .order_by(Payment.paid_at.desc())
        .all()
    )
    docs = (
        Document.query.filter_by(booking_id=b.id, is_archived=False)
        .order_by(Document.created_at.desc())
        .all()
    )

    uploaded_types = {d.doc_type for d in docs}
    required_docs = REQUIRED_DOCS_DEFAULT[:]
    missing_docs = [t for t in required_docs if t not in uploaded_types]

    payment_form = PaymentCreateForm()
    doc_form = DocumentUploadForm()

    logs_q = ActivityLog.query
    if current_user.role != "admin":
        logs_q = logs_q.filter(ActivityLog.user_id == current_user.id)
    recent_logs = logs_q.order_by(ActivityLog.created_at.desc()).limit(10).all()

    return render_template(
        "bookings/detail.html",
        booking=b,
        client=client,
        payments=payments,
        docs=docs,
        missing_docs=missing_docs,
        payment_form=payment_form,
        doc_form=doc_form,
        recent_logs=recent_logs,
    )


@bookings_bp.route("/<int:booking_id>/edit", methods=["GET", "POST"])
@login_required
def edit(booking_id):
    b = get_booking_or_404(booking_id)
    client = Client.query.get_or_404(b.client_id)

    form = BookingCreateForm(obj=b)
    # mbush edhe fushat e klientit
    if request.method == "GET":
        form.first_name.data = client.first_name
        form.last_name.data = client.last_name
        form.email.data = client.email
        form.phone.data = client.phone
        form.birth_date.data = client.birth_date
        form.passport_no.data = client.passport_no
        form.passport_expiry.data = client.passport_expiry
        form.nationality.data = client.nationality
        form.address.data = client.address
        form.client_notes.data = client.notes

    if form.validate_on_submit():
        # update client
        client.first_name = form.first_name.data.strip()
        client.last_name = form.last_name.data.strip()
        client.email = form.email.data.strip()
        client.phone = form.phone.data.strip()
        client.birth_date = form.birth_date.data
        client.passport_no = form.passport_no.data.strip() if form.passport_no.data else None
        client.passport_expiry = form.passport_expiry.data
        client.nationality = form.nationality.data.strip() if form.nationality.data else None
        client.address = form.address.data.strip() if form.address.data else None
        client.notes = form.client_notes.data.strip() if form.client_notes.data else None

        # update booking
        b.booking_type = form.booking_type.data
        b.departure_city = form.departure_city.data.strip() if form.departure_city.data else None
        b.destination = form.destination.data.strip()
        b.travel_date = form.travel_date.data
        b.return_date = form.return_date.data
        b.num_pax = form.num_pax.data
        b.adults = form.adults.data
        b.children = form.children.data
        b.hotel_name = form.hotel_name.data.strip() if form.hotel_name.data else None
        b.flight_numbers = form.flight_numbers.data.strip() if form.flight_numbers.data else None
        b.pnr = form.pnr.data.strip() if form.pnr.data else None
        b.currency = form.currency.data
        b.total_price = form.total_price.data or 0
        b.discount = form.discount.data or 0
        b.service_fee = form.service_fee.data or 0
        b.extras_total = form.extras_total.data or 0
        b.internal_cost = form.internal_cost.data or 0
        b.status = form.status.data

        log_action("Updated booking", "Booking", b.id, {"reference": b.reference})
        db.session.commit()

        flash("Booking updated successfully.", "success")
        return redirect(url_for("bookings.detail", booking_id=b.id))

    if request.method == "POST":
        print("FORM ERRORS (edit):", form.errors)
        flash("Form has errors. Please fix highlighted fields.", "danger")

    return render_template("bookings/edit.html", form=form, booking=b)



@bookings_bp.route("/<int:booking_id>/payments/add", methods=["POST"])
@login_required
def add_payment(booking_id):
    b = get_booking_or_404(booking_id)
    form = PaymentCreateForm()

    if not form.validate_on_submit():
        flash("Invalid payment data.", "danger")
        return redirect(url_for("bookings.detail", booking_id=b.id))

    p = Payment(
        booking_id=b.id,
        agent_id=b.agent_id,
        currency=form.currency.data,
        amount=form.amount.data,
        method=form.method.data,
        note=form.note.data.strip() if form.note.data else None,
        receipt_no=next_receipt_no(),
        paid_at=datetime.utcnow(),
    )
    db.session.add(p)
    db.session.flush()

    log_action("Payment added", "Payment", p.id, {"booking_id": b.id, "amount": p.amount, "currency": p.currency})

    # Auto status update (simple rule)
    if b.due_amount() - p.amount <= 0 and b.status in ("new", "in_progress", "pending_payment"):
        b.status = "confirmed"
        log_action("Booking status updated", "Booking", b.id, {"status": b.status})

    db.session.commit()
    flash("Payment added successfully.", "success")
    return redirect(url_for("bookings.detail", booking_id=b.id))


@bookings_bp.route("/<int:booking_id>/docs/upload", methods=["POST"])
@login_required
def upload_doc(booking_id):
    b = get_booking_or_404(booking_id)
    form = DocumentUploadForm()

    if not form.validate_on_submit():
        flash("Invalid document upload.", "danger")
        return redirect(url_for("bookings.detail", booking_id=b.id))

    f = form.file.data
    filename = secure_filename(f.filename or "")
    if not filename:
        flash("Invalid filename.", "danger")
        return redirect(url_for("bookings.detail", booking_id=b.id))

    root = current_app.config.get("UPLOAD_FOLDER", "uploads")
    folder = os.path.join(root, "bookings", str(b.id))
    os.makedirs(folder, exist_ok=True)

    ext = os.path.splitext(filename)[1].lower()
    safe_name = f"{form.doc_type.data}_{int(datetime.utcnow().timestamp())}{ext}"
    save_path = os.path.join(folder, safe_name)
    f.save(save_path)

    doc = Document(
        client_id=b.client_id,
        booking_id=b.id,
        doc_type=form.doc_type.data,
        file_path=save_path.replace("\\", "/"),
        original_name=filename,
        is_required=bool(form.is_required.data),
        uploaded_by=current_user.id,
    )
    db.session.add(doc)
    db.session.flush()

    log_action("Document uploaded", "Document", doc.id, {"booking_id": b.id, "type": doc.doc_type})

    db.session.commit()
    flash("Document uploaded.", "success")
    return redirect(url_for("bookings.detail", booking_id=b.id))


@bookings_bp.route("", methods=["GET"])
@login_required
def list_bookings():
    form = BookingFilterForm(request.args)

    # Base query + join me Client (për kërkim)
    q = (
        Booking.query.join(Client, Booking.client_id == Client.id)
        .filter(or_(Booking.is_archived.is_(False), Booking.is_archived.is_(None)))
    )

    # Scope: admin all, agent own only
    if current_user.role != "admin":
        q = q.filter(Booking.agent_id == current_user.id)

    # Populate agent dropdown (admin only)
    if current_user.role == "admin":
        agents = User.query.filter_by(role="agent", is_active=True).order_by(User.full_name.asc()).all()
        form.agent_id.choices = [("", "all")] + [(str(a.id), a.full_name) for a in agents]

        if form.agent_id.data:
            q = q.filter(Booking.agent_id == int(form.agent_id.data))
    else:
        form.agent_id.choices = [("", "all")]

    # Text search
    if form.q.data:
        term = f"%{form.q.data.strip()}%"
        q = q.filter(
            or_(
                Booking.reference.ilike(term),
                Client.first_name.ilike(term),
                Client.last_name.ilike(term),
                Client.email.ilike(term),
                Client.phone.ilike(term),
            )
        )

    if form.destination.data:
        term = f"%{form.destination.data.strip()}%"
        q = q.filter(Booking.destination.ilike(term))

    if form.status.data:
        q = q.filter(Booking.status == form.status.data)

    if form.date_from.data:
        q = q.filter(Booking.travel_date >= form.date_from.data)
    if form.date_to.data:
        q = q.filter(Booking.travel_date <= form.date_to.data)

    # Pagination
    page = request.args.get("page", 1, type=int)
    per_page = 15
    pagination = q.order_by(Booking.created_at.desc()).paginate(page=page, per_page=per_page, error_out=False)

    args = request.args.to_dict(flat=True)
    args.pop("page", None)

    prev_url = None
    next_url = None
    if pagination.has_prev:
        prev_url = url_for("bookings.list_bookings", **args, page=pagination.prev_num)
    if pagination.has_next:
        next_url = url_for("bookings.list_bookings", **args, page=pagination.next_num)

    return render_template(
        "bookings/list.html",
        form=form,
        bookings=pagination.items,
        pagination=pagination,
        prev_url=prev_url,
        next_url=next_url,
    )
