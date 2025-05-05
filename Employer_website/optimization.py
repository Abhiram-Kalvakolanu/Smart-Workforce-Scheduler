import psycopg2

def get_db_connection():
    """Helper to connect to Postgres."""
    return psycopg2.connect(
        dbname="postgres",
        user="postgres",
        password="sql123",
        host="localhost",
        port="5432"
    )

def optimize_schedule():
    """
    1. Read from limits table: employee_id, employee_name, min_hours, max_hours
    2. Read from preferences table: mon..sun (0/1)
    3. For each employee, keep or remove days to respect min/max hours.
       One day = 10 hours.
    4. Write final 0/1 schedule to new_schedule.
    """

    DAYS = ["mon","tue","wed","thu","fri","sat","sun"]
    HOURS_PER_DAY = 10

    conn = get_db_connection()
    cur = conn.cursor()

    # 1) Read from limits
    cur.execute("""
        SELECT employee_id, employee_name, designation, min_hours, max_hours
          FROM limits
         ORDER BY employee_id
    """)
    limit_rows = cur.fetchall()
    # store in a dict:  emp_id -> { "name":..., "min":..., "max":... }
    emp_limits = {}
    for row in limit_rows:
        eid, ename, designation, min_h, max_h = row
        emp_limits[eid] = {
            "name": ename,
            "min": min_h,
            "max": max_h
        }

    # 2) Read from preferences table
    #    Each row has: employee_id, employee_name, mon..sun (ints 0/1)
    cur.execute("""
        SELECT employee_id, employee_name, mon, tue, wed, thu, fri, sat, sun
          FROM preferences
         ORDER BY employee_id
    """)
    pref_rows = cur.fetchall()

    # We'll store final optimized schedule in a dictionary,
    # keyed by employee_id => {"name":..., "days": {"mon":0/1, ...}}
    final_schedule = {}

    for row in pref_rows:
        eid = row[0]
        ename = row[1]
        # days_avail is e.g. [1,1,0,1,1,0,1]
        days_avail = list(row[2:])  # mon..sun
        day_map = dict(zip(DAYS, days_avail))

        # If employee is in limits table, get min/max
        if eid not in emp_limits:
            # If somehow not found, skip
            continue

        min_h = emp_limits[eid]["min"]
        max_h = emp_limits[eid]["max"]

        # convert the 0/1 availability into a *tentative* schedule
        #  if day_map[day]==1 => we plan to schedule them that day
        # each scheduled day is 10 hours
        scheduled_days = [d for d in DAYS if day_map[d] == 1]
        total_pref_hours = len(scheduled_days) * HOURS_PER_DAY

        # A) If total preferred < min, you *could* add days not in preference
        #    But let's do a simple approach: we won't forcibly add days
        #    (or you can decide to add them if you truly need to meet min).
        if total_pref_hours < min_h:
            # Not meeting min. We could add days if you want:
            #   for day in DAYS:
            #       if day_map[day]==0 => consider adding
            # But in many real setups, if they didn't prefer it, we don't assign it.
            pass

        # B) If total preferred > max, remove days until within max
        #    We'll remove from "least necessary" day. For example, remove from
        #    the day that has the highest overall coverage or from random day.
        #    For simplicity, remove from the end until we meet max:
        while total_pref_hours > max_h and scheduled_days:
            # pick a day to remove. E.g. remove the last one in the list
            # or you can remove the day with highest coverage, etc.
            day_to_remove = scheduled_days[-1]  # remove last
            scheduled_days.pop()
            total_pref_hours = len(scheduled_days) * HOURS_PER_DAY

        # Now we have a final set of scheduled days for this employee
        # build a dict of 0/1 for each day
        final_days = {d: 1 if d in scheduled_days else 0 for d in DAYS}

        # store in final_schedule
        final_schedule[eid] = {
            "name": ename,
            "days": final_days
        }

    # 3) Write final schedule to new_schedule table
    #    First create new_schedule if not exists
    cur.execute("""
        CREATE TABLE IF NOT EXISTS new_schedule (
            employee_id INT PRIMARY KEY,
            employee_name VARCHAR(100),
            mon VARCHAR(50),
            tue VARCHAR(50),
            wed VARCHAR(50),
            thu VARCHAR(50),
            fri VARCHAR(50),
            sat VARCHAR(50),
            sun VARCHAR(50)
        );
    """)

    # optional: clear out the table each time, or do an upsert
    cur.execute("TRUNCATE TABLE new_schedule;")

    for eid, data in final_schedule.items():
        ename = data["name"]
        day_vals = data["days"]  # {mon:0/1, tue:0/1, ...}
        # insert as strings "0" or "1"
        cur.execute("""
            INSERT INTO new_schedule (employee_id, employee_name, mon, tue, wed, thu, fri, sat, sun)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            eid,
            ename,
            str(day_vals["mon"]),
            str(day_vals["tue"]),
            str(day_vals["wed"]),
            str(day_vals["thu"]),
            str(day_vals["fri"]),
            str(day_vals["sat"]),
            str(day_vals["sun"])
        ))

                # --- Sync to changed_schedule ---
        cur.execute("""
            CREATE TABLE IF NOT EXISTS changed_schedule (
                employee_id INT PRIMARY KEY,
                employee_name VARCHAR(100),
                mon VARCHAR(50),
                tue VARCHAR(50),
                wed VARCHAR(50),
                thu VARCHAR(50),
                fri VARCHAR(50),
                sat VARCHAR(50),
                sun VARCHAR(50)
            );
        """)
        cur.execute("TRUNCATE TABLE changed_schedule;")
        cur.execute("""
            INSERT INTO changed_schedule (employee_id, employee_name, mon, tue, wed, thu, fri, sat, sun)
            SELECT employee_id, employee_name, mon, tue, wed, thu, fri, sat, sun
            FROM new_schedule
        """)

    conn.commit()
    cur.close()
    conn.close()

    print("Optimization complete. 'new_schedule' table updated.")

if __name__ == "__main__":
    optimize_schedule()
