import traceback
import cv2
from flask import Flask, jsonify, render_template, request, redirect, session, url_for
import secrets
import os
import pymongo
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta, timezone
import random
import numpy as np
import face_recognition
import csv
import string
from werkzeug.security import generate_password_hash, check_password_hash # Import hashing functions
app = Flask(__name__)
# MongoDB Configuration:
try:
    client = pymongo.MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=5000)
    client.server_info()  # Forces connection check
    print("MongoDB Connection Successful!")
except Exception as e:
    print("Error:", e)
db = client["attendance_system"]  # Replace with your database name
students_collection = db["students"]  # Replace with your collection name
attendance_collection = db["attendance"] 
users_collection = db["users"]
reset_tokens_collection = db['reset_tokens']
# Email Configuration (replace with your settings)
EMAIL_SENDER = "riyavarma290404@gmail.com"
EMAIL_PASSWORD = "rkcl dzcw kwjd dwdi" # Consider using environment variables
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
# Helper function to generate a random token
@app.route('/reset_password_invalid')
def reset_password_invalid():
    return render_template('reset_password_invalid.html')
@app.route('/forgot_password_success')
def forgot_password_success():
    return render_template('forgot_password_success.html')
@app.route('/reset_password_success')
def reset_password_success():
    return render_template('reset_password_success.html')

def generate_token(length=32):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for i in range(length))

# Helper function to send an email
def send_email(recipient, subject, body):
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = EMAIL_SENDER
    msg["To"] = recipient

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"Email sending failed: {e}")
        return False

@app.route('/', methods=['GET'])
def root():
    return redirect(url_for('login'))
@app.route('/login', methods=['GET', 'POST'])
def login():
    error_message = None  # Initialize error message

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        user = users_collection.find_one({"email": email})

        if user and check_password_hash(user["password"], password):  # Verify hashed password
            session['email'] = email  # Store session
            return redirect(url_for('index'))  # Redirect on success
        else:
            error_message = "Incorrect email or password."

    return render_template('login.html', error=error_message)  # Pass error to template


@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    success_message = None
    error_message = None
    
    if request.method == 'POST':
        email = request.form.get('email')
        user = users_collection.find_one({"email": email})

        if user:
            token = generate_token()
            expiry = datetime.now(timezone.utc) + timedelta(hours=1)
            
            reset_tokens_collection.update_one(
                {"email": email},
                {"$set": {"token": token, "expiry": expiry}},
                upsert=True
            )
            reset_link = url_for('reset_password', token=token, _external=True)

            email_body = f"Click this link to reset your password: {reset_link}"

            if send_email(email, "Password Reset", email_body):
                success_message = "You have received a password reset link."
            else:
                error_message = "Email sending failed."
        else:
            error_message = "Email not found."

    return render_template("forgot_password.html", success=success_message, error=error_message)
@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    reset_token = reset_tokens_collection.find_one({"token": token})

    if not reset_token or reset_token["expiry"] < datetime.utcnow():
        return "The password reset link is either invalid or expired."
    
    success_message = None
    error_message = None

    if request.method == 'POST':
        new_password = request.form.get('new_password')

        if len(new_password) < 6:
            error_message = "Password must be at least 6 characters long."
        else:
            email = reset_token["email"]
            hashed_password = generate_password_hash(new_password)  # Hash the password
            users_collection.update_one({"email": email}, {"$set": {"password": hashed_password}})
            reset_tokens_collection.delete_one({"token": token})
            success_message = "Your password has been successfully reset."

    return render_template("reset_password.html", token=token, success=success_message, error=error_message)

app.secret_key = secrets.token_urlsafe(32)  
@app.route('/index')
def index():
    if 'email' not in session:  # Check if user is logged in!
        return redirect(url_for('login'))  # Redirect if not logged in
    return render_template('index.html') # Only show index if logged in

@app.route('/logout')
def logout():
    session.pop('email', None)  # Clear the username from the session
    return redirect(url_for('login'))

@app.route('/get_attendance_list', methods=['GET'])
def get_attendance_list():
    class_name = request.args.get('class')

    if not class_name:
        return jsonify({"success": False, "message": "Class is required"})

    try:
        # Fetch students in the selected class
        students = list(students_collection.find(
            {"class": class_name},
            {"_id": 0, "roll_no": 1, "name": 1}
        ))

        # Return the list of students
        return jsonify({"success": True, "attendance": students})

    except Exception as e:
        print(e)
        return jsonify({"success": False, "message": f"Error fetching students: {str(e)}"})

@app.route('/get_students', methods=['GET'])
def get_students():
    try:
        class_order = ["FY", "SY", "TY"]

        print("Fetching students from MongoDB...")

        students = list(students_collection.aggregate([
            {"$addFields": {"class_order_index": {"$indexOfArray": [class_order, "$class"]}}},
            {"$sort": {"class_order_index": 1, "roll_no": 1}},  # Sort by class first, then roll_no
            {"$project": {"_id": 0, "class_order_index": 0}}  # Hide unnecessary fields
        ]))

        print("Students found:", len(students))
        return jsonify({"success": True, "students": students})
    
    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "status": f"Error: {str(e)}"}), 500
@app.route('/delete_student', methods=['POST'])
def delete_student():
    try:
        data = request.get_json()
        roll_no = data.get('roll_no')

        if not roll_no:
            return jsonify({"success": False, "status": "Roll number is required."})

        # Convert roll_no to integer
        try:
            roll_no = int(roll_no)
        except ValueError:
            return jsonify({"success": False, "status": "Invalid roll number format."})

        print(f"Attempting to delete student with roll_no: {roll_no}")  # Debug log

        # Find student in MongoDB
        student = students_collection.find_one({"roll_no": roll_no})

        if not student:
            return jsonify({"success": False, "status": "Student not found in database."})

        student_name = student.get("name", "").strip().lower()  # Get student name safely

        # Delete student record from MongoDB
        result = students_collection.delete_one({"roll_no": roll_no})
        print(f"Delete result: {result.deleted_count} documents deleted.")  # Debug log

        # Attempt to delete student photo
        possible_extensions = [".jpg", ".jpeg", ".png"]
        deleted_photo = False

        for ext in possible_extensions:
            file_path = os.path.join(UPLOAD_FOLDER, f"{roll_no}_{student_name}{ext}")
            absolute_path = os.path.abspath(file_path)
            print(f"Checking file: {absolute_path}")  # Debug print

            if os.path.exists(absolute_path):
                os.remove(absolute_path)
                print(f"Deleted student photo: {absolute_path}")  # Debug print
                deleted_photo = True
                break  # Stop after deleting the first matching file

        if result.deleted_count > 0:
            return jsonify({
                "success": True,
                "status": "Student deleted successfully.",
                "photo_deleted": deleted_photo
            })
        else:
            return jsonify({"success": False, "status": "Student not found."})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "status": str(e)})
@app.route('/get_total_students', methods=['GET'])
def get_total_students():
    try:
        total_students = students_collection.count_documents({})  # Count all students
        return jsonify({"success": True, "total": total_students})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/get-dashboard-data', methods=['GET'])
def get_dashboard_data():
    today = datetime.now().strftime('%Y-%m-%d')

    # Get total students
    total_students = students_collection.count_documents({})

    # Get attendance counts
    present_today = attendance_collection.count_documents({"date": today, "status": "Present"})
    absent_today = attendance_collection.count_documents({"date": today, "status": "Absent"})

    return jsonify({
        "total_students": total_students,
        "present_today": present_today,
        "absent_today": absent_today
    })
# ... (in your server.py or face_attendance.py file)
def get_roll_no_from_name(name):
    try:
        student = students_collection.find_one({"name": name})  # Find by name
        if student:
            return student['roll_no']  # Access roll_no using dictionary syntax
        else:
            print(f"Roll number not found for name: {name}")  # Debugging
            return None
    except Exception as e:
        print(f"Error finding student: {e}")  # Debugging
        return None
def get_name_from_roll_no(roll_no):
    try:
        student = students_collection.find_one({"roll_no": roll_no})  # Find by roll_no
        if student:
            return student['name']  # Access name using dictionary syntax
        else:
            print(f"Name not found for roll_no: {roll_no}")  # Debugging
            return None
    except Exception as e:
        print(f"Error finding student: {e}")  # Debugging
        return None

# Configure file upload settings
from werkzeug.utils import secure_filename
UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Ensure the upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    """Check if the uploaded file has an allowed extension."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
@app.route("/add-student", methods=["POST"])
def add_student():
    try:
        roll_no = request.form.get("rollNo", "").strip()
        student_name = request.form.get("studentName", "").strip()
        student_class = request.form.get("studentClass", "").strip()
        student_file = request.files.get("file")

        # Validation
        if not roll_no or not student_name or not student_class:
            return jsonify({"success": False, "message": "All fields are required."})

        if not roll_no.isdigit():
            return jsonify({"success": False, "message": "Roll number must be numeric."})

        # Check if roll number already exists
        if students_collection.find_one({"roll_no": int(roll_no)}):
            return jsonify({"success": False, "message": "Roll number already exists."})

        # Handle file upload
        if student_file and allowed_file(student_file.filename):
            filename = f"{roll_no}_{secure_filename(student_file.filename)}"  # Unique filename
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            student_file.save(filepath)
        else:
            return jsonify({"success": False, "message": "Invalid file type. Allowed: JPG, JPEG, PNG."})

        # Save student details in MongoDB
        student_data = {
            "roll_no": int(roll_no),  # Convert to integer
            "name": student_name,
            "class": student_class,
            "file_path": filepath,  # Store file path in DB
        }
        students_collection.insert_one(student_data)

        return jsonify({"success": True, "message": "Student added successfully."})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "message": f"Internal Server Error: {str(e)}"}), 500
@app.route("/get-student/<int:roll_no>", methods=["GET"])
def get_student(roll_no):
    try:
        student = students_collection.find_one({"roll_no": roll_no})
        if student:
            return jsonify({
                "success": True,
                "student": {
                    "roll_no": student["roll_no"],
                    "name": student["name"],
                    "class": student["class"],
                    "file_path": student.get("file_path", ""),
                },
            })
        else:
            return jsonify({"success": False, "message": "Student not found."}), 404
    except Exception as e:
        return jsonify({"success": False, "message": f"Internal Server Error: {str(e)}"}), 500
@app.route("/update-student", methods=["POST"])
def update_student():
    try:
        # Get form data
        old_roll_no = request.form.get("oldRollNo")
        new_roll_no = request.form.get("newRollNo")
        student_name = request.form.get("studentName", "").strip()
        student_class = request.form.get("studentClass", "").strip()
        student_file = request.files.get("file")

        # Validate Roll No fields
        if not old_roll_no or not new_roll_no:
            return jsonify({"success": False, "message": "Roll number fields are required."})

        try:
            old_roll_no = int(old_roll_no)  # Convert to integer
            new_roll_no = int(new_roll_no)  # Convert to integer
        except ValueError:
            return jsonify({"success": False, "message": "Invalid roll number format."})

        # Validate other fields
        if not student_name or not student_class:
            return jsonify({"success": False, "message": "All fields are required."})

        # Check if the new roll no already exists (if it's being changed)
        if new_roll_no != old_roll_no:
            existing_student = students_collection.find_one({"roll_no": new_roll_no})
            if existing_student:
                return jsonify({"success": False, "message": "Roll number already exists."})

        # Handle file upload (if a new file is provided)
        filepath = None
        if student_file and allowed_file(student_file.filename):
            filename = f"{new_roll_no}_{secure_filename(student_file.filename)}"
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            student_file.save(filepath)

        # Update student details in MongoDB
        update_data = {
            "roll_no": new_roll_no,  # Update roll no if changed
            "name": student_name,
            "class": student_class,
        }
        if filepath:
            update_data["file_path"] = filepath

        # Update the student record
        students_collection.update_one(
            {"roll_no": old_roll_no},
            {"$set": update_data}
        )

        return jsonify({"success": True, "message": "Student updated successfully."})

    except Exception as e:
        return jsonify({"success": False, "message": f"Internal Server Error: {str(e)}"}), 500
# Path for training images
path = 'uploads'
images = []
classNames = []
myList = os.listdir(path)

# Load training images
for cl in myList:
    curImg = cv2.imread(f'{path}/{cl}')
    images.append(curImg)
    classNames.append(os.path.splitext(cl)[0])

# Encode faces
def findEncodings(images):
    encodeList = []
    for img in images:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        encode = face_recognition.face_encodings(img)[0]
        encodeList.append(encode)
    return encodeList

encodeListKnown = findEncodings(images)
def get_roll_number(name):
    student = students_collection.find_one(
        {"name": {"$regex": f"^{name}$", "$options": "i"}},  # Case-insensitive search
    )
    return student["roll_no"] if student else "Unknown"

def markAttendance(name, recognized=True):
    """
    Marks attendance based on recognition status and only allows updates from 'Absent' to 'Present'.
    """
    name = name.strip().lower()
    rollNo = get_roll_number(name)
    dateString = datetime.now().strftime('%Y-%m-%d')
    csv_filename = "Attendance.csv"

    if rollNo == "Unknown":
        return f"Roll number not found for {name}."

    status = "Present" if recognized else "Absent"

    # Check if attendance is already marked
    existing_record = attendance_collection.find_one({"roll_no": rollNo, "date": dateString})

    if existing_record:
        if existing_record["status"] == "Present" and status == "Absent":
            return f"{name.capitalize()} is already marked Present today."
        elif existing_record["status"] == status:
            return f"{name.capitalize()} is already marked {status} today."
        elif existing_record["status"] == "Absent" and status == "Present":
            # Update only if going from 'Absent' to 'Present'
            attendance_collection.update_one(
                {"roll_no": rollNo, "date": dateString},
                {"$set": {"status": "Present", "percentage": 100.00}}
            )

            # Update CSV
            updated_rows = []
            with open(csv_filename, "r", newline="") as file:
                reader = csv.reader(file)
                for row in reader:
                    if row[0] == str(rollNo) and row[2] == dateString:
                        row[3] = "100.00"
                        row[4] = "Present"
                    updated_rows.append(row)

            with open(csv_filename, "w", newline="") as file:
                writer = csv.writer(file)
                writer.writerows(updated_rows)

    else:
        # Insert new record if it's not in the database
        attendance_collection.insert_one({
            "roll_no": rollNo,
            "name": name.capitalize(),
            "date": dateString,
            "status": status,
            "percentage": 100.00 if status == "Present" else 0.00
        })

        # Append record to CSV
        with open(csv_filename, "a", newline="") as file:
            writer = csv.writer(file)
            writer.writerow([rollNo, name.capitalize(), dateString, "100.00" if status == "Present" else "0.00", status])

    return f"{name.capitalize()} marked as {status}."

def automatically_mark_absentees():
    """
    Automatically marks students as 'Absent' if they are not marked 'Present' for the current date.
    """
    dateString = datetime.now().strftime('%Y-%m-%d')
    csv_filename = "Attendance.csv"

    # Get all students from the database
    all_students = list(students_collection.find())

    # Get students marked 'Present' for today
    present_students = list(attendance_collection.find({
        "date": dateString,
        "status": "Present"
    }))

    present_roll_numbers = [student["roll_no"] for student in present_students]

    for student in all_students:
        roll_no = student["roll_no"]
        name = student["name"]

        if roll_no not in present_roll_numbers:
            # Student not marked 'Present', mark them 'Absent'
            markAttendance(name, False)  # Mark as Absent
            print(f"{name} (Roll No: {roll_no}) automatically marked as Absent.")
            
def run_face_recognition():
    cap = cv2.VideoCapture(0)

    while True:
        success, img = cap.read()
        if not success:
            print("Failed to capture frame")
            break

        imgS = cv2.resize(img, (0, 0), None, 0.25, 0.25)
        imgS = cv2.cvtColor(imgS, cv2.COLOR_BGR2RGB)

        facesCurFrame = face_recognition.face_locations(imgS)
        encodesCurFrame = face_recognition.face_encodings(imgS, facesCurFrame)

        recognized_names = []  # Keep track of recognized names

        for encodeFace, faceLoc in zip(encodesCurFrame, facesCurFrame):
            matches = face_recognition.compare_faces(encodeListKnown, encodeFace)
            faceDis = face_recognition.face_distance(encodeListKnown, encodeFace)
            matchIndex = np.argmin(faceDis)

            if matches[matchIndex]:
                filename = classNames[matchIndex]
                name = "_".join(filename.split("_")[1:]).lower()
                print(f"🔍 Recognized Name: {name}")

                y1, x2, y2, x1 = [i * 4 for i in faceLoc]
                cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.rectangle(img, (x1, y2 - 35), (x2, y2), (0, 255, 0), cv2.FILLED)
                cv2.putText(img, name, (x1 + 6, y2 - 6), cv2.FONT_HERSHEY_COMPLEX, 1, (255, 255, 255), 2)

                recognized_names.append(name)  # Add recognized name to the list
                result = markAttendance(name)
                print(result)

        cv2.imshow('Webcam', img)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

    # Mark absentees after face recognition is done
    for student in students_collection.find():
        if student["name"].lower() not in recognized_names:
            markAttendance(student["name"].lower(), False)  # Mark as Absent
            print(f"{student['name']} automatically marked as Absent.")

    return "Face Recognition Stopped"
# Flask route to trigger attendance marking
@app.route('/mark_attendance', methods=['POST'])
def mark_attendance():
    recognized_name = run_face_recognition()
    return jsonify({"message": recognized_name})

if __name__ == '__main__':
    # Ensure CSV file has a header
    csv_filename = "Attendance.csv"
    if not os.path.exists(csv_filename):
        with open(csv_filename, "w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["Roll No", "Name", "Date", "Percentage", "Status"])
    
    app.run(debug=False)
