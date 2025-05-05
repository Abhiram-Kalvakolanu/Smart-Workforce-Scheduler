from flask import Flask, render_template, request, redirect, jsonify
import psycopg2
from psycopg2 import sql

app = Flask(__name__)

# --------------------------------------------------------
# SHARED DB CONNECTION
# --------------------------------------------------------
def get_db_connection():
    return psycopg2.connect(
        dbname="postgres",
        user="postgres",
        password="sql123",
        host="localhost",
        port="5432"
    )

# --------------------------------------------------------
# ADDED FROM tables.py
# --------------------------------------------------------
def create_dynamic_table(organization, roles):
    """
    Dynamically creates (or recreates) a table named "<organization>_employees"
    with Employee_ID as a VARCHAR(50) PRIMARY KEY, plus columns for each role in 'roles'.
    """
    conn = get_db_connection()
    cur = conn.cursor()

    table_name = f"{organization.lower()}_employees"

    # 1) Drop table if it already exists
    drop_query = sql.SQL("DROP TABLE IF EXISTS {}").format(sql.Identifier(table_name))
    cur.execute(drop_query)

    # Employee_ID stored as string, consistent with your existing code.
    default_columns = [
        ("Employee_ID", "VARCHAR(50) PRIMARY KEY"),
        ("Employee_name", "VARCHAR(100)"),
        ("Designation", "VARCHAR(100)"),
        ("Role", "VARCHAR(100)")
    ]

    # Create columns for each skill role
    dynamic_columns = [(role.replace(' ', '_'), "INT") for role in roles]

    # 2) Create table with default + dynamic columns
    create_query = sql.SQL("CREATE TABLE {} ({})").format(
        sql.Identifier(table_name),
        sql.SQL(", ").join(
            sql.SQL("{} {}").format(sql.Identifier(col), sql.SQL(dtype))
            for col, dtype in default_columns + dynamic_columns
        )
    )

    cur.execute(create_query)
    conn.commit()
    cur.close()
    conn.close()


@app.route('/create_roles_table', methods=['POST'])
def create_roles_table():
    data = request.json
    roles = data.get('roles', [])
    organization = data.get('organization', 'default_org')

    if not roles:
        return jsonify({"message": "No roles provided."}), 400

    try:
        # 1. Recreate the dynamic school_employees table
        create_dynamic_table(organization, roles)

        # 2. Clean up related tables
        conn = get_db_connection()
        cur = conn.cursor()

        # Clear all related tables
        cur.execute("DELETE FROM candidate_credentials;")
        cur.execute("DELETE FROM preferences;")
        cur.execute("DELETE FROM new_schedule;")
        cur.execute("DELETE FROM limits;")
        cur.execute("DELETE FROM changed_schedule;")


        conn.commit()
        cur.close()
        conn.close()

        return jsonify({
            "message": f"Table '{organization.lower()}_employees' created successfully with columns: {', '.join(roles)}. Related tables cleared."
        }), 200

    except Exception as e:
        return jsonify({"message": f"Error creating table: {str(e)}"}), 500

# --------------------------------------------------------
# ORIGINAL app.py CODE
# --------------------------------------------------------
@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/add_employee')
def add_employee():
    """
    Show a form for adding a new employee and display the employees from 'school_employees'
    in ascending numeric order by Employee_ID (even though it's stored as VARCHAR).
    """
    conn = get_db_connection()
    cur = conn.cursor()

    # Fetch dynamic (role skill) columns from school_employees
    cur.execute("""
        SELECT column_name 
        FROM information_schema.columns
        WHERE table_name='school_employees' 
          AND ordinal_position > 4
        ORDER BY ordinal_position
    """)
    roles = [col[0] for col in cur.fetchall()]

    # Fetch all employees, sorted numerically by casting Employee_ID to int
    cur.execute('SELECT * FROM school_employees ORDER BY CAST("Employee_ID" AS int) ASC')
    employees = cur.fetchall()

    # Fetch all column names for display
    cur.execute("""
        SELECT column_name 
        FROM information_schema.columns
        WHERE table_name='school_employees'
        ORDER BY ordinal_position
    """)
    columns = [col[0] for col in cur.fetchall()]

    cur.close()
    conn.close()

    return render_template('add_employee.html', roles=roles, employees=employees, columns=columns)

@app.route('/submit_employee', methods=['POST'])
def submit_employee():
    """
    Inserts a new row into school_employees, generating the next integer Employee_ID
    by taking MAX(CAST(Employee_ID AS int)) + 1, then storing it as a string.
    This ensures strictly sequential IDs (1, 2, 3...) and avoids null constraints.
    """
    data = request.form
    employee_name = data['Employee_name']
    designation = data['Designation']
    role_selected = data['Role']

    conn = get_db_connection()
    cur = conn.cursor()

    # 1) Fetch dynamic columns (skip the first 4: Employee_ID, Employee_name, Designation, Role)
    cur.execute("""
        SELECT column_name 
        FROM information_schema.columns
        WHERE table_name='school_employees'
          AND ordinal_position > 4
        ORDER BY ordinal_position
    """)
    columns = [col[0] for col in cur.fetchall()]

    # 2) Generate the new Employee_ID by casting the existing ones to int, then +1
    cur.execute('SELECT MAX(CAST("Employee_ID" AS int)) FROM school_employees')
    last_id = cur.fetchone()[0]
    if last_id is None:
        last_id = 0
    new_id_int = last_id + 1
    new_id_str = str(new_id_int)  # store as string in DB

    # 3) Prepare the columns & values for INSERT (including Employee_ID)
    insert_columns = ['Employee_ID', 'Employee_name', 'Designation', 'Role'] + columns
    insert_values = [new_id_str, employee_name, designation, role_selected]

    # 4) Append skill ratings
    for col in columns:
        insert_values.append(int(data.get(col, 0)))

    # 5) Insert row
    query = sql.SQL('INSERT INTO school_employees ({}) VALUES ({})').format(
        sql.SQL(', ').join(map(sql.Identifier, insert_columns)),
        sql.SQL(', ').join(sql.Placeholder() * len(insert_values))
    )
    cur.execute(query, insert_values)

    conn.commit()
    cur.close()
    conn.close()

    # Return to the page that shows the new employee in the table
    return redirect('/add_employee')


# JSON endpoint to get existing data for a specific employee
@app.route('/employee_data/<int:emp_id>', methods=['GET'])
def get_employee_data(emp_id):
    """
    Because Employee_ID is actually stored as VARCHAR in the DB,
    we must convert the incoming integer to string before querying.
    So if you hit /employee_data/3, we query 'WHERE "Employee_ID" = "3"'
    """
    conn = get_db_connection()
    cur = conn.cursor()

    emp_id_str = str(emp_id)
    cur.execute('SELECT * FROM school_employees WHERE "Employee_ID" = %s', (emp_id_str,))
    row = cur.fetchone()

    # Get all column names
    cur.execute("""
        SELECT column_name 
        FROM information_schema.columns
        WHERE table_name='school_employees'
        ORDER BY ordinal_position
    """)
    columns = [col[0] for col in cur.fetchall()]

    cur.close()
    conn.close()

    if not row:
        return jsonify({"error": "Employee not found"}), 404

    data = dict(zip(columns, row))
    return jsonify(data), 200

@app.route('/update_employee', methods=['POST'])
def update_employee():
    """
    Updates the skill ratings for a specific employee_id.
    JSON input like:
      {
        "Employee_ID": "3",
        "ratings": { "Server": 8, "Line_Cook": 5 }
      }
    """
    data = request.json
    employee_id = data.get('Employee_ID')
    updated_ratings = data.get('ratings', {})

    if not employee_id:
        return jsonify({"error": "Employee_ID is required"}), 400
    if not updated_ratings:
        return jsonify({"error": "No ratings provided"}), 400

    conn = get_db_connection()
    cur = conn.cursor()

    set_clauses = []
    values = []
    for role, rating in updated_ratings.items():
        set_clauses.append(sql.SQL('{} = %s').format(sql.Identifier(role)))
        values.append(rating)

    # WHERE "Employee_ID" = %s but employee_id is a string in DB, so:
    update_query = (
        sql.SQL('UPDATE school_employees SET ') +
        sql.SQL(', ').join(set_clauses) +
        sql.SQL(' WHERE "Employee_ID" = %s')
    )
    values.append(employee_id)  # the string ID

    cur.execute(update_query, values)
    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"message": "Employee skill ratings updated successfully"}), 200

# --------------------------------------------------------
# CANDIDATE CREDENTIALS
# --------------------------------------------------------
@app.route('/select_candidates')
def select_candidates():
    """
    Show a page with all employees from school_employees,
    plus fields to update Email & Phone in candidate_credentials,
    and display the updated candidate_credentials below.
    """
    conn = get_db_connection()
    cur = conn.cursor()

    # Make sure candidate_credentials exists
    cur.execute("""
        CREATE TABLE IF NOT EXISTS candidate_credentials (
            employee_id INT PRIMARY KEY,
            employee_name VARCHAR(100),
            email VARCHAR(100),
            phone VARCHAR(20)
        );
    """)

    # Since Employee_ID is stored as string, but we want them in numeric order:
    cur.execute('SELECT "Employee_ID", "Employee_name" FROM school_employees ORDER BY CAST("Employee_ID" AS int) ASC')
    employees = cur.fetchall()

    # Grab existing candidate creds
    cur.execute("SELECT employee_id, employee_name, email, phone FROM candidate_credentials ORDER BY employee_id ASC")
    cred_rows = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        'select_candidates.html',
        employees=employees,
        cred_rows=cred_rows
    )

@app.route('/update_candidate', methods=['POST'])
def update_candidate():
    """
    Upserts the candidate's email/phone into candidate_credentials,
    keyed by the int employee_id they typed in.
    """
    employee_id = request.form.get('employee_id')
    employee_name = request.form.get('employee_name')
    email = request.form.get('email', '')
    phone = request.form.get('phone', '')

    if not employee_id or not employee_name:
        return "Missing employee info", 400

    conn = get_db_connection()
    cur = conn.cursor()

    # Make sure candidate_credentials exists
    cur.execute("""
        CREATE TABLE IF NOT EXISTS candidate_credentials (
            employee_id INT PRIMARY KEY,
            employee_name VARCHAR(100),
            email VARCHAR(100),
            phone VARCHAR(20)
        );
    """)

    upsert_query = """
    INSERT INTO candidate_credentials (employee_id, employee_name, email, phone)
    VALUES (%s, %s, %s, %s)
    ON CONFLICT (employee_id)
    DO UPDATE SET
      employee_name = EXCLUDED.employee_name,
      email = EXCLUDED.email,
      phone = EXCLUDED.phone
    """
    cur.execute(upsert_query, (employee_id, employee_name, email, phone))

    conn.commit()
    cur.close()
    conn.close()

    return redirect('/select_candidates')

# --------------------------------------------------------
# FILE UPLOAD
# --------------------------------------------------------
@app.route('/upload_pdf', methods=['POST'])
def upload_pdf():
    if 'pdfFile' not in request.files:
        return "No file part in the request", 400
    file = request.files['pdfFile']
    if file.filename == '':
        return "No selected file", 400

    save_path = "C:/Users/sivad/Documents/Chatbot/RAG/Document.pdf"
    file.save(save_path)

    return redirect('/')  # or return a message if preferred

# --------------------------------------------------------
# LIMITS FEATURE
# --------------------------------------------------------
@app.route('/set_limits')
def set_limits():
    """
    1) Create the limits table ONLY if it doesn't exist.
    2) Insert any missing employees from school_employees (no dropping).
    3) Show the updated table with preserved data.
    """
    conn = get_db_connection()
    cur = conn.cursor()

    # 1) Create if not exists, so we keep existing data
    cur.execute("""
        CREATE TABLE IF NOT EXISTS limits (
            employee_id INTEGER PRIMARY KEY,
            employee_name VARCHAR(100) UNIQUE NOT NULL,
            designation VARCHAR(100),
            min_hours INT DEFAULT 0,
            max_hours INT DEFAULT 0
        );
    """)

    # 2) Insert missing employees (without overwriting existing records)
    cur.execute('SELECT "Employee_ID", "Employee_name", "Designation" FROM school_employees')
    employees = cur.fetchall()

    for emp_id, emp_name, designation in employees:
        cur.execute("""
            INSERT INTO limits (employee_id, employee_name, designation)
            VALUES (%s, %s, %s)
            ON CONFLICT (employee_name) DO NOTHING
        """, (emp_id, emp_name, designation))

    conn.commit()

    # 3) Fetch all data from 'limits', including any custom min/max hours
    cur.execute("""
        SELECT employee_name, designation, min_hours, max_hours, employee_id
        FROM limits
        ORDER BY employee_id
    """)
    limit_rows = cur.fetchall()

    cur.close()
    conn.close()

    return render_template('limits.html', limit_rows=limit_rows)


@app.route('/update_limits', methods=['POST'])
def update_limits():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "No data provided"}), 400

    emp_name = data.get('employee_name')
    min_h = data.get('min_hours')
    max_h = data.get('max_hours')
    emp_id = data.get('employee_id')

    if emp_id is None or str(emp_id).strip() == "":
        return jsonify({"success": False, "error": "Missing employee ID"}), 400

    try:
        emp_id = int(emp_id)  # ensure integer
        min_val = int(min_h)
        max_val = int(max_h)
    except ValueError:
        return jsonify({"success": False, "error": "Min/Max/ID must be integers"}), 400

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute("""
            UPDATE limits
               SET min_hours = %s,
                   max_hours = %s
             WHERE employee_id = %s
        """, (min_val, max_val, emp_id))
        conn.commit()
    except Exception as e:
        conn.rollback()
        cur.close()
        conn.close()
        return jsonify({"success": False, "error": str(e)}), 500

    cur.close()
    conn.close()

    # Return the new values so the frontend can display them instantly
    return jsonify({"success": True, "new_min": min_val, "new_max": max_val}), 200

def sync_new_to_changed_schedule():
    """
    Copies all rows from new_schedule to changed_schedule (overwrites existing data).
    """
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Clear existing records in changed_schedule
        cur.execute("DELETE FROM changed_schedule;")

        # Copy fresh data from new_schedule
        cur.execute("""
            INSERT INTO changed_schedule
            SELECT * FROM new_schedule;
        """)

        conn.commit()
    except Exception as e:
        print("Error syncing new_schedule to changed_schedule:", e)
        conn.rollback()
    finally:
        cur.close()
        conn.close()

# --------------------------------------------------------
# PAY (PLACEHOLDER)
# --------------------------------------------------------
@app.route('/pay')
def pay():
    return render_template('pay.html')

# --------------------------------------------------------
# MAIN ENTRY
# --------------------------------------------------------
if __name__ == '__main__':
    app.run(debug=True, port=5000)
