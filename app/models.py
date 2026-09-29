from datetime import datetime, timezone

from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db, login_manager


def utcnow():
    return datetime.now(timezone.utc)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="student")
    last_seen_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_active(self):
        return True

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)

    @property
    def is_admin(self):
        return self.role == "admin"


class Match(db.Model):
    __tablename__ = "matches"

    id = db.Column(db.Integer, primary_key=True)
    host_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    guest_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    status = db.Column(db.String(20), default="created")
    difficulty = db.Column(db.String(20), default="medium")
    host_ready = db.Column(db.Boolean, default=False)
    guest_ready = db.Column(db.Boolean, default=False)
    seed = db.Column(db.Integer, default=0)
    final_state_json = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)
    started_at = db.Column(db.DateTime(timezone=True), nullable=True)
    finished_at = db.Column(db.DateTime(timezone=True), nullable=True)

    host = db.relationship("User", foreign_keys=[host_id])
    guest = db.relationship("User", foreign_keys=[guest_id])
    teams = db.relationship("Team", backref="match", lazy=True)


class Team(db.Model):
    __tablename__ = "teams"

    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey("matches.id"), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    difficulty = db.Column(db.String(20), default="medium")
    configuration_json = db.Column(db.JSON, nullable=False, default=dict)

    player = db.relationship("User", foreign_keys=[player_id])
    players = db.relationship("Player", backref="team", lazy=True)


class Player(db.Model):
    __tablename__ = "players"

    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=False)
    slot = db.Column(db.Integer, nullable=False)  # 1 or 2
    configuration_json = db.Column(db.JSON, nullable=False, default=dict)


class Event(db.Model):
    __tablename__ = "events"

    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey("matches.id"), nullable=False)
    sequence_number = db.Column(db.Integer, nullable=False)
    event_type = db.Column(db.String(50), nullable=False)
    actor_id = db.Column(db.String(120), nullable=True)
    payload_json = db.Column(db.JSON, nullable=False, default=dict)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)

    __table_args__ = (
        db.UniqueConstraint("match_id", "sequence_number", name="uq_event_seq"),
    )


class AppSetting(db.Model):
    __tablename__ = "app_settings"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.JSON, nullable=False, default=dict)
