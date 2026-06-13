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
# Helper
# -------------------------------
def get_student_id(user_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT student_id FROM STUDENT WHERE user_id=%s", (user_id,))
    row = cur.fetchone()
    return row[0] if row else None


# -------------------------------
# HOME
# -------------------------------
@app.route('/')
def home():
    return render_template('login.html')


# -------------------------------
# LOGIN PAGES
# -------------------------------
@app.route('/student_login')
def student_login():
    return render_template('student_login.html')

@app.route('/admin_login')
def admin_login():
    return render_template('admin_login.html')


# -------------------------------
# STUDENT LOGIN
# -------------------------------
@app.route('/login_student', methods=['POST'])
def login_student():
    username = request.form['username']
    password = request.form['password']

    cur = mysql.connection.cursor()
    cur.execute(
        "SELECT user_id FROM USER WHERE username=%s AND password=%s AND role='student'",
        (username, password)
    )
    user = cur.fetchone()

    if not user:
        flash('Invalid student login.', 'danger')
        return redirect('/student_login')

    session['user_id'] = user[0]
    session['role'] = 'student'

    return redirect('/student')


# -------------------------------
# ADMIN LOGIN
# -------------------------------
@app.route('/login_admin', methods=['POST'])
def login_admin():

    username = request.form['username']
    password = request.form['password']

    cur = mysql.connection.cursor()
    cur.execute(
        "SELECT user_id FROM USER WHERE username=%s AND password=%s AND role='placement'",
        (username, password)
    )
    user = cur.fetchone()

    if not user:
        flash('Invalid admin login.', 'danger')
        return redirect('/admin_login')

    session['user_id'] = user[0]
    session['role'] = 'placement'

    return redirect('/officer')


@app.route('/steps')
def steps():
    return render_template('steps.html')
# -------------------------------
# REGISTER
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

        cur.execute("INSERT INTO USER(username,password,role) VALUES(%s,%s,%s)",
                    (username, password, 'student'))
        mysql.connection.commit()

        cur.execute("SELECT user_id FROM USER WHERE username=%s", (username,))
        user_id = cur.fetchone()[0]

        cur.execute("""
            INSERT INTO STUDENT(user_id,name,roll_no,department,cgpa,email,placement_status)
            VALUES(%s,%s,%s,%s,%s,%s,%s)
        """, (user_id, name, roll_no, department, cgpa, email, 'Not Placed'))

        mysql.connection.commit()

        flash('Registration successful.', 'success')
        return redirect('/student_login')

    return render_template('register.html')


# -------------------------------
# STUDENT DASHBOARD
# -------------------------------
@app.route('/student')
def student_dashboard():
    if 'user_id' not in session or session.get('role') != 'student':
        return redirect('/')
    return render_template('student_dashboard.html')


# -------------------------------
# DRIVES
# -------------------------------
@app.route('/drives')
def drives():
    if 'user_id' not in session:
        return redirect('/')

    user_id = session['user_id']
    cur = mysql.connection.cursor()

    cur.execute("SELECT cgpa FROM STUDENT WHERE user_id=%s", (user_id,))
    student_cgpa = cur.fetchone()[0]

    cur.execute("SELECT drive_id,job_role,package,minimum_cgpa,drive_date FROM PLACEMENT_DRIVE")
    drives = cur.fetchall()

    updated = []
    for d in drives:
        status = "Eligible" if student_cgpa >= d[3] else "Not Eligible"
        updated.append(d + (status,))

    return render_template('drives.html', drives=updated)


# -------------------------------
# APPLY
# -------------------------------
@app.route('/apply/<int:drive_id>')
def apply(drive_id):
    user_id = session['user_id']
    student_id = get_student_id(user_id)

    cur = mysql.connection.cursor()

    cur.execute("SELECT cgpa FROM STUDENT WHERE user_id=%s", (user_id,))
    student_cgpa = cur.fetchone()[0]

    cur.execute("SELECT minimum_cgpa FROM PLACEMENT_DRIVE WHERE drive_id=%s", (drive_id,))
    min_cgpa = cur.fetchone()[0]

    if student_cgpa < min_cgpa:
        flash('Not eligible.', 'warning')
        return redirect('/drives')

    cur.execute("SELECT * FROM APPLICATION WHERE student_id=%s AND drive_id=%s", (student_id, drive_id))
    if cur.fetchone():
        flash('Already applied.', 'info')
        return redirect('/drives')

    cur.execute("INSERT INTO APPLICATION(student_id,drive_id,application_status) VALUES(%s,%s,%s)",
                (student_id, drive_id, 'Applied'))
    mysql.connection.commit()

    flash('Applied successfully.', 'success')
    return redirect('/applications')


# -------------------------------
# APPLICATIONS
# -------------------------------
@app.route('/applications')
def applications():
    user_id = session['user_id']
    student_id = get_student_id(user_id)

    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT c.company_name,d.job_role,a.application_status
        FROM APPLICATION a
        JOIN PLACEMENT_DRIVE d ON a.drive_id=d.drive_id
        JOIN COMPANY c ON d.company_id=c.company_id
        WHERE a.student_id=%s
    """, (student_id,))

    return render_template('applications.html', applications=cur.fetchall())


# -------------------------------
# PROFILE
# -------------------------------
@app.route('/profile', methods=['GET', 'POST'])
def profile():
    user_id = session['user_id']
    cur = mysql.connection.cursor()

    if request.method == 'POST':
        cur.execute("""
            UPDATE STUDENT
            SET name=%s, roll_no=%s, department=%s, cgpa=%s, email=%s
            WHERE user_id=%s
        """, (
            request.form['name'],
            request.form['roll_no'],
            request.form['department'],
            request.form['cgpa'],
            request.form['email'],
            user_id
        ))
        mysql.connection.commit()
        flash('Profile updated.', 'success')
        return redirect('/profile')

    cur.execute("SELECT name,roll_no,department,cgpa,email FROM STUDENT WHERE user_id=%s", (user_id,))
    student = cur.fetchone()

    return render_template('profile.html', student=student)


# -------------------------------
# SKILLS
# -------------------------------
@app.route('/skills', methods=['GET', 'POST'])
def skills():
    student_id = get_student_id(session['user_id'])
    cur = mysql.connection.cursor()

    if request.method == 'POST':
        skill = request.form['skill']

        cur.execute("SELECT * FROM SKILL WHERE student_id=%s AND skill_name=%s", (student_id, skill))
        if not cur.fetchone():
            cur.execute("INSERT INTO SKILL(student_id,skill_name) VALUES(%s,%s)", (student_id, skill))
            mysql.connection.commit()
            flash('Skill added.', 'success')

    cur.execute("SELECT skill_name FROM SKILL WHERE student_id=%s", (student_id,))
    skills = cur.fetchall()

    return render_template('skills.html', skills=skills)


# -------------------------------
# OFFICER DASHBOARD
# -------------------------------
@app.route('/officer')
def officer():
    if 'user_id' not in session:
        return redirect('/')

    cur = mysql.connection.cursor()

    cur.execute("SELECT COUNT(*) FROM STUDENT")
    s = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM COMPANY")
    c = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM PLACEMENT_DRIVE")
    d = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM APPLICATION")
    a = cur.fetchone()[0]

    cur.execute("SELECT name FROM PLACEMENT_OFFICER WHERE user_id=%s", (session['user_id'],))
    officer = cur.fetchone()
    name = officer[0] if officer else None

    return render_template('officer_dashboard.html',
                           stats=(s, c, d, a),
                           officer_name=name)


# -------------------------------
# COMPANY
# -------------------------------
@app.route('/add_company', methods=['GET', 'POST'])
def add_company():
    if request.method == 'POST':
        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO COMPANY(company_name,industry_type,location,contact_email)
            VALUES(%s,%s,%s,%s)
        """, (
            request.form['company_name'],
            request.form['industry_type'],
            request.form['location'],
            request.form['contact_email']
        ))
        mysql.connection.commit()
        return redirect('/officer')

    return render_template('add_company.html')


@app.route('/view_companies')
def view_companies():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM COMPANY")
    return render_template('view_companies.html', companies=cur.fetchall())


# -------------------------------
# DRIVE
# -------------------------------
@app.route('/create_drive', methods=['GET', 'POST'])
def create_drive():
    if request.method == 'POST':
        cur = mysql.connection.cursor()

        cur.execute("SELECT officer_id FROM PLACEMENT_OFFICER WHERE user_id=%s",
                    (session['user_id'],))
        officer_id = cur.fetchone()[0]

        cur.execute("""
            INSERT INTO PLACEMENT_DRIVE
            (drive_date,job_role,package,minimum_cgpa,company_id,officer_id,required_skill)
            VALUES(%s,%s,%s,%s,%s,%s,%s)
        """, (
            request.form['drive_date'],
            request.form['job_role'],
            request.form['package'],
            request.form['minimum_cgpa'],
            request.form['company_id'],
            officer_id,
            request.form['required_skill']
        ))

        mysql.connection.commit()
        return redirect('/view_drives_admin')

    return render_template('create_drive.html')


@app.route('/view_drives_admin')
def view_drives_admin():
    cur = mysql.connection.cursor()
    cur.execute("SELECT drive_id,job_role,minimum_cgpa FROM PLACEMENT_DRIVE")
    return render_template('admin_drives.html', drives=cur.fetchall())


# -------------------------------
# LOGOUT
# -------------------------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


# -------------------------------
# RUN
# -------------------------------
if __name__ == "__main__":
    app.run(debug=True)