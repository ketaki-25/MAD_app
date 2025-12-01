from controller.database import db
from controller.model import User, Doctor, Appointment, Department, Patient, Doctor_availability, PatientHistory
from datetime import datetime

sess = db.session

def add_record(record):
    sess.add(record)
    sess.commit()

def delete_record(record):
    sess.delete(record)
    sess.commit()

def get_all_doctors():
    total_doctors = (
        sess.query(Doctor)
        .join(User, Doctor.user_id == User.id)
        .filter(User.role == "doctor", Doctor.blacklisted == False)
        .count()
    )

    return total_doctors

def get_all_patients():
    return User.query.filter_by(role="patient").count()

def get_all_active_appointments():
    return Appointment.query.filter(
    Appointment.status.in_(["Booked", "Completed"])).count()


def get_all_registered_doctor_data():
    return Doctor.query.filter_by(blacklisted=False).all()

def get_registered_patients_data():
    patients = (
        sess.query(Patient, User).join(User, Patient.user_id == User.id)
        .all())
    return patients

def get_future_appointments():
    appointments = (
        sess.query(Appointment, Doctor, Patient, User, Department)
        .join(Doctor, Appointment.doctor_id == Doctor.id)
        .join(Patient, Appointment.patient_id == Patient.id)
        .join(User, Patient.user_id == User.id)
        .outerjoin(Department, Doctor.department_id == Department.id)
        .filter(Doctor.blacklisted == False)
        .filter(Appointment.status.in_(["Booked", "Completed"]))
        .all()
    )
    return appointments

def get_appointment_for_patient_view(patient):
    appointments = (
        db.session.query(Appointment, Doctor, User, Department)
        .join(Doctor, Appointment.doctor_id == Doctor.id)
        .join(User, Doctor.user_id == User.id)
        .outerjoin(Department, Doctor.department_id == Department.id)
        .filter(Appointment.patient_id == patient.id)
        .all()
    )
    return appointments
def get_upcoming_appointments_doc_specific(doc):
    today = datetime.now().strftime("%Y-%m-%d")
    upcoming_appointments = (
        db.session.query(Appointment, Patient, User)
        .join(Patient, Appointment.patient_id == Patient.id)
        .join(User, Patient.user_id == User.id)
        .filter(
            Appointment.doctor_id == doc.id,
            Appointment.date >= today
        )
        .order_by(Appointment.date, Appointment.time)
        .all()
    )
    return upcoming_appointments



def get_doctor(doctor_id):
    return Doctor.query.get(doctor_id)

def get_patient(patient_id):
    return Patient.query.get(patient_id)

def blacklist_doc(doctor_id):
    doctor = get_doctor(doctor_id)
    doctor.blacklisted = not doctor.blacklisted
    sess.commit()

def check_user_exists(username, email):
    existing_user = User.query.filter(
        (User.username == username) | (User.email == email)
    ).first()

    if existing_user:
        return True
    else:
        return False

def get_active_patients(doctor_id):
    active_patients = (
        db.session.query(Patient, User)
        .join(User, Patient.user_id == User.id)
        .join(Appointment, Appointment.patient_id == Patient.id)
        .filter(
            Appointment.doctor_id == doctor_id,
            Appointment.status == "Pending"
        )
        .all()
    )
    return active_patients

def query_user_results(search_input):
    user_results = User.query.filter(
        (User.username.ilike(f"%{search_input}%")) |
        (User.email.ilike(f"%{search_input}%"))
    ).all()
    return user_results

def get_appointment(appointment_id):
    return Appointment.query.get(appointment_id)

def get_history_records(patient_id):
    ahh = PatientHistory.query.filter_by(patient_id=patient_id).order_by(PatientHistory.date.desc()).all()
    return ahh


