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


class Game(db.Model):
    __tablename__ = "games"

    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default="")
    status = db.Column(db.String(20), default="draft")
    current_version_id = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    versions = db.relationship(
        "GameVersion", backref="game", lazy=True, order_by="GameVersion.id"
    )


class GameVersion(db.Model):
    __tablename__ = "game_versions"

    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey("games.id"), nullable=False)
    version = db.Column(db.String(20), nullable=False)
    blueprint_json = db.Column(db.JSON, nullable=False, default=dict)
    blueprint_files = db.Column(db.JSON, nullable=False, default=dict)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)

    __table_args__ = (db.UniqueConstraint("game_id", "version", name="uq_game_version"),)


class Playground(db.Model):
    __tablename__ = "playgrounds"

    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    game_version_id = db.Column(db.Integer, db.ForeignKey("game_versions.id"), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    configuration_json = db.Column(db.JSON, nullable=False, default=dict)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)
    updated_at = db.Column(db.DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    game_version = db.relationship("GameVersion")
    teams = db.relationship("Team", backref="playground", lazy=True)


class Team(db.Model):
    __tablename__ = "teams"

    id = db.Column(db.Integer, primary_key=True)
    playground_id = db.Column(db.Integer, db.ForeignKey("playgrounds.id"), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    configuration_json = db.Column(db.JSON, nullable=False, default=dict)

    agents = db.relationship("AgentConfiguration", backref="team", lazy=True)


class AgentConfiguration(db.Model):
    __tablename__ = "agent_configurations"

    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=False)
    role = db.Column(db.String(50), nullable=False)
    configuration_json = db.Column(db.JSON, nullable=False, default=dict)


class Competition(db.Model):
    __tablename__ = "competitions"

    id = db.Column(db.Integer, primary_key=True)
    game_version_id = db.Column(db.Integer, db.ForeignKey("game_versions.id"), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)
    started_at = db.Column(db.DateTime(timezone=True), nullable=True)
    finished_at = db.Column(db.DateTime(timezone=True), nullable=True)
    status = db.Column(db.String(20), default="created")
    configuration_json = db.Column(db.JSON, nullable=False, default=dict)
    final_state_json = db.Column(db.JSON, nullable=True)

    game_version = db.relationship("GameVersion")
    events = db.relationship("Event", backref="competition", lazy=True)


class CompetitionTeam(db.Model):
    __tablename__ = "competition_teams"

    id = db.Column(db.Integer, primary_key=True)
    competition_id = db.Column(db.Integer, db.ForeignKey("competitions.id"), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)


class Event(db.Model):
    __tablename__ = "events"

    id = db.Column(db.Integer, primary_key=True)
    competition_id = db.Column(db.Integer, db.ForeignKey("competitions.id"), nullable=False)
    sequence_number = db.Column(db.Integer, nullable=False)
    event_type = db.Column(db.String(50), nullable=False)
    actor_id = db.Column(db.String(80), nullable=True)
    payload_json = db.Column(db.JSON, nullable=False, default=dict)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)

    __table_args__ = (
        db.UniqueConstraint("competition_id", "sequence_number", name="uq_event_seq"),
    )


class Action(db.Model):
    __tablename__ = "actions"

    id = db.Column(db.Integer, primary_key=True)
    competition_id = db.Column(db.Integer, db.ForeignKey("competitions.id"), nullable=False)
    turn_number = db.Column(db.Integer, nullable=False)
    team_id = db.Column(db.Integer, nullable=False)
    agent_id = db.Column(db.String(80), nullable=True)
    action_type = db.Column(db.String(50), nullable=False)
    request_json = db.Column(db.JSON, nullable=False, default=dict)
    result_json = db.Column(db.JSON, nullable=False, default=dict)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)


class ResourceUsage(db.Model):
    __tablename__ = "resource_usage"

    id = db.Column(db.Integer, primary_key=True)
    competition_id = db.Column(db.Integer, db.ForeignKey("competitions.id"), nullable=False)
    agent_id = db.Column(db.String(80), nullable=True)
    tokens_input = db.Column(db.Integer, default=0)
    tokens_output = db.Column(db.Integer, default=0)
    model = db.Column(db.String(120), default="")
    duration_ms = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow)


class AppSetting(db.Model):
    __tablename__ = "app_settings"

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.JSON, nullable=False, default=dict)
