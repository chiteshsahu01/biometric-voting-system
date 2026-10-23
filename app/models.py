from flask_sqlalchemy import SQLAlchemy
from datetime import datetime


db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"

    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum("ADMIN", "VOTER"), nullable=False, default="VOTER")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Admin(db.Model):
    __tablename__ = "admins"

    admin_id = db.Column(
        db.Integer,
        primary_key=True,
        autoincrement=True
    )
    username = db.Column(
        db.String(50),
        unique=True,
        nullable=False
    )
    password_hash = db.Column(
        db.String(255),
        nullable=False
    )
    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

class Voter(db.Model):
    __tablename__ = "voters"

    voter_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), unique=True, nullable=True)
    password_hash = db.Column(db.String(255), nullable=True)

    voter_number = db.Column(db.String(50), unique=True, nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    date_of_birth = db.Column(db.Date)
    gender = db.Column(db.String(20))
    mobile = db.Column(db.String(15))
    address = db.Column(db.String(255))

    status = db.Column(
        db.Enum("PENDING", "VERIFIED", "BLOCKED"),
        default="PENDING"
    )

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    face_verification = db.relationship(
        "FaceVerification",
        back_populates="voter",
        uselist=False
    )

    votes = db.relationship(
        "Vote",
        back_populates="voter"
    )


class Election(db.Model):
    __tablename__ = "elections"

    election_id = db.Column(
        db.Integer,
        primary_key=True,
        autoincrement=True
    )

    election_name = db.Column(
        db.String(150),
        nullable=False
    )

    description = db.Column(db.Text)

    start_date = db.Column(
        db.DateTime,
        nullable=False
    )

    end_date = db.Column(
        db.DateTime,
        nullable=False
    )

    status = db.Column(
        db.Enum("UPCOMING", "ACTIVE", "COMPLETED"),
        default="UPCOMING"
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    candidates = db.relationship(
        "Candidate",
        back_populates="election"
    )

    votes = db.relationship(
        "Vote",
        back_populates="election"
    )


class Candidate(db.Model):
    __tablename__ = "candidates"

    candidate_id = db.Column(
        db.Integer,
        primary_key=True,
        autoincrement=True
    )

    election_id = db.Column(
        db.Integer,
        db.ForeignKey("elections.election_id"),
        nullable=False
    )

    candidate_name = db.Column(
        db.String(100),
        nullable=False
    )

    party_name = db.Column(
        db.String(100)
    )

    symbol = db.Column(
        db.String(255)
    )

    description = db.Column(
        db.Text
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    election = db.relationship(
        "Election",
        back_populates="candidates"
    )

    votes = db.relationship(
        "Vote",
        back_populates="candidate"
    )


class FaceVerification(db.Model):
    __tablename__ = "face_verifications"

    verification_id = db.Column(
        db.Integer,
        primary_key=True,
        autoincrement=True
    )

    voter_id = db.Column(
        db.Integer,
        db.ForeignKey("voters.voter_id"),
        unique=True,
        nullable=False
    )

    verification_status = db.Column(
        db.Enum(
            "NOT_REGISTERED",
            "REGISTERED",
            "VERIFIED",
            "FAILED"
        ),
        default="NOT_REGISTERED"
    )

    verification_method = db.Column(
        db.String(50),
        default="FACE"
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    voter = db.relationship(
        "Voter",
        back_populates="face_verification"
    )


class Vote(db.Model):
    __tablename__ = "votes"

    vote_id = db.Column(
        db.Integer,
        primary_key=True,
        autoincrement=True
    )

    voter_id = db.Column(
        db.Integer,
        db.ForeignKey("voters.voter_id"),
        nullable=False
    )

    election_id = db.Column(
        db.Integer,
        db.ForeignKey("elections.election_id"),
        nullable=False
    )

    candidate_id = db.Column(
        db.Integer,
        db.ForeignKey("candidates.candidate_id"),
        nullable=False
    )

    voted_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    voter = db.relationship(
        "Voter",
        back_populates="votes"
    )

    election = db.relationship(
        "Election",
        back_populates="votes"
    )

    candidate = db.relationship(
        "Candidate",
        back_populates="votes"
    )