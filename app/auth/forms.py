from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SelectField, SubmitField
from wtforms.validators import DataRequired, Email, Length, Optional


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=180)])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Login")


class AgentCreateForm(FlaskForm):
    full_name = StringField("Full name", validators=[DataRequired(), Length(min=2, max=120)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=180)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=6)])

    role = SelectField(
        "Role",
        choices=[("agent", "Agent"), ("admin", "Admin")],
        default="agent",
    )

    is_active = BooleanField("Active", default=True)
    submit = SubmitField("Create user")


class AgentEditForm(FlaskForm):
    full_name = StringField("Full name", validators=[DataRequired(), Length(min=2, max=120)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=180)])

    password = PasswordField(
        "New password (optional)",
        validators=[Optional(), Length(min=6)],
    )

    role = SelectField(
        "Role",
        choices=[("agent", "Agent"), ("admin", "Admin")],
        default="agent",
    )

    is_active = BooleanField("Active")
    submit = SubmitField("Save changes")
