from flask import Flask, render_template, request, redirect, flash 
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
# OS module to access environment variables
import os
# Google Generative AI (Gemini API)
import google.generativeai as genai


# Load environment variables
load_dotenv()

# Gemini API key from .env
API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=API_KEY )

# Flask App Initialization
app = Flask(__name__)

# Secret key used for session management and flash messages
app.secret_key = "health_prediction_secret"

# Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///health.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy
db = SQLAlchemy(app)


# Patient Model
class Patient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100))
    dob = db.Column(db.String(20))
    email = db.Column(db.String(100))
    glucose = db.Column(db.Float)
    haemoglobin = db.Column(db.Float)
    cholesterol = db.Column(db.Float)
    remarks = db.Column(db.String(1000))


# Gemini AI Function
def generate_health_remark(glucose, haemoglobin, cholesterol):

     # Load Gemini model
    model = genai.GenerativeModel("gemini-2.5-flash")

    # Prompt sent to AI model
    prompt = f"""
    Analyze the following patient blood test values:

    Glucose: {glucose}
    Haemoglobin: {haemoglobin}
    Cholesterol: {cholesterol}

    Provide a short health assessment in less than 50 words.
    Mention possible health risks if values are abnormal.
    """

    try:
         # Generate AI response
        response = model.generate_content(prompt)
        return response.text

    # Handle API failure gracefully
    except Exception as e:
        return f"AI Prediction Error: {str(e)}"


# HOME PAGE (CREATE + READ)
@app.route('/')
def landing():
    return render_template('home.html')

# CREATE + READ PATIENT DATA
@app.route('/patients', methods=['GET', 'POST'])
def patients():

    # ---------------- POST REQUEST (CREATE) ----------------
    if request.method == 'POST':

        # Get form data
        full_name = request.form['full_name']
        dob = request.form['dob']
        email = request.form['email']

        # ---------------- Email validation ----------------
        import re
        pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'

        if not re.match(pattern, email):
            flash("Invalid Email", "danger")
            return redirect('/patients')

        # ---------------- DOB validation ----------------
        from datetime import datetime

        dob_date = datetime.strptime(dob, "%Y-%m-%d").date()

        if dob_date > datetime.today().date():
            flash("DOB cannot be in future", "danger")
            return redirect('/patients')

        # ---------------- Numeric validation ----------------
        try:
            glucose = float(request.form['glucose'])
            haemoglobin = float(request.form['haemoglobin'])
            cholesterol = float(request.form['cholesterol'])
        except:
            flash("Blood values must be numeric", "danger")
            return redirect('/patients')

        # Generate AI-based health remarks
        remarks = generate_health_remark(glucose, haemoglobin, cholesterol)

        # Create Patient object
        patient = Patient(
            full_name=full_name,
            dob=dob,
            email=email,
            glucose=glucose,
            haemoglobin=haemoglobin,
            cholesterol=cholesterol,
            remarks=remarks
        )

        # Save to database
        db.session.add(patient)
        db.session.commit()

        flash("Patient added successfully ✅", "success")

        return redirect('/patients')

    # ---------------- GET REQUEST (READ) ----------------
    patients = Patient.query.all()
    return render_template('patients.html', patients=patients)


# UPDATE
@app.route('/edit/<int:id>', methods=['POST'])
def edit_patient(id):

    # Fetch patient by ID
    patient = Patient.query.get_or_404(id)

    # Update fields
    patient.full_name = request.form['full_name']
    patient.dob = request.form['dob']
    patient.email = request.form['email']

    patient.glucose = float(request.form['glucose'])
    patient.haemoglobin = float(request.form['haemoglobin'])
    patient.cholesterol = float(request.form['cholesterol'])

    # Regenerate AI remarks after update
    patient.remarks = generate_health_remark(
        patient.glucose,
        patient.haemoglobin,
        patient.cholesterol
    )

    # Commit changes
    db.session.commit()

    flash("Patient updated successfully ✅", "success")

    return redirect('/patients')

# DELETE
@app.route('/delete/<int:id>')
def delete_patient(id):

    # Fetch patient record
    patient = Patient.query.get_or_404(id)

    # Delete from database
    db.session.delete(patient)
    db.session.commit()

    flash("Patient deleted successfully ✅", "success")

    return redirect('/patients')


# MAIN
if __name__ == '__main__':

    # Create database tables if not exist
    with app.app_context():
        db.create_all()

    # Start Flask server
    app.run(debug=True)
