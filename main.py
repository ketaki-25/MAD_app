from flask import Flask, render_template,request,redirect,url_for,session,flash
from controller.database import db
from controller.model import *
from datetime import datetime,date
from sqlalchemy.orm import joinedload

app = Flask(__name__, template_folder='templates', static_folder='static')

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.sqlite3'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = '12345'

@app.route('/')
def base():
    return render_template('base.html')

@app.route('/registration', methods=['GET', 'POST'])
def registration():
    if request.method == 'POST':
        form = request.form

        username = form.get('username')
        email = form.get('user_email')
        password = form.get('password')
        contact = form.get('contact')
        age = form.get('age')
        gender = form.get('gender')

        # Role is fixed as patient (HTML also sends hidden input)
        role = "patient"

        # Check if username or email already exists
        existing_user = User.query.filter(
            (User.username == username) | (User.email == email)
        ).first()

        if existing_user:
            return render_template(
                'login.html',
                error_message="This account already exists. Please log in."
            )

        # Create User entry
        new_user = User(
            username=username,
            email=email,
            password=password,
            role=role,
            contact=contact,
            age=age,
            gender=gender
        )
        db.session.add(new_user)
        db.session.commit()

        # Create Patient Profile
        patient_profile = Patient(user_id=new_user.id)
        db.session.add(patient_profile)
        db.session.commit()

        return redirect(url_for('login'))

    return render_template('registration.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Find user
        user = User.query.filter_by(username=username, password=password).first()

        if not user:
            return render_template('login.html', 
                                   error_message="Invalid username or password.")

        # Blacklist check (only applies to doctor role)
        if user.role == "doctor" and user.doctor_profile and user.doctor_profile.blacklisted:
            return render_template('login.html',
                                   error_message="Access Denied: You are blacklisted.")

        # Store login session
        session['username'] = user.username
        session['user_id'] = user.id        
        session['role'] = user.role

        # Redirect based on role
        if user.role == 'patient':
            return redirect(url_for('patient'))
        elif user.role == 'doctor':
            return redirect(url_for('doctor'))
        elif user.role == 'admin':
            return redirect(url_for('admin'))

    return render_template('login.html')
    

@app.route('/admin')
def admin():
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    # Count all non-blacklisted doctors
    total_doctors = (
        db.session.query(Doctor)
        .join(User, Doctor.user_id == User.id)
        .filter(User.role == "doctor", Doctor.blacklisted == False)
        .count()
    )

    # Count patients
    total_patients = User.query.filter_by(role="patient").count()

    # Count total appointments
    total_appointments = Appointment.query.count()

    # List of all non-blacklisted doctors
    registered_doctors = Doctor.query.filter_by(blacklisted=False).all()

    # List of all patients + their user info
    registered_patients = (
        db.session.query(Patient, User)
        .join(User, Patient.user_id == User.id)
        .all()
    )

    # Upcoming appointments with doctor, patient & user info
    upcoming_appointments = (
        db.session.query(Appointment, Doctor, Patient, User, Department)
        .join(Doctor, Appointment.doctor_id == Doctor.id)
        .join(Patient, Appointment.patient_id == Patient.id)
        .join(User, Patient.user_id == User.id)
        .outerjoin(Department, Doctor.department_id == Department.id)
        .filter(Doctor.blacklisted == False)
        .all()
    )

    return render_template(
        "admin.html",
        total_doctors=total_doctors,
        total_patients=total_patients,
        total_appointments=total_appointments,
        registered_doctors=registered_doctors,
        registered_patients=registered_patients,
        upcoming_appointments=upcoming_appointments
    )

@app.route('/admin/edit_doctor/<int:doctor_id>', methods=['GET', 'POST'])
def edit_doctor(doctor_id):
    doctor = Doctor.query.get(doctor_id)
    user = doctor.user

    if request.method == 'POST':
        user.username = request.form['username']
        user.contact = request.form['contact']
        doctor.specialization = request.form['specialization']

        db.session.commit()
        flash("Doctor updated successfully!", "success")
        return redirect(url_for('admin'))

    return render_template(
        'edit_doctor.html',
        doctor=doctor,
        user=user,
        specialization=doctor.specialization 
    )


@app.route('/admin/delete_doctor/<int:doctor_id>', methods=['POST', 'GET'])
def delete_doctor(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)

    # Get the linked user (correct relationship usage)
    user = doctor.user

    # Delete ONLY the user — doctor will be deleted automatically
    db.session.delete(user)
    db.session.commit()

    flash("Doctor and associated user account deleted successfully!", "success")
    return redirect(url_for('admin'))

@app.route('/admin/blacklist_doctor/<int:doctor_id>', methods=['POST'])
def blacklist_doctor(doctor_id):

    # Only admin can blacklist
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    doctor = Doctor.query.get_or_404(doctor_id)

    # Toggle blacklist state
    doctor.blacklisted = not doctor.blacklisted  
    db.session.commit()

    # Flash message
    if doctor.blacklisted:
        flash(f"Doctor '{doctor.user.username}' is now BLACKLISTED!", "danger")
    else:
        flash(f"Doctor '{doctor.user.username}' is now ACTIVE again.", "success")

    return redirect(url_for('admin'))

@app.route('/admin/create_doctor', methods=['GET', 'POST'])
def create_doctor():

    if session.get("role") != "admin":
        return redirect(url_for("login"))

    if request.method == 'POST':
        
        username = request.form['username']
        email = request.form['email']
        contact = request.form.get('contact')
        department_id = request.form.get('department_id')

        # Check if email already exists
        existing = User.query.filter_by(email=email).first()
        if existing:
            flash("A doctor already exists with this email!", "error")
            return redirect(url_for('create_doctor'))

        # Fetch selected department
        department = Department.query.get(department_id)
        if not department:
            flash("Invalid department selected!", "error")
            return redirect(url_for('create_doctor'))

        # Create user entry
        new_user = User(
            username=username,
            email=email,
            password="temp123",    # Temporary password
            role="doctor",
            contact=contact
        )
        db.session.add(new_user)
        db.session.commit()

        # Create doctor profile entry
        new_doctor = Doctor(
            user_id=new_user.id,
            department_id=department_id,
            specialization=department.name   # ✔ Store department NAME here
        )
        db.session.add(new_doctor)
        db.session.commit()

        flash("Doctor created successfully!", "success")
        return redirect(url_for('create_doctor'))

    # Fetch departments for dropdown
    departments = Department.query.all()

    return render_template('create_doctor.html', departments=departments)


@app.route('/admin/admin_search', methods=['GET', 'POST'])
def admin_search():
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    query = ""
    results = []

    if request.method == "POST":
        query = request.form.get("search_input", "").strip()

        # Search by username or email
        user_results = User.query.filter(
            (User.username.ilike(f"%{query}%")) |
            (User.email.ilike(f"%{query}%"))
        ).all()

        results = []
        for user in user_results:

            # If the user is a doctor and blacklisted → skip
            if user.role == "doctor" and user.doctor_profile:
                if user.doctor_profile.blacklisted:
                    continue

            results.append(user)

    return render_template(
        "admin_search.html",
        results=results,
        query=query
    )

@app.route('/doctor')
def doctor():
    # Ensure doctor is logged in
    if session.get("role") != "doctor":
        return redirect(url_for("login"))

    # Get doctor record
    user_id = session.get("user_id")
    doctor = Doctor.query.filter_by(user_id=user_id).first()

    if not doctor:
        flash("Doctor profile not found.", "danger")
        return redirect(url_for("login"))

    today = datetime.now().strftime("%Y-%m-%d")

    # -------- 1. Today's Appointments --------
    today_appointments = (
        db.session.query(Appointment, Patient, User)
        .join(Patient, Appointment.patient_id == Patient.id)
        .join(User, Patient.user_id == User.id)
        .filter(
            Appointment.doctor_id == doctor.id,
            Appointment.date == today
        )
        .all()
    )

    # Convert raw rows into a clean list for Jinja
    today_schedule = []
    for appt, patient, user in today_appointments:
        today_schedule.append({
            "patient_name": user.username,
            "time": appt.time,
            "patient_history": patient.patient_history,
            "appointment_id": appt.id,
            "status": appt.status
        })

    # -------- 2. Assigned Patients --------
    active_patients = (
        db.session.query(Patient, User)
        .join(User, Patient.user_id == User.id)
        .join(Appointment, Appointment.patient_id == Patient.id)
        .filter(
            Appointment.doctor_id == doctor.id,
            Appointment.status == "Pending"
        )
        .all()
    )

    assigned_patients = []
    for patient, user in active_patients:
        assigned_patients.append({
            "name": user.username,
            "history": patient.patient_history
        })

    # -------- Render the dashboard --------
    return render_template(
        "doctor.html",
        today_schedule=today_schedule,
        assigned_patients=assigned_patients,
        doctor=doctor.user
    )

from datetime import datetime, timedelta

@app.route('/doctor_availability', methods=['GET', 'POST'])
def doctor_availability():
    if 'user_id' not in session or session.get('role') != 'doctor':
        return redirect(url_for('login'))

    today = datetime.today()
    dates = [(today + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]

    return render_template(
        "doctor_availability.html",
        dates=dates
    )


@app.route("/set_availability", methods=["POST"])
def set_availability():
    # Check login & role
    if "user_id" not in session or session.get("role") != "doctor":
        return redirect(url_for("login"))

    # Correct doctor_id
    user_id = session["user_id"]
    doctor = Doctor.query.filter_by(user_id=user_id).first()
    if not doctor:
        return redirect(url_for("login"))
    
    doctor_id = doctor.id

    # Get selected slots
    # Note: Template should use name="availability"
    selected = request.form.getlist("availability")   

    # Delete old availability first
    DoctorAvailability.query.filter_by(doctor_id=doctor_id).delete()

    # Time slot mapping
    slot_map = {
        "1": "08:00 - 12:00",
        "2": "12:00 - 16:00",
        "3": "16:00 - 20:00",
        "4": "20:00 - 00:00"
    }

    # Insert new selections
    for slot in selected:
        if "_" in slot:
            date, slot_key = slot.split("_", 1)
            time_slot = slot_map.get(slot_key, slot_key) # Fallback to key if not found
            
            new_entry = DoctorAvailability(
                doctor_id=doctor_id,
                date=date,
                time_slot=time_slot,
                is_available=True
            )
            db.session.add(new_entry)

    db.session.commit()

    return redirect(url_for("doctor"))

@app.route('/update_history/<int:patient_id>', methods=['GET', 'POST'])
def update_history(patient_id):


    if 'user_id' not in session or session.get('role') != 'doctor':
        return redirect(url_for('login'))


    patient_details = db.session.execute(
        text("""
            SELECT 
                p.patient_id,
                p.patient_name,
                d.doctor_name,
                d.department
            FROM patients p
            JOIN doctors d ON p.doctor_id = d.doctor_id
            WHERE p.patient_id = :pid
        """), {"pid": patient_id}
    ).fetchone()

    if not patient_details:
        return "Patient not found", 404

    # If POST → Save patient history
    if request.method == "POST":

        visit_type = request.form.get("visitType")
        diagnosis = request.form.get("diagnosis")
        prescription = request.form.get("prescription") # Added prescription

        # Only saving visit type + diagnosis
        new_history = PatientHistory(
            patient_id = patient_id,
            visit_type = visit_type,
            diagnosis = diagnosis,
            created_by = session["user_id"]
        )
        db.session.add(new_history)

        # Also mark appointment as completed if linked (logic simplified here, ideally we know which appointment)
        # For now, let's just save history.

        db.session.commit()

        return redirect(url_for("doctor"))  # Back to doctor dashboard

    # If GET → Show page
    # We need to fetch patient object to get name etc.
    patient = Patient.query.get_or_404(patient_id)
    patient_user = User.query.get(patient.user_id)

    # Get current doctor details
    doctor_user = User.query.get(session['user_id'])
    doctor_profile = Doctor.query.filter_by(user_id=session['user_id']).first()
    department = Department.query.get(doctor_profile.department_id) if doctor_profile and doctor_profile.department_id else None

    patient_details = {
        "patient_id": patient.id,
        "patient_name": patient_user.username,
        "doctor_name": doctor_user.username,
        "department": department.name if department else "N/A"
    }

    return render_template("update_patient_history.html", patient_details=patient_details)

@app.route('/patient/dashboard')
def patient():
    user_id = session.get('user_id')

    if not user_id:
        return redirect('/login')

    # Correct field name
    user = User.query.filter_by(id=user_id).first()

    if not user:
        return redirect('/login')

    # Access restriction
    if user.role != "patient":
        return "Access denied. Only patients can access this page.", 403

    # Patient profile lookup
    patient = Patient.query.filter_by(user_id=user_id).first()

    if not patient:
        return "Patient profile not found. Please create patient profile.", 400

    departments = Department.query.all()

    appointments = (
        db.session.query(Appointment, Doctor, User, Department)
        .join(Doctor, Appointment.doctor_id == Doctor.id)
        .join(User, Doctor.user_id == User.id)
        .outerjoin(Department, Doctor.department_id == Department.id)
        .filter(Appointment.patient_id == patient.id)
        .all()
    )

    formatted_appointments = []
    for appt, doc, doc_user, dept in appointments:
        formatted_appointments.append({
            "id": appt.id,
            "doctor_name": doc_user.username,
            "department": dept.name if dept else "N/A",
            "date": appt.date,
            "time": appt.time,
            "status": appt.status
        })

    return render_template(
        "patient.html",
        user=user,
        patient=patient,
        departments=departments,
        appointments=formatted_appointments
    )


@app.route('/patient/view_doctors/<int:department_id>')
def view_doctors(department_id):
    if 'user_id' not in session or session.get('role') != 'patient':
        return redirect(url_for('login'))

    department = Department.query.get_or_404(department_id)
    doctors = (
        db.session.query(Doctor, User)
        .join(User, Doctor.user_id == User.id)
        .filter(Doctor.department_id == department_id, Doctor.blacklisted == False)
        .all()
    )

    return render_template('view_doctors.html', department=department, doctors=doctors)


@app.route('/patient/book_appointment/<int:doctor_id>', methods=['GET', 'POST'])
def book_appointment(doctor_id):
    if 'user_id' not in session or session.get('role') != 'patient':
        return redirect(url_for('login'))

    doctor = Doctor.query.get_or_404(doctor_id)
    doctor_user = User.query.get(doctor.user_id)
    
  
    availabilities = DoctorAvailability.query.filter_by(doctor_id=doctor_id, is_available=True).all()

    if request.method == 'POST':
        date_time = request.form.get('date_time') 
        if not date_time:
            flash("Please select a time slot.", "error")
            return redirect(url_for('book_appointment', doctor_id=doctor_id))

        date, time = date_time.split('_', 1)
        
        patient = Patient.query.filter_by(user_id=session['user_id']).first()

        
        existing = Appointment.query.filter_by(
            doctor_id=doctor_id,
            date=date,
            time=time,
            status="Pending" 
        ).first()

        if existing:
            flash("This slot is already booked. Please choose another.", "error")
            return redirect(url_for('book_appointment', doctor_id=doctor_id))

        new_appt = Appointment(
            patient_id=patient.id,
            doctor_id=doctor_id,
            date=date,
            time=time,
            status="Booked"
        )
        db.session.add(new_appt)
        db.session.commit()

        flash("Appointment booked successfully!", "success")
        return redirect(url_for('patient'))

    return render_template('book_appointment.html', doctor=doctor, doctor_user=doctor_user, availabilities=availabilities)


@app.route('/patient/cancel_appointment/<int:appointment_id>')
def cancel_appointment(appointment_id):
    if 'user_id' not in session or session.get('role') != 'patient':
        return redirect(url_for('login'))

    appt = Appointment.query.get_or_404(appointment_id)
    
    # Verify ownership
    patient = Patient.query.filter_by(user_id=session['user_id']).first()
    if appt.patient_id != patient.id:
        flash("Unauthorized action.", "error")
        return redirect(url_for('patient'))

    appt.status = "Cancelled"
    db.session.commit()
    flash("Appointment cancelled.", "success")
    return redirect(url_for('patient'))


@app.route('/patient/history')
def patient_history():
    if 'user_id' not in session or session.get('role') != 'patient':
        return redirect(url_for('login'))

    patient = Patient.query.filter_by(user_id=session['user_id']).first()
    history = PatientHistory.query.filter_by(patient_id=patient.id).order_by(PatientHistory.date.desc()).all()
    
    # Also fetch past appointments
    past_appointments = (
        db.session.query(Appointment, Doctor, User)
        .join(Doctor, Appointment.doctor_id == Doctor.id)
        .join(User, Doctor.user_id == User.id)
        .filter(Appointment.patient_id == patient.id, Appointment.status == "Completed")
        .all()
    )

    return render_template('patient_history.html', history=history, past_appointments=past_appointments)


@app.route('/patient/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    if 'user_id' not in session or session.get('role') != 'patient':
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])

    if request.method == 'POST':
        user.username = request.form.get('username')
        user.email = request.form.get('email')
        user.password = request.form.get('password')
        user.contact = request.form.get('contact')
        user.age = request.form.get('age')
        user.gender = request.form.get('gender')
        
        db.session.commit()
        flash("Profile updated.", "success")
        return redirect(url_for('patient'))

    return render_template('edit_profile.html', user=user)

@app.route('/logout')     
def logout():
     session.pop('username', None)
     return redirect(url_for('base'))
        

db.init_app(app)

with app.app_context():
    db.create_all()

    admin = User.query.filter_by(role='admin').first()

    if not admin:
        admin = User(
            username="Superuser",
            email="admin@gmail.com",
            password="1234567890",
            role="admin",
            contact="0000000000"
        )
        db.session.add(admin)
        db.session.commit()

    # Seed Departments
    if not Department.query.first():
        depts = [
            Department(name="Cardiology", description="Heart and cardiovascular system"),
            Department(name="Neurology", description="Nervous system"),
            Department(name="Oncology", description="Cancer treatment"),
            Department(name="Orthopedics", description="Bones and muscles"),
            Department(name="General Medicine", description="General health")
        ]
        db.session.add_all(depts)
        db.session.commit()
        print("Departments seeded.")

    print("Database setup complete. Admin user ensured.")

if __name__ == "__main__":
    app.run(debug=True)

