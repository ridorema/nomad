from flask import render_template, redirect, url_for, flash, request, abort
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import check_password_hash

from .forms import LoginForm, AgentCreateForm, AgentEditForm
from ..models import User, ActivityLog
from ..extensions import db
from . import auth_bp


# =========================
# AUTH
# =========================

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.home"))

    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter_by(
            email=form.email.data.strip(),
            is_active=True
        ).first()

        if user and user.check_password(form.password.data):
            login_user(user)
            next_url = request.args.get("next")
            return redirect(next_url or url_for("dashboard.home"))

        flash("Invalid email or password", "danger")

    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out", "info")
    return redirect(url_for("auth.login"))


# =========================
# USERS / AGENTS (ADMIN ONLY)
# =========================

def admin_only():
    if current_user.role != "admin":
        abort(403)


@auth_bp.route("/users", endpoint="users_list")
@login_required
def users_list():
    admin_only()

    users = User.query.order_by(User.created_at.desc()).all()
    return render_template("auth/users_list.html", users=users)


@auth_bp.route("/users/new", methods=["GET", "POST"], endpoint="users_create")
@login_required
def users_create():
    admin_only()
    form = AgentCreateForm()

    if form.validate_on_submit():
        email = form.email.data.strip().lower()

        if User.query.filter_by(email=email).first():
            flash("Email already exists.", "warning")
            return render_template("auth/user_form.html", form=form, mode="create")

        user = User(
            full_name=form.full_name.data.strip(),
            email=email,
            role=form.role.data,
            is_active=form.is_active.data,
        )
        user.set_password(form.password.data)

        db.session.add(user)
        db.session.flush()

        db.session.add(
            ActivityLog(
                user_id=current_user.id,
                action="Created user",
                entity_type="User",
                entity_id=user.id,
                meta={"email": user.email, "role": user.role},
            )
        )

        db.session.commit()
        flash("User created successfully.", "success")
        return redirect(url_for("auth.users_list"))

    return render_template("auth/user_form.html", form=form, mode="create")


@auth_bp.route("/users/<int:user_id>/edit", methods=["GET", "POST"], endpoint="users_edit")
@login_required
def users_edit(user_id):
    admin_only()

    user = User.query.get_or_404(user_id)
    form = AgentEditForm(obj=user)

    if form.validate_on_submit():
        email = form.email.data.strip().lower()

        conflict = User.query.filter(User.email == email, User.id != user.id).first()
        if conflict:
            flash("Email already used by another user.", "warning")
            return render_template("auth/user_form.html", form=form, mode="edit", user=user)

        user.full_name = form.full_name.data.strip()
        user.email = email
        user.role = form.role.data
        user.is_active = form.is_active.data

        if form.password.data:
            user.set_password(form.password.data)

        db.session.add(
            ActivityLog(
                user_id=current_user.id,
                action="Updated user",
                entity_type="User",
                entity_id=user.id,
                meta={"email": user.email, "role": user.role},
            )
        )

        db.session.commit()
        flash("User updated successfully.", "success")
        return redirect(url_for("auth.users_list"))

    return render_template("auth/user_form.html", form=form, mode="edit", user=user)
