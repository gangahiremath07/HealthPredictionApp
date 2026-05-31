from flask import Flask, render_template, request, redirect, flash 
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import os
import google.generativeai as genai


# Load environment variables
load_dotenv()

# Gemini API key from .env
API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=API_KEY )

app = Flask(__name__)

app.secret_key = "health_prediction_secret"

# Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///health.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

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

    model = genai.GenerativeModel("gemini-2.5-flash")

    prompt = f"""
    Analyze the following patient blood test values:

    Glucose: {glucose}
    Haemoglobin: {haemoglobin}
    Cholesterol: {cholesterol}

    Provide a short health assessment in less than 50 words.
    Mention possible health risks if values are abnormal.
    """

    try:
        response = model.generate_content(prompt)
        return response.text

    except Exception as e:
        return f"AI Prediction Error: {str(e)}"


# HOME PAGE (CREATE + READ)
@app.route('/')
def landing():
    return render_template('home.html')


@app.route('/patients', methods=['GET', 'POST'])
def patients():

    if request.method == 'POST':

        full_name = request.form['full_name']
        dob = request.form['dob']
        email = request.form['email']

        import re
        pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'

        if not re.match(pattern, email):
            flash("Invalid Email", "danger")
            return redirect('/patients')

        from datetime import datetime

        dob_date = datetime.strptime(dob, "%Y-%m-%d").date()

        if dob_date > datetime.today().date():
            flash("DOB cannot be in future", "danger")
            return redirect('/patients')

        try:
            glucose = float(request.form['glucose'])
            haemoglobin = float(request.form['haemoglobin'])
            cholesterol = float(request.form['cholesterol'])
        except:
            flash("Blood values must be numeric", "danger")
            return redirect('/patients')

        remarks = generate_health_remark(glucose, haemoglobin, cholesterol)

        patient = Patient(
            full_name=full_name,
            dob=dob,
            email=email,
            glucose=glucose,
            haemoglobin=haemoglobin,
            cholesterol=cholesterol,
            remarks=remarks
        )

        db.session.add(patient)
        db.session.commit()

        flash("Patient added successfully ✅", "success")

        return redirect('/patients')

    patients = Patient.query.all()
    return render_template('patients.html', patients=patients)


# UPDATE
@app.route('/edit/<int:id>', methods=['POST'])
def edit_patient(id):

    patient = Patient.query.get_or_404(id)

    patient.full_name = request.form['full_name']
    patient.dob = request.form['dob']
    patient.email = request.form['email']

    patient.glucose = float(request.form['glucose'])
    patient.haemoglobin = float(request.form['haemoglobin'])
    patient.cholesterol = float(request.form['cholesterol'])

    patient.remarks = generate_health_remark(
        patient.glucose,
        patient.haemoglobin,
        patient.cholesterol
    )

    db.session.commit()

    flash("Patient updated successfully ✅", "success")

    return redirect('/patients')

# DELETE
@app.route('/delete/<int:id>')
def delete_patient(id):

    patient = Patient.query.get_or_404(id)

    db.session.delete(patient)
    db.session.commit()

    flash("Patient deleted successfully ✅", "success")

    return redirect('/patients')


# MAIN
if __name__ == '__main__':

    with app.app_context():
        db.create_all()

    app.run(debug=True)
