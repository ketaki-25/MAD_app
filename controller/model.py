from controller.database import db
from datetime import datetime

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False, unique=True)
    password = db.Column(db.String(120), nullable=False)

    role = db.Column(db.String(50), nullable=False)
    contact = db.Column(db.String(20))
    age = db.Column(db.Integer)
    gender = db.Column(db.String(10))

    doctor_profile = db.relationship(
        "Doctor",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan"
    )

    patient_profile = db.relationship(
        "Patient",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan"
    )


class Department(db.Model):
    __tablename__ = "departments"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text)

    doctors = db.relationship("Doctor", back_populates="department")


class Patient(db.Model):
    __tablename__ = "patients"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True
    )

    patient_history = db.Column(db.Text)
    user = db.relationship("User", back_populates="patient_profile")

    appointments = db.relationship(
        "Appointment",
        back_populates="patient",
        cascade="all, delete-orphan",
        lazy=True
    )

    history_records = db.relationship(
        "PatientHistory",
        back_populates="patient",
        cascade="all, delete-orphan",
        lazy=True
    )


class Doctor(db.Model):
    __tablename__ = "doctors"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True
    )

    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"), nullable=True)
    specialization = db.Column(db.String(120))
    blacklisted = db.Column(db.Boolean, default=False)
    user = db.relationship("User", back_populates="doctor_profile")
    department = db.relationship("Department", back_populates="doctors")

    appointments = db.relationship(
        "Appointment",
        back_populates="doctor",
        cascade="all, delete-orphan",
        lazy=True
    )


class Appointment(db.Model):
    __tablename__ = "appointments"

    id = db.Column(db.Integer, primary_key=True)

    patient_id = db.Column(
        db.Integer,
        db.ForeignKey("patients.id", ondelete="SET NULL"),
        nullable=True
    )

    doctor_id = db.Column(
        db.Integer,
        db.ForeignKey("doctors.id", ondelete="SET NULL"),
        nullable=True
    )

    date = db.Column(db.String(50))
    time = db.Column(db.String(50))

    status = db.Column(db.String(50), default="Pending")

    diagnosis = db.Column(db.Text)

    patient = db.relationship("Patient", back_populates="appointments")
    doctor = db.relationship("Doctor", back_populates="appointments")

class Doctor_availability(db.Model):
    __tablename__ = "doctor_availability"

    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey("doctors.id"), nullable=False)

    date = db.Column(db.String(50), nullable=False)
    time_slot = db.Column(db.String(50), nullable=False)
    is_available = db.Column(db.Boolean, default=False)

    doctor = db.relationship("Doctor", backref="availability")

class PatientHistory(db.Model):
    __tablename__ = "patient_history"

    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patients.id"), nullable=False)
    visit_type = db.Column(db.String(100))
    diagnosis = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    date = db.Column(db.DateTime, default=datetime.utcnow())

    patient = db.relationship("Patient", back_populates="history_records")

