from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms.validators import InputRequired


from wtforms import (
    StringField,
    DateField,
    IntegerField,
    FloatField,
    SelectField,
    TextAreaField,
    SubmitField,
    BooleanField,
)
from wtforms.validators import DataRequired, Email, Length, NumberRange, Optional


STATUS_CHOICES = [
    ("new", "new"),
    ("in_progress", "in_progress"),
    ("pending_docs", "pending_docs"),
    ("pending_payment", "pending_payment"),
    ("confirmed", "confirmed"),
    ("ticketed", "ticketed"),
    ("completed", "completed"),
    ("canceled", "canceled"),
    ("issue", "issue"),
    ("refund_requested", "refund_requested"),
    ("refunded", "refunded"),
]

CURRENCY_CHOICES = [
    ("EUR", "EUR"),
    ("ALL", "ALL"),
    ("USD", "USD"),
    ("GBP", "GBP"),
]

BOOKING_TYPE_CHOICES = [
    ("combined", "combined"),
    ("flight", "flight"),
    ("hotel", "hotel"),
    ("visa", "visa"),
    ("package", "package"),
    ("other", "other"),
]


def empty_to_zero(v):
    # bosh -> 0, por 0 mbetet 0
    if v is None:
        return 0
    if isinstance(v, str) and v.strip() == "":
        return 0
    return v


def empty_to_zero_int(v):
    if v is None:
        return 0
    if isinstance(v, str) and v.strip() == "":
        return 0
    return v


class BookingCreateForm(FlaskForm):
    # Client (required)
    first_name = StringField("First name", validators=[DataRequired(), Length(max=100)])
    last_name = StringField("Last name", validators=[DataRequired(), Length(max=100)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=180)])
    phone = StringField("Phone", validators=[DataRequired(), Length(max=50)])

    # Dates
    birth_date = DateField("Birth date", format="%Y-%m-%d", validators=[Optional()])
    passport_no = StringField("Passport no", validators=[Optional(), Length(max=80)])
    passport_expiry = DateField("Passport expiry", format="%Y-%m-%d", validators=[Optional()])
    nationality = StringField("Nationality", validators=[Optional(), Length(max=80)])
    address = StringField("Address", validators=[Optional(), Length(max=255)])

    client_notes = TextAreaField("Client notes", validators=[Optional()])

    # Booking
    booking_type = SelectField(
        "Booking type",
        choices=BOOKING_TYPE_CHOICES,
        default="combined",
        validators=[DataRequired()],
    )
    departure_city = StringField("Departure city", validators=[Optional(), Length(max=120)])
    destination = StringField("Destination", validators=[DataRequired(), Length(max=120)])

    travel_date = DateField("Travel date", format="%Y-%m-%d", validators=[Optional()])
    return_date = DateField("Return date", format="%Y-%m-%d", validators=[Optional()])

    # Pax fields
    # Pax zakonisht duhet i detyrueshëm (min 1)
    num_pax = IntegerField("Pax", validators=[InputRequired(), NumberRange(min=1)], default=1)

    # adults/children: bosh -> 0 (ose 1 për adults, por default e mban 1)
    adults = IntegerField(
        "Adults",
        validators=[Optional(), NumberRange(min=0)],
        default=1,
        filters=[empty_to_zero_int],
    )

    children = IntegerField(
        "Children",
        validators=[Optional(), NumberRange(min=0)],
        default=0,
        filters=[empty_to_zero_int],
    )

    hotel_name = StringField("Hotel name", validators=[Optional(), Length(max=150)])
    flight_numbers = StringField("Flight numbers", validators=[Optional(), Length(max=255)])
    pnr = StringField("PNR", validators=[Optional(), Length(max=50)])

    currency = SelectField(
        "Currency",
        choices=CURRENCY_CHOICES,
        default="EUR",
        validators=[DataRequired()],
    )

    total_price = FloatField("Total price", validators=[DataRequired(), NumberRange(min=0)], default=0)

    # Money fields: bosh -> 0
    discount = FloatField(
        "Discount",
        validators=[Optional(), NumberRange(min=0)],
        default=0,
        filters=[empty_to_zero],
    )

    service_fee = FloatField(
        "Service fee",
        validators=[Optional(), NumberRange(min=0)],
        default=0,
        filters=[empty_to_zero],
    )

    extras_total = FloatField(
        "Extras total",
        validators=[Optional(), NumberRange(min=0)],
        default=0,
        filters=[empty_to_zero],
    )

    internal_cost = FloatField(
        "Internal cost",
        validators=[Optional(), NumberRange(min=0)],
        default=0,
        filters=[empty_to_zero],
    )

    status = SelectField(
        "Status",
        choices=STATUS_CHOICES,
        default="new",
        validators=[DataRequired()],
    )

    booking_notes = TextAreaField("Booking notes", validators=[Optional()])

    submit = SubmitField("Create Booking")


PAYMENT_METHODS = [
    ("cash", "cash"),
    ("bank", "bank"),
    ("card", "card"),
    ("online", "online"),
]

DOC_TYPES = [
    ("passport", "passport"),
    ("id_card", "id_card"),
    ("ticket", "ticket"),
    ("visa", "visa"),
    ("insurance", "insurance"),
    ("invoice", "invoice"),
    ("contract", "contract"),
    ("hotel_voucher", "hotel_voucher"),
    ("other", "other"),
]


class PaymentCreateForm(FlaskForm):
    amount = FloatField("Amount", validators=[DataRequired(), NumberRange(min=0.01)])
    method = SelectField("Method", choices=PAYMENT_METHODS, default="cash", validators=[DataRequired()])
    currency = SelectField("Currency", choices=CURRENCY_CHOICES, default="EUR", validators=[DataRequired()])
    note = StringField("Note", validators=[Optional(), Length(max=255)])
    submit = SubmitField("Add Payment")


class DocumentUploadForm(FlaskForm):
    doc_type = SelectField("Doc type", choices=DOC_TYPES, default="passport", validators=[DataRequired()])
    is_required = BooleanField("Required doc", default=False)
    file = FileField(
        "File",
        validators=[
            DataRequired(),
            FileAllowed(["pdf", "jpg", "jpeg", "png", "webp"], "Allowed: pdf, jpg, png, webp"),
        ],
    )
    submit = SubmitField("Upload")


class BookingFilterForm(FlaskForm):
    q = StringField("Search", validators=[Optional(), Length(max=120)])  # reference/client/email/phone
    destination = StringField("Destination", validators=[Optional(), Length(max=120)])

    status = SelectField(
        "Status",
        choices=[("", "all")] + STATUS_CHOICES,
        default="",
        validators=[Optional()],
    )

    date_from = DateField("From", format="%Y-%m-%d", validators=[Optional()])
    date_to = DateField("To", format="%Y-%m-%d", validators=[Optional()])

    agent_id = SelectField("Agent", choices=[("", "all")], default="", validators=[Optional()])

    submit = SubmitField("Filter")
