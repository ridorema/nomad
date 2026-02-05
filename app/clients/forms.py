from flask_wtf import FlaskForm
from wtforms import StringField, DateField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Email, Length, Optional


class ClientEditForm(FlaskForm):
    first_name = StringField("First name", validators=[DataRequired(), Length(max=100)])
    last_name = StringField("Last name", validators=[DataRequired(), Length(max=100)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=180)])
    phone = StringField("Phone", validators=[DataRequired(), Length(max=50)])

    birth_date = DateField("Birth date", format="%Y-%m-%d", validators=[Optional()])
    passport_no = StringField("Passport no", validators=[Optional(), Length(max=80)])
    passport_expiry = DateField("Passport expiry", format="%Y-%m-%d", validators=[Optional()])
    nationality = StringField("Nationality", validators=[Optional(), Length(max=80)])
    address = StringField("Address", validators=[Optional(), Length(max=255)])

    notes = TextAreaField("Notes", validators=[Optional()])

    submit = SubmitField("Save changes")
