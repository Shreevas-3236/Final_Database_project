import os
from flask import Flask, render_template, request, redirect, url_for, session as flask_session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from pymongo import MongoClient
from mongoengine import Document, StringField, EmailField
import stripe

app = Flask(__name__)

# Set the secret key to a random value
app.secret_key = os.urandom(24)

# AWS RDS Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://Meha:Mehagupte280496@educational-website-instance-1.c5wmsyci2aiy.us-east-1.rds.amazonaws.com:5432/education_website_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# MongoDB connection for storing images
mongo_client = MongoClient('mongodb://localhost:27017/')  # Replace with your MongoDB connection string
mongo_db = mongo_client['Final_DB_Project']
collection = mongo_db['images']

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

# Add your Stripe secret key
stripe.api_key = 'your_stripe_secret_key'

# User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    firstname = db.Column(db.String(100), nullable=False)
    lastname = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    contact = db.Column(db.String(15), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)

# Course model
class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    length_of_program = db.Column(db.String(50), nullable=False)
    type_of_program = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    next_intake = db.Column(db.String(50), nullable=False)
    international = db.Column(db.Boolean, default=False)
    course_description = db.Column(db.Text, nullable=False)
    course_fees = db.Column(db.Text, nullable=False)

class Images(Document):
    url = StringField(required=True, max_length=500) 
    meta = {'collection': 'images'}  # Optional: specify collection name

@app.route('/')
def home():
    if 'username' in flask_session:
        return render_template('home.html')
    return redirect(url_for('login'))
 
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and bcrypt.check_password_hash(user.password, password):
            flask_session['username'] = username
            return redirect(url_for('home'))
        return 'Invalid username or password.'
    return render_template('login.html')
 
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        firstname = request.form['firstname']
        lastname = request.form['lastname']
        email = request.form['email']
        contact = request.form['contact']
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if password != confirm_password:
            return 'Passwords do not match.'
        
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        user = User(firstname=firstname, lastname=lastname, email=email, contact=contact, username=username, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')
 
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        username = request.form['username']
        new_password = request.form['new_password']
        confirm_new_password = request.form['confirm_new_password']
 
        if new_password != confirm_new_password:
            return 'Passwords do not match.'
        
        user = User.query.filter_by(username=username).first()
        if user:
            hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
            user.password = hashed_password
            db.session.commit()
            return redirect(url_for('login'))
        return 'Username not found.'
    return render_template('forgot_password.html')
 
@app.route('/logout')
def logout():
    flask_session.pop('username', None)
    return redirect(url_for('login'))
 
@app.route('/profile')
def profile():
    abc = Images.objects(url="username").first()
    print({abc})
    # Render a profile page template or return some response
    return render_template('profile.html')()

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        file = request.files['file']
        if file and file.filename.endswith(('.png', '.jpg', '.jpeg')):
            filename = os.path.join(app.config['UPLOAD_FOLDER'], 'profile.jpg')  # Save with a fixed name
            file.save(filename)
            return redirect(url_for('profile'))  # Redirect to profile page after upload
    return render_template('upload.html')  # Render upload page on GET request
 
@app.route('/contact')
def contact():
    return render_template('contact.html')
 
@app.route('/courses')
def courses():
    if 'username' in flask_session:
        return render_template('courses.html')
    return redirect(url_for('login'))
 
@app.route('/courses/<program_type>')
def get_courses(program_type):
    courses = Course.query.filter_by(type_of_program=program_type).all()
    course_list = [{
        'id': course.id,
        'name': course.name,
        'length_of_program': course.length_of_program,
        'type_of_program': course.type_of_program,
        'location': course.location,
        'next_intake': course.next_intake,
        'international': course.international,
        'course_description': course.course_description,
        'course_fees': course.course_fees
    } for course in courses]
    return jsonify(course_list)
 
@app.route('/course/<int:course_id>')
def course_details(course_id):
    course = Course.query.get_or_404(course_id)
    course_data = {
        'name': course.name,
        'length_of_program': course.length_of_program,
        'type_of_program': course.type_of_program,
        'location': course.location,
        'next_intake': course.next_intake,
        'international': course.international,
        'course_description': course.course_description,
        'course_fees': course.course_fees
    }
    return jsonify(course_data)
 
@app.route('/enroll')
def enroll():
    if 'username' in flask_session:
        course_id = request.args.get('course_id')
        course = Course.query.get_or_404(course_id)
        user = User.query.filter_by(username=flask_session['username']).first()
        return render_template('enroll.html', course_name=course.name, user=user)
    return redirect(url_for('login'))
 
@app.route('/payment', methods=['GET', 'POST'])
def payment():
    if 'username' not in flask_session:
        return redirect(url_for('login'))
 
    if request.method == 'POST':
        course_id = request.form['course_id']
        course = Course.query.get_or_404(course_id)
        
        # Create a payment session with Stripe
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': course.name,
                    },
                    'unit_amount': int(float(course.course_fees.strip('$').replace(',', '')) * 100),
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=url_for('payment_success', course_id=course.id, _external=True),
            cancel_url=url_for('payment_cancel', _external=True),
        )
 
        return redirect(session.url, code=303)
 
    course_id = request.args.get('course_id')
    course = Course.query.get_or_404(course_id)
    
    return render_template('payment.html', course=course)
 
@app.route('/process_payment', methods=['POST'])
def process_payment():
    course_id = request.form['course_id']
    card_number = request.form['card_number']
    card_expiry = request.form['card_expiry']
    card_cvc = request.form['card_cvc']
 
    # Log or process the payment information
    print(f"Processing payment for course ID {course_id}")
    print(f"Card Number: {card_number}")
    print(f"Card Expiry: {card_expiry}")
    print(f"Card CVC: {card_cvc}")
 
    # Simulate successful payment and redirect to confirmation page
    return redirect(url_for('enroll_confirmation', course_id=course_id))
 
@app.route('/enroll/<int:course_id>')
def enroll_confirmation(course_id):
    if 'username' not in flask_session:
        return redirect(url_for('login'))
 
    course = Course.query.get_or_404(course_id)
    user = User.query.filter_by(username=flask_session['username']).first()
    return render_template('enroll.html', course_name=course.name, user=user)
 
@app.route('/payment_cancel')
def payment_cancel():
    return "Payment was canceled. Please try again."
 
@app.route('/forum')
def forum():
    if 'username' in flask_session:
        return render_template('forum.html')
    return redirect(url_for('login'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Create database tables
        # Sample data
        if Course.query.count() == 0:
            sample_courses = [
                Course(name="Full-time Program 1", length_of_program="2 years", type_of_program="Full-time Program", location="Location 1", next_intake="January 2025", international=True, course_description="This is a comprehensive full-time program designed to provide in-depth knowledge and skills in your chosen field. The program spans two years and covers a wide range of topics.", course_fees="$10,000"),
                Course(name="Full-time Program 2", length_of_program="3 years", type_of_program="Full-time Program", location="Location 2", next_intake="March 2025", international=False, course_description="A three-year program offering a balanced mix of theoretical and practical knowledge in the subject area.", course_fees="$20,000"),
                Course(name="International Program 1", length_of_program="1 year", type_of_program="International", location="Location 3", next_intake="June 2025", international=True, course_description="An intensive one-year program designed for international students, providing them with essential skills and knowledge.", course_fees="$22,000"),
                Course(name="Graduate Certificate 1", length_of_program="6 months", type_of_program="Graduate Certificate", location="Location 4", next_intake="September 2025", international=True, course_description="A short, six-month certificate program ideal for graduates seeking to enhance their qualifications.", course_fees="$5,000"),
                Course(name="Diploma Program 1", length_of_program="1.5 years", type_of_program="Diploma", location="Location 5", next_intake="December 2025", international=False, course_description="A comprehensive diploma program providing specialized knowledge and practical skills.", course_fees="$15,000")
            ]
            db.session.bulk_save_objects(sample_courses)
            db.session.commit()

    app.run(debug=True)