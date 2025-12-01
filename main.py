import os
from flask import Flask, render_template,request,redirect,url_for,session,flash
from datetime import timedelta, datetime
from controller.model import *
from controller.sql_scripts import *
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__, template_folder='templates', static_folder='static')

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = os.getenv('SQLALCHEMY_TRACK_MODIFICATIONS')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

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
        role = "patient"

        if check_user_exists(username, email):
            return render_template(
                'login.html',
                error_message="This account already exists. Please log in."
            )

        new_user = User(
            username=username,
            email=email,
            password=password,
            role=role,
            contact=contact,
            age=age,
            gender=gender
        )

        #print(f"new user {new_user}")
        add_record(new_user)

        patient_profile = Patient(user_id=new_user.id)
        add_record(patient_profile)

        return redirect(url_for('login'))

    return render_template('registration.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username, password=password).first()
        if not user:
            return render_template('login.html', 
                                   error_message="Invalid username or password.")
        if user.role == "doctor" and user.doctor_profile and user.doctor_profile.blacklisted:
            return render_template('login.html',
                                   error_message="Access Denied: You are blacklisted.")

        session['username'] = user.username
        session['user_id'] = user.id        
        session['role'] = user.role

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

    return render_template(
        "admin.html",
        total_doctors=get_all_doctors(),
        total_patients=get_all_patients(),
        total_appointments=get_all_active_appointments(),
        registered_doctors=get_all_registered_doctor_data(),
        registered_patients=get_registered_patients_data(),
        upcoming_appointments=get_future_appointments(),
    )

@app.route('/admin/edit_doctor/<int:doctor_id>', methods=['GET', 'POST'])
def edit_doctor(doctor_id):
    doc = get_doctor(doctor_id)
    user = doc.user

    if request.method == 'POST':
        user.username = request.form['username']
        user.contact = request.form['contact']
        doc.specialization = request.form['specialization']

        db.session.commit()
        flash("Doctor updated successfully!", "success")
        return redirect(url_for('admin'))

    return render_template(
        'edit_doctor.html',
        doctor=doc,
        user=user,
        specialization=doc.specialization
    )


@app.route('/admin/delete_doctor/<int:doctor_id>', methods=['POST', 'GET'])
def delete_doctor(doctor_id):

    doc = get_doctor(doctor_id)
    user = doc.user
    delete_record(user)

    flash("Doctor and associated user account deleted successfully!", "success")
    return redirect(url_for('admin'))

@app.route('/admin/blacklist_doctor/<int:doctor_id>', methods=['POST'])
def blacklist_doctor(doctor_id):

    blacklist_doc(doctor_id)
    doc = get_doctor(doctor_id)
    if doc.blacklisted:
        flash(f"Doctor '{doc.user.username}' is now BLACKLISTED!", "danger")
    else:
        flash(f"An error occurred while blacklisting {doc.user.username}")

    return redirect(url_for('admin'))


@app.route('/admin/create_doctor', methods=['GET', 'POST'])
def create_doctor():

    if request.method == 'POST':

        username = request.form['username']
        email = request.form['email']
        contact = request.form.get('contact')
        department_id = request.form.get('department_id')

        existing = User.query.filter_by(email=email).first()
        if existing:
            flash("A doctor already exists with this email", "error")
            return redirect(url_for('create_doctor'))

        department = Department.query.get(department_id)
        if not department:
            flash("Invalid department selected", "error")
            return redirect(url_for('create_doctor'))

        new_user = User(
            username=username,
            email=email,
            password="temp123",
            role="doctor",
            contact=contact
        )
        add_record(new_user)

        new_doctor = Doctor(
            user_id=new_user.id,
            department_id=department_id,
            specialization=department.name
        )
        add_record(new_doctor)

        flash("Doctor created successfully!", "success")
        return redirect(url_for('create_doctor'))

    departments = Department.query.all()
    return render_template('create_doctor.html', departments=departments)


@app.route('/admin/admin_search', methods=['GET', 'POST'])
def admin_search():

    if request.method == "POST":

        search_input = request.form.get("search_input", "").strip()
        user_results = User.query.filter(
            (User.username.ilike(f"%{search_input}%")) |
            (User.email.ilike(f"%{search_input}%"))
        ).all()

        results = []
        for user in user_results:
            if user.role == "doctor" and user.doctor_profile:
                if user.doctor_profile.blacklisted:

                    #print("got inside for and if loop")
                    continue

            results.append(user)

        return render_template(
            "admin_search.html",
            results=results,
            query=search_input
        )

@app.route('/doctor')
def doctor():

    user_id = session.get("user_id")
    doctor = Doctor.query.filter_by(user_id=user_id).first()

    if not doctor:
        flash("Doctor profile not found.", "danger")
        return redirect(url_for("login"))

    upcoming_appointments = get_upcoming_appointments_doc_specific(doctor)

    upcoming_schedule = []
    for appt, patient, user in upcoming_appointments:
        upcoming_schedule.append(
            {
                "patient_name": user.username,
                "patient_id": patient.id,
                "date": appt.date,
                "time": appt.time,
                "patient_history": patient.patient_history,
                "appointment_id": appt.id,
                "status": appt.status
            }
        )

    return render_template(
        "doctor.html",
        today_schedule=upcoming_schedule,
        doctor=doctor.user
    )

@app.route('/doctor_availability', methods=['GET', 'POST'])
def doctor_availability():

    today = datetime.today()
    dates = [(today + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]

    return render_template(
        "doctor_availability.html",
        dates=dates
    )

@app.route("/set_availability", methods=["POST"])
def set_availability():

    if "user_id" not in session or session.get("role") != "doctor":
        return redirect(url_for("login"))

    user_id = session["user_id"]
    doctor = Doctor.query.filter_by(user_id=user_id).first()
    if not doctor:
        return redirect(url_for("login"))
    
    doctor_id = doctor.id
    selected = request.form.getlist("availability")

    Doctor_availability.query.filter_by(doctor_id=doctor_id).delete()

    slot_map = {
        "1": "08:00 - 12:00",
        "2": "12:00 - 16:00",
        "3": "16:00 - 20:00",
        "4": "20:00 - 00:00"
    }
    for slot in selected:
        if "_" in slot:
            date, slot_key = slot.split("_", 1)
            time_slot = slot_map.get(slot_key, slot_key) # Fallback to key if not found
            
            new_entry = Doctor_availability(
                doctor_id=doctor_id,
                date=date,
                time_slot=time_slot,
                is_available=True
            )
            db.session.add(new_entry)

    db.session.commit()

    return redirect(url_for("doctor"))


@app.route('/doctor/complete_appointment/<int:appointment_id>')
def complete_appointment(appointment_id):
    if 'user_id' not in session or session.get('role') != 'doctor':
        return redirect(url_for('login'))

    appt = get_appointment(appointment_id)

    doctor = Doctor.query.filter_by(user_id=session['user_id']).first()
    if appt.doctor_id != doctor.id:
        flash("Unauthorized action.", "error")
        return redirect(url_for('doctor'))

    appt.status = "Completed"
    db.session.commit()
    flash("Appointment marked as completed.", "success")
    return redirect(url_for('doctor'))


@app.route('/doctor/cancel_appointment/<int:appointment_id>')
def cancel_appointment_doctor(appointment_id):
    if 'user_id' not in session or session.get('role') != 'doctor':
        return redirect(url_for('login'))

    appt = get_appointment(appointment_id)
    doctor = Doctor.query.filter_by(user_id=session['user_id']).first()
    if appt.doctor_id != doctor.id:
        flash("Unauthorized action.", "error")
        return redirect(url_for('doctor'))

    appt.status = "Cancelled"
    db.session.commit()
    flash("Appointment cancelled.", "success")
    return redirect(url_for('doctor'))

@app.route('/doctor/view_history/<int:patient_id>')
def view_history(patient_id):
    if 'user_id' not in session or session.get('role') != 'doctor':
        return redirect(url_for('login'))

    patient = get_patient(patient_id)
    patient_user = User.query.get(patient.user_id)
    
    history_records = get_history_records(patient_id)

    enriched_history = []
    for record in history_records:
        doctor_user = User.query.get(record.created_by)
        enriched_history.append({
            "date": record.date.strftime('%Y-%m-%d'),
            "visit_type": record.visit_type,
            "diagnosis": record.diagnosis,
            "doctor_name": doctor_user.username if doctor_user else "Unknown"
        })

    patient_data = {
        "name": patient_user.username,
        "age": patient_user.age,
        "gender": patient_user.gender,
        "contact": patient_user.contact
    }

    return render_template("view_patient_history.html", patient=patient_data, history=enriched_history)


@app.route('/update_history/<int:patient_id>', methods=['GET', 'POST'])
def update_patient_history(patient_id):


    if 'user_id' not in session or session.get('role') != 'doctor':
        return redirect(url_for('login'))

    patient = Patient.query.get_or_404(patient_id)

    if request.method == "POST":

        visit_type = request.form.get("visitType")
        diagnosis = request.form.get("diagnosis")

        new_history = PatientHistory(
            patient_id = patient_id,
            visit_type = visit_type,
            diagnosis = diagnosis,
            created_by = session["user_id"]
        )
        add_record(new_history)
        return redirect(url_for("doctor"))

    patient_user = User.query.get(patient.user_id)
    doctor_user = User.query.get(session['user_id'])
    doctor_profile = Doctor.query.filter_by(user_id=session['user_id']).first()

    if doctor_profile and doctor_profile.department_id:
        department = Department.query.get(doctor_profile.department_id)
    else:
        department = None


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

    user = User.query.filter_by(id=user_id).first()

    if not user:
        return redirect('/login')
    if user.role != "patient":
        return "Access denied. Only patients can access this page.", 403

    patient = Patient.query.filter_by(user_id=user_id).first()

    if not patient:
        return "Patient profile not found. Please create patient profile.", 400

    departments = Department.query.all()

    appointments = get_appointment_for_patient_view(patient)

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

    doctor = Doctor.query.get(doctor_id)
    doctor_user = User.query.get(doctor.user_id)
    availabilities = Doctor_availability.query.filter_by(doctor_id=doctor_id, is_available=True).all()

    if request.method == 'POST':
        date_time = request.form.get('date_time') 
        if not date_time:
            flash("Please select a time slot.", "error")
            return redirect(url_for('book_appointment', doctor_id=doctor_id))

        date, time = date_time.split('_', 1)
        
        patient = Patient.query.filter_by(user_id=session['user_id']).first()


        existing = Appointment.query.filter(
            Appointment.doctor_id == doctor_id,
            Appointment.date == date,
            Appointment.time == time,
            Appointment.status.in_(["Booked", "Pending"])
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
        add_record(new_appt)

        flash("Appointment booked successfully, yayyyy!", "success")
        return redirect(url_for('patient'))

    return render_template('book_appointment.html', doctor=doctor, doctor_user=doctor_user, availabilities=availabilities)


@app.route('/patient/cancel_appointment/<int:appointment_id>')
def cancel_appointment(appointment_id):
    if 'user_id' not in session or session.get('role') != 'patient':
        return redirect(url_for('login'))

    appt = Appointment.query.get_or_404(appointment_id)
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

