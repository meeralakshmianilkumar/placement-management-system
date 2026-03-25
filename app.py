from flask import Flask, render_template, request, redirect, session, flash
from flask_mysqldb import MySQL

app = Flask(__name__)
app.secret_key = 'secret123'

# -------------------------------
# MySQL Configuration
# -------------------------------
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '1247909'
app.config['MYSQL_DB'] = 'placement_management'

mysql = MySQL(app)


# -------------------------------
# Helper: get student_id from user_id
# -------------------------------
def get_student_id(user_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT student_id FROM STUDENT WHERE user_id = %s", (user_id,))
    row = cur.fetchone()
    return row[0] if row else None


# -------------------------------
# Home Page
# -------------------------------
@app.route('/')
def home():
    return render_template('login.html')


# -------------------------------
# Login
# -------------------------------
@app.route('/login', methods=['POST'])
def login():
    session.pop('_flashes', None)

    username = request.form['username']
    password = request.form['password']

    cur = mysql.connection.cursor()
    cur.execute(
        "SELECT user_id, role FROM USER WHERE username=%s AND password=%s",
        (username, password)
    )
    user = cur.fetchone()

    if user is None:
        flash('Invalid username or password.', 'danger')
        return redirect('/')

    session['user_id'] = user[0]
    session['role'] = user[1]
    flash('Login successful.', 'success')

    if user[1] == 'student':
        return redirect('/student')
    elif user[1] == 'placement':
        return redirect('/officer')

    flash('Invalid role.', 'danger')
    return redirect('/')

   


# -------------------------------
# Register
# -------------------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        name = request.form['name']
        roll_no = request.form['roll_no']
        department = request.form['department']
        cgpa = request.form['cgpa']
        email = request.form['email']

        cur = mysql.connection.cursor()

        cur.execute("""
            INSERT INTO USER(username, password, role)
            VALUES (%s, %s, %s)
        """, (username, password, 'student'))
        mysql.connection.commit()

        cur.execute("SELECT user_id FROM USER WHERE username=%s", (username,))
        user = cur.fetchone()
        user_id = user[0]

        cur.execute("""
            INSERT INTO STUDENT(user_id, name, roll_no, department, cgpa, email, placement_status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (user_id, name, roll_no, department, cgpa, email, 'Not Placed'))
        mysql.connection.commit()

        flash('Registration successful. Please login.', 'success')
        return redirect('/')

    return render_template('register.html')


# -------------------------------
# Student Dashboard
# -------------------------------
@app.route('/student')
def student_dashboard():
    return render_template("student_dashboard.html")


# -------------------------------
# View Drives (ALL + STATUS)
# -------------------------------
@app.route('/drives')
def view_drives():
    user_id = session['user_id']
    cur = mysql.connection.cursor()

    cur.execute("SELECT cgpa FROM STUDENT WHERE user_id=%s", (user_id,))
    student = cur.fetchone()
    student_cgpa = student[0]

    cur.execute("""
        SELECT drive_id, job_role, package, minimum_cgpa, drive_date
        FROM PLACEMENT_DRIVE
    """)
    drives = cur.fetchall()

    updated_drives = []
    for d in drives:
        status = "Eligible" if student_cgpa >= d[3] else "Not Eligible"
        updated_drives.append(d + (status,))

    return render_template("drives.html", drives=updated_drives)


# -------------------------------
# Apply (Eligibility + No Duplicate)
# -------------------------------
@app.route('/apply/<int:drive_id>')
def apply_drive(drive_id):
    user_id = session['user_id']
    student_id = get_student_id(user_id)

    if not student_id:
        flash('Student not found.', 'danger')
        return redirect('/student')

    cur = mysql.connection.cursor()

    cur.execute("SELECT cgpa FROM STUDENT WHERE user_id=%s", (user_id,))
    student = cur.fetchone()
    student_cgpa = student[0]

    cur.execute("""
        SELECT minimum_cgpa
        FROM PLACEMENT_DRIVE
        WHERE drive_id=%s
    """, (drive_id,))
    drive = cur.fetchone()

    if not drive:
        flash('Drive not found.', 'danger')
        return redirect('/drives')

    min_cgpa = drive[0]

    if student_cgpa < min_cgpa:
        flash('You are not eligible for this drive.', 'warning')
        return redirect('/drives')

    cur.execute("""
        SELECT * FROM APPLICATION
        WHERE student_id=%s AND drive_id=%s
    """, (student_id, drive_id))

    if cur.fetchone():
        flash('You have already applied for this drive.', 'info')
        return redirect('/drives')

    cur.execute("""
        INSERT INTO APPLICATION(student_id, drive_id, application_status)
        VALUES (%s, %s, %s)
    """, (student_id, drive_id, 'Applied'))
    mysql.connection.commit()

    flash('Application submitted successfully.', 'success')
    return redirect('/applications')


# -------------------------------
# View Applications
# -------------------------------
@app.route('/applications')
def view_applications():
    user_id = session['user_id']
    student_id = get_student_id(user_id)

    if not student_id:
        flash('Student not found.', 'danger')
        return redirect('/student')

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT c.company_name, d.job_role, a.application_status
        FROM APPLICATION a
        JOIN PLACEMENT_DRIVE d ON a.drive_id = d.drive_id
        JOIN COMPANY c ON d.company_id = c.company_id
        WHERE a.student_id = %s
    """, (student_id,))

    applications = cur.fetchall()

    return render_template("applications.html", applications=applications)


# -------------------------------
# Officer Dashboard
# -------------------------------
@app.route('/officer')
def officer_dashboard():
    cur = mysql.connection.cursor()

    cur.execute("SELECT COUNT(*) FROM STUDENT")
    students = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM COMPANY")
    companies = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM PLACEMENT_DRIVE")
    drives = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM APPLICATION")
    applications = cur.fetchone()[0]

    stats = (students, companies, drives, applications)

    return render_template('officer_dashboard.html', stats=stats)


# -------------------------------
# Add Company
# -------------------------------
@app.route('/add_company', methods=['GET', 'POST'])
def add_company():
    if request.method == 'POST':
        company_name = request.form['company_name']
        industry_type = request.form['industry_type']
        location = request.form['location']
        contact_email = request.form['contact_email']

        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO COMPANY(company_name, industry_type, location, contact_email)
            VALUES (%s, %s, %s, %s)
        """, (company_name, industry_type, location, contact_email))
        mysql.connection.commit()

        flash('Company added successfully.', 'success')
        return redirect('/officer')

    return render_template('add_company.html')


# -------------------------------
# Create Drive
# -------------------------------
@app.route('/create_drive', methods=['GET', 'POST'])
def create_drive():
    if request.method == 'POST':
        company_id = request.form['company_id']
        job_role = request.form['job_role']
        package = request.form['package']
        minimum_cgpa = request.form['minimum_cgpa']
        drive_date = request.form['drive_date']
        required_skill = request.form['required_skill']

        cur = mysql.connection.cursor()

        cur.execute("""
            SELECT officer_id FROM PLACEMENT_OFFICER
            WHERE user_id = %s
        """, (session['user_id'],))
        officer = cur.fetchone()

        if not officer:
            flash('Officer not found.', 'danger')
            return redirect('/officer')

        officer_id = officer[0]

        cur.execute("""
            INSERT INTO PLACEMENT_DRIVE
            (drive_date, job_role, package, minimum_cgpa, company_id, officer_id, required_skill)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (drive_date, job_role, package, minimum_cgpa, company_id, officer_id, required_skill))
        mysql.connection.commit()

        flash('Placement drive created successfully.', 'success')
        return redirect('/view_drives_admin')

    return render_template('create_drive.html')


# -------------------------------
# Admin View Drives
# -------------------------------
@app.route('/view_drives_admin')
def view_drives_admin():
    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT drive_id, job_role, minimum_cgpa
        FROM PLACEMENT_DRIVE
    """)
    drives = cur.fetchall()

    return render_template("admin_drives.html", drives=drives)


# -------------------------------
# Eligible Students
# -------------------------------
@app.route('/eligible/<int:drive_id>')
def view_eligible_students(drive_id):
    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT minimum_cgpa, required_skill
        FROM PLACEMENT_DRIVE
        WHERE drive_id = %s
    """, (drive_id,))
    drive = cur.fetchone()

    if not drive:
        flash('Drive not found.', 'danger')
        return redirect('/view_drives_admin')

    min_cgpa = drive[0]
    required_skill = drive[1]

    if required_skill and required_skill.strip() != "":
        cur.execute("""
            SELECT s.name, s.roll_no, s.department, s.cgpa
            FROM STUDENT s
            JOIN SKILL sk ON s.student_id = sk.student_id
            WHERE s.cgpa >= %s AND sk.skill_name = %s
        """, (min_cgpa, required_skill))
    else:
        cur.execute("""
            SELECT s.name, s.roll_no, s.department, s.cgpa
            FROM STUDENT s
            WHERE s.cgpa >= %s
        """, (min_cgpa,))

    students = cur.fetchall()

    return render_template("eligible_students.html", students=students)


# -------------------------------
# View Applicants
# -------------------------------
@app.route('/view_applicants/<int:drive_id>')
def view_applicants(drive_id):
    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT s.name, d.job_role, a.application_status, a.application_id
        FROM APPLICATION a
        JOIN STUDENT s ON a.student_id = s.student_id
        JOIN PLACEMENT_DRIVE d ON a.drive_id = d.drive_id
        WHERE a.drive_id = %s
    """, (drive_id,))

    applications = cur.fetchall()

    return render_template("view_applicants.html", applications=applications)


# -------------------------------
# Update Status
# -------------------------------
@app.route('/update_status/<int:app_id>/<status>')
def update_status(app_id, status):
    cur = mysql.connection.cursor()

    cur.execute("""
        UPDATE APPLICATION
        SET application_status = %s
        WHERE application_id = %s
    """, (status, app_id))
    mysql.connection.commit()

    flash('Application status updated.', 'success')
    return redirect('/view_drives_admin')


# -------------------------------
# Profile
# -------------------------------
@app.route('/profile', methods=['GET', 'POST'])
def profile():
    user_id = session['user_id']
    cur = mysql.connection.cursor()

    if request.method == 'POST':
        name = request.form['name']
        roll_no = request.form['roll_no']
        department = request.form['department']
        cgpa = request.form['cgpa']
        email = request.form['email']

        cur.execute("""
            UPDATE STUDENT
            SET name=%s, roll_no=%s, department=%s, cgpa=%s, email=%s
            WHERE user_id=%s
        """, (name, roll_no, department, cgpa, email, user_id))
        mysql.connection.commit()

        flash('Profile updated successfully.', 'success')
        return redirect('/profile')

    cur.execute("""
        SELECT name, roll_no, department, cgpa, email
        FROM STUDENT
        WHERE user_id=%s
    """, (user_id,))
    student = cur.fetchone()

    return render_template("profile.html", student=student)


# -------------------------------
# Skills
# -------------------------------
@app.route('/skills', methods=['GET', 'POST'])
def skills():
    user_id = session['user_id']
    student_id = get_student_id(user_id)

    if not student_id:
        flash('Student not found.', 'danger')
        return redirect('/student')

    cur = mysql.connection.cursor()

    if request.method == 'POST':
        skill = request.form['skill']

        cur.execute("""
            SELECT * FROM SKILL
            WHERE student_id = %s AND skill_name = %s
        """, (student_id, skill))
        existing = cur.fetchone()

        if not existing:
            cur.execute("""
                INSERT INTO SKILL(student_id, skill_name)
                VALUES (%s, %s)
            """, (student_id, skill))
            mysql.connection.commit()
            flash('Skill added successfully.', 'success')
        else:
            flash('Skill already exists.', 'info')

        return redirect('/skills')

    cur.execute("""
        SELECT skill_name FROM SKILL
        WHERE student_id = %s
    """, (student_id,))
    skills = cur.fetchall()

    return render_template("skills.html", skills=skills)


# -------------------------------
# Logout
# -------------------------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


# -------------------------------
# Run
# -------------------------------
if __name__ == "__main__":
    app.run(debug=False)