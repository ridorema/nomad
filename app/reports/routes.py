from datetime import datetime, date
from flask import render_template, request, abort
from flask_login import login_required, current_user
from sqlalchemy import func

from ..extensions import db
from ..models import Booking, Payment, User
from . import reports_bp



def require_admin():
    if current_user.role != "admin":
        abort(403)


def parse_date(value: str):
    """
    Pret YYYY-MM-DD, kthen date ose None.
    """
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def booking_scope_query(agent_id: int | None, date_from: date | None, date_to: date | None):
    """
    Kthen query për bookings me scope + filters.
    - agent_id: None => all agents (vetëm admin)
    - date_from/to: filtron sipas Booking.created_at (DATE)
    """
    q = Booking.query.filter(func.coalesce(Booking.is_archived, False) == False)  # noqa: E712

    if agent_id is not None:
        q = q.filter(Booking.agent_id == agent_id)

    if date_from:
        q = q.filter(func.date(Booking.created_at) >= date_from)
    if date_to:
        q = q.filter(func.date(Booking.created_at) <= date_to)

    return q


def payments_scope_query(agent_id: int | None, date_from: date | None, date_to: date | None):
    """
    Payments në të njëjtën periudhë, për total Paid.
    """
    q = Payment.query.filter(func.coalesce(Payment.is_archived, False) == False)  # noqa: E712

    if agent_id is not None:
        q = q.filter(Payment.agent_id == agent_id)

    if date_from:
        q = q.filter(func.date(Payment.paid_at) >= date_from)
    if date_to:
        q = q.filter(func.date(Payment.paid_at) <= date_to)

    return q


def compute_kpis(agent_id: int | None, date_from: date | None, date_to: date | None):
    # Bookings KPIs
    bq = booking_scope_query(agent_id, date_from, date_to)

    total_bookings = bq.with_entities(func.count(Booking.id)).scalar() or 0
    revenue = bq.with_entities(func.coalesce(func.sum(Booking.total_price), 0.0)).scalar() or 0.0
    internal_cost = bq.with_entities(func.coalesce(func.sum(Booking.internal_cost), 0.0)).scalar() or 0.0

    profit = float(revenue) - float(internal_cost)

    # Paid KPIs
    pq = payments_scope_query(agent_id, date_from, date_to)
    paid = pq.with_entities(func.coalesce(func.sum(Payment.amount), 0.0)).scalar() or 0.0

    due = float(revenue) - float(paid)

    avg_booking = (float(revenue) / total_bookings) if total_bookings else 0.0
    margin = (profit / float(revenue) * 100.0) if float(revenue) > 0 else 0.0

    return {
        "total_bookings": int(total_bookings),
        "revenue": float(revenue),
        "paid": float(paid),
        "due": float(due),
        "internal_cost": float(internal_cost),
        "profit": float(profit),
        "avg_booking": float(avg_booking),
        "margin": float(margin),
    }


@reports_bp.route("", methods=["GET"])
@login_required
def dashboard():
    """
    - Admin: sheh total (all agents) dhe mund të filtrojë (opsionale) nga query.
    - Agent: sheh vetëm të vetat.
    """
    # Filters
    date_from = parse_date((request.args.get("date_from") or "").strip())
    date_to = parse_date((request.args.get("date_to") or "").strip())

    # Agent scope:
    # - agent user => e fiksuar
    # - admin => mund të shohë total (default) ose të filtrojë te vetët (opsionale)
    agent_id = None
    selected_agent_id = (request.args.get("agent_id") or "").strip()

    if current_user.role != "admin":
        agent_id = current_user.id
    else:
        if selected_agent_id.isdigit():
            agent_id = int(selected_agent_id)

    kpis = compute_kpis(agent_id=agent_id, date_from=date_from, date_to=date_to)

    agents = []
    if current_user.role == "admin":
        agents = User.query.filter_by(role="agent", is_active=True).order_by(User.full_name.asc()).all()

    return render_template(
        "reports/dashboard.html",
        kpis=kpis,
        agents=agents,
        date_from=date_from.isoformat() if date_from else "",
        date_to=date_to.isoformat() if date_to else "",
        selected_agent_id=str(agent_id) if (agent_id is not None and current_user.role == "admin") else "",
        is_admin=(current_user.role == "admin"),
    )


@reports_bp.route("/agents", methods=["GET"])
@login_required
def agents_overview():
    """
    Vetëm admin: listë e agjentëve + link për raport individual.
    """
    require_admin()
    agents = User.query.filter_by(role="agent", is_active=True).order_by(User.full_name.asc()).all()
    return render_template("reports/agents.html", agents=agents)


@reports_bp.route("/agent/<int:agent_id>", methods=["GET"])
@login_required
def agent_report(agent_id):
    """
    Vetëm admin: raport individual për një agjent të caktuar.
    """
    require_admin()

    date_from = parse_date((request.args.get("date_from") or "").strip())
    date_to = parse_date((request.args.get("date_to") or "").strip())

    agent = User.query.get_or_404(agent_id)
    if agent.role != "agent":
        abort(404)

    kpis = compute_kpis(agent_id=agent_id, date_from=date_from, date_to=date_to)

    return render_template(
        "reports/agent_report.html",
        agent=agent,
        kpis=kpis,
        date_from=date_from.isoformat() if date_from else "",
        date_to=date_to.isoformat() if date_to else "",
    )

@reports_bp.route("/outstanding", methods=["GET"])
@login_required
def outstanding():
    """
    Bookings me due > 0
    - Admin: all agents + filter by agent
    - Agent: only own
    Filters: date range (created_at), destination, status
    """
    date_from = parse_date((request.args.get("date_from") or "").strip())
    date_to = parse_date((request.args.get("date_to") or "").strip())
    destination = (request.args.get("destination") or "").strip()
    status = (request.args.get("status") or "").strip()
    selected_agent_id = (request.args.get("agent_id") or "").strip()

    # scope
    agent_id = None
    if current_user.role != "admin":
        agent_id = current_user.id
    else:
        if selected_agent_id.isdigit():
            agent_id = int(selected_agent_id)

    # base query bookings
    q = Booking.query.filter(func.coalesce(Booking.is_archived, False) == False)  # noqa: E712

    if agent_id is not None:
        q = q.filter(Booking.agent_id == agent_id)

    if date_from:
        q = q.filter(func.date(Booking.created_at) >= date_from)
    if date_to:
        q = q.filter(func.date(Booking.created_at) <= date_to)

    if destination:
        q = q.filter(Booking.destination.ilike(f"%{destination}%"))

    if status:
        q = q.filter(Booking.status == status)

    # Marrim listën dhe filtrojmë due > 0 në Python (sepse paid është relationship)
    bookings = q.order_by(Booking.created_at.desc()).all()

    rows = []
    total_due = 0.0
    total_revenue = 0.0
    total_paid = 0.0

    for b in bookings:
        paid = float(b.paid_amount() or 0.0)
        revenue = float(b.total_price or 0.0)
        due = max(0.0, revenue - paid)

        if due <= 0:
            continue

        rows.append({
            "booking": b,
            "paid": paid,
            "due": due,
            "revenue": revenue,
        })

        total_due += due
        total_paid += paid
        total_revenue += revenue

    # dropdown agents (admin only)
    agents = []
    if current_user.role == "admin":
        agents = User.query.filter_by(role="agent", is_active=True).order_by(User.full_name.asc()).all()

    return render_template(
        "reports/outstanding.html",
        rows=rows,
        total_due=total_due,
        total_paid=total_paid,
        total_revenue=total_revenue,
        agents=agents,
        is_admin=(current_user.role == "admin"),
        selected_agent_id=str(agent_id) if (agent_id is not None and current_user.role == "admin") else "",
        date_from=date_from.isoformat() if date_from else "",
        date_to=date_to.isoformat() if date_to else "",
        destination=destination,
        status=status,
        STATUS_CHOICES=[("","all"),("new","new"),("in_progress","in_progress"),("pending_docs","pending_docs"),
                        ("pending_payment","pending_payment"),("confirmed","confirmed"),("ticketed","ticketed"),
                        ("completed","completed"),("canceled","canceled"),("issue","issue"),
                        ("refund_requested","refund_requested"),("refunded","refunded")],
    )
