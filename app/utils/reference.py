from datetime import datetime
from sqlalchemy import func
from ..extensions import db
from ..models import Booking, Payment

def next_booking_reference(prefix="OUT"):
    year = datetime.utcnow().year
    like = f"{prefix}-{year}-%"

    last_ref = (
        db.session.query(func.max(Booking.reference))
        .filter(Booking.reference.like(like))
        .scalar()
    )

    if not last_ref:
        seq = 1
    else:
        # OUT-2026-000123
        seq = int(last_ref.split("-")[-1]) + 1

    return f"{prefix}-{year}-{seq:06d}"


def next_receipt_no():
    year = datetime.utcnow().year
    like = f"RCPT-{year}-%"

    last_no = (
        db.session.query(func.max(Payment.receipt_no))
        .filter(Payment.receipt_no.like(like))
        .scalar()
    )

    if not last_no:
        seq = 1
    else:
        seq = int(last_no.split("-")[-1]) + 1

    return f"RCPT-{year}-{seq:06d}"
