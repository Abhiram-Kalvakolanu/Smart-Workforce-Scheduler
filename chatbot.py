from flask import Flask, request, jsonify, render_template

from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # <-- Enables cross-origin requests from React


import os
import re  # <-- Make sure we explicitly import re if we use regex
import psycopg2

# Gemini LLM imports
from google import genai
from google.genai import types

# ---------------------------
# RAG CONSTANTS & HELPER FUNCTIONS (NEW)
# ---------------------------

# 1. Path to your reference document
DOC_PATH = "C:/Users/sivad/Documents/Chatbot/paradise.pdf"

# Optional: put your RAG model key here if different from your main chat keys
RAG_API_KEY = "*********************"

import fitz  # <-- Add this at the top of your file

def load_document(doc_path):
    """
    Extract text from a PDF file using PyMuPDF (fitz).
    """
    if not os.path.exists(doc_path):
        return ""

    try:
        doc = fitz.open(doc_path)
        full_text = ""
        for page in doc:
            full_text += page.get_text()
        doc.close()
        return full_text
    except Exception as e:
        print("[PDF Read Error]", str(e))
        return ""


def rag_qa(user_query):
    """
    Naive RAG approach:
    1) Load the entire doc text as 'context'.
    2) Build a prompt that includes the doc plus user query.
    3) Call Gemini to see if it can answer from that context.
    4) If the response is mostly useless or empty, return None to fallback.
    """
    context_text = load_document(DOC_PATH)
    if not context_text.strip():
        # No doc or the doc is empty, so we can't do RAG
        return None
    print("Extracted RAG content:\n", context_text[:1000])  # Just print first 1000 chars

    # You may use the same or different API key you use for LLM calls
    client = genai.Client(api_key=RAG_API_KEY)

    prompt = (
        "You are a helpful AI assistant with the following reference text:\n"
        f"---\n{context_text}\n---\n\n"
        "If the user's question can be answered using the above reference, "
        "provide the best possible answer. Otherwise, respond with 'No relevant info found'.\n\n"
        f"User's question: {user_query}\nAnswer:"
    )

    try:
        contents = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=prompt)]
            )
        ]

        response_text = ""
        for chunk in client.models.generate_content_stream(
            model="gemini-2.0-flash-lite",
            contents=contents,
            config=types.GenerateContentConfig(response_mime_type="text/plain")
        ):
            response_text += chunk.text

        answer = response_text.strip()
        
        # If model says "No relevant info found" or is too short, return None so fallback
        if "no relevant info" in answer.lower() or len(answer) < 10:
            return None
        return answer
    
    except Exception as e:
        print("[RAG Error]", str(e))
        return None


# ---------------------------
# Gemini-powered day parser
# ---------------------------
def parse_day_from_gemini(user_input):
    client = genai.Client(api_key="AIzaSyDrZvIV7zOOujGWEwuIwQciwLyXeiNEaNk")
    prompt = (
        f"The user said:\n\"{user_input}\"\n\n"
        "Which day of the week are they referring to for a leave? "
        "Just return the full name of the weekday (e.g., Monday, Tuesday). If not found, respond with None."
    )

    try:
        contents = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=prompt)]
            )
        ]

        response_text = ""
        for chunk in client.models.generate_content_stream(
            model="gemini-2.0-flash-lite",
            contents=contents,
            config=types.GenerateContentConfig(response_mime_type="text/plain")
        ):
            response_text += chunk.text

        response_text = response_text.strip().lower()
        day_map = {
            "monday": "mon", "tuesday": "tue", "wednesday": "wed",
            "thursday": "thu", "friday": "fri", "saturday": "sat", "sunday": "sun"
        }

        for full_day, short_day in day_map.items():
            if full_day in response_text:
                return short_day

        return None
    except Exception as e:
        print("[Gemini Error]", str(e))
        return None


def get_general_response(user_input):
    """
    Uses Gemini to generate a general response using a custom assistant persona.
    """
    try:
        client = genai.Client(api_key="AIzaSyDrZvIV7zOOujGWEwuIwQciwLyXeiNEaNk")

        system_prompt = (
            "You are a helpful, polite, and smart assistant for a restaurant called Paradise Restaurant.\n"
            "You are not a generic AI model. You are the official chatbot assistant for Paradise Restaurant.\n"
            "You help employees with:\n"
            "- Approving leave requests\n"
            "- Handling shift swap requests\n"
            "- Answering general queries\n"
            "- Providing technical support\n\n"
            "If someone asks who you are, say: 'I'm a chatbot assisting on behalf of Paradise Restaurant.'\n"
            "If someone asks what you can do, reply with: 'I can approve leave requests, help with shift swaps, answer general questions, and provide technical support.'\n"
            "Always sound confident and supportive. If someone asks if you can approve leave or swap shifts, say yes and guide them.\n"
            "Avoid mentioning that you're a language model, AI, or developed by Google.\n"
        )

        full_prompt = system_prompt + "\n\nUser: " + user_input

        contents = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=full_prompt)]
            )
        ]

        response_text = ""
        for chunk in client.models.generate_content_stream(
            model="gemini-2.5-pro-exp-03-25",
            contents=contents,
            config=types.GenerateContentConfig(response_mime_type="text/plain")
        ):
            response_text += chunk.text

        return response_text.strip()

    except Exception as e:
        print("[Chatbot Error]", str(e))
        return "Sorry, I'm having trouble answering that right now."


def check_schedule_query(user_text, default_employee="Maria Gonzalez"):
    try:
        client = genai.Client(api_key="AIzaSyDrZvIV7zOOujGWEwuIwQciwLyXeiNEaNk")

        prompt = (
            f"You are a schedule analyzer for Paradise Restaurant.\n"
            f"From the user input, extract:\n"
            f"1. employee name (if mentioned, else assume default '{default_employee}')\n"
            f"2. specific day of the week (e.g., Monday) if asked\n"
            f"Only respond with two values separated by a line break like:\n"
            f"{default_employee}\nWednesday"
        )

        full_prompt = prompt + "\n\nUser input:\n" + user_text

        contents = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=full_prompt)]
            )
        ]

        response_text = ""
        for chunk in client.models.generate_content_stream(
            model="gemini-2.0-flash",
            contents=contents,
            config=types.GenerateContentConfig(response_mime_type="text/plain")
        ):
            response_text += chunk.text

        lines = response_text.strip().split("\n")
        employee = lines[0].strip()
        weekday = lines[1].strip().lower()[:3] if len(lines) > 1 else None

        conn = psycopg2.connect(
            dbname="postgres",
            user="postgres",
            password="sql123",
            host="localhost",
            port="5432"
        )
        cursor = conn.cursor()

        if employee and not weekday:
            cursor.execute("""
                SELECT mon, tue, wed, thu, fri, sat, sun
                FROM changed_schedule
                WHERE employee_name = %s
            """, (employee,))
            row = cursor.fetchone()
            conn.close()

            if not row:
                return f"I couldn't find any schedule for {employee}."

            day_map = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

            # Determine if it's a negative query
            negative_keywords = ['no shift', "don’t", "don't", 'off', 'free', 'leave', 'not working', 'doesn’t', 'doesnt']
            is_asking_for_leaves = any(neg in user_text.lower() for neg in negative_keywords)

            if is_asking_for_leaves:
                leave_days = [day_map[i] for i, val in enumerate(row) if val == '0']
                if employee == default_employee:
                    return "You have leave (no shifts) on: " + ", ".join(leave_days) + "." if leave_days else "You have no leave days this week."
                else:
                    return f"{employee} has leave (no shifts) on: " + ", ".join(leave_days) + "." if leave_days else f"{employee} has no leave days this week."
            else:
                working_days = [day_map[i] for i, val in enumerate(row) if val == '1']
                if employee == default_employee:
                    return "You have shifts on: " + ", ".join(working_days) + "." if working_days else "You have no shifts this week."
                else:
                    return f"{employee} has shifts on: " + ", ".join(working_days) + "." if working_days else f"{employee} has no shifts this week."

        elif employee and weekday:
            cursor.execute(f"""
                SELECT {weekday}
                FROM changed_schedule
                WHERE employee_name = %s
            """, (employee,))
            row = cursor.fetchone()
            conn.close()

            if not row:
                return f"I couldn't find any schedule for {employee}."

            status = "has a shift" if row[0] == '1' else "does not have a shift"
            if employee == default_employee:
                status = "You have a shift" if row[0] == '1' else "You don't have a shift"
                return f"{status} on {weekday.capitalize()}."
            else:
                return f"{employee} {status} on {weekday.capitalize()}."

        return "I couldn't understand the schedule query properly."

    except Exception as e:
        print("[Schedule Check Error]", str(e))
        return "Sorry, I couldn't retrieve the schedule right now."


def process_leave_request(employee_name, leave_day):
    conn = psycopg2.connect(
        dbname="postgres",
        user="postgres",
        password="sql123",
        host="localhost",
        port="5432"
    )
    cursor = conn.cursor()

    leave_day = leave_day.strip().lower()
    cursor.execute(f"""
        SELECT {leave_day}
        FROM changed_schedule
        WHERE employee_name = %s
    """, (employee_name,))
    shift_check = cursor.fetchone()

    if not shift_check:
        conn.close()
        return f"Error: Employee '{employee_name}' not found in changed_schedule."

    requestor_shift_status = shift_check[0]
    if requestor_shift_status == '0':
        conn.close()
        return f"You don't have a shift on {leave_day.capitalize()}."

    cursor.execute("""
        SELECT "Role", "Employee_ID"
        FROM school_employees
        WHERE "Employee_name" = %s
    """, (employee_name,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        return f"Error: Employee '{employee_name}' not found in school_employees."

    requestor_role, requestor_id = row

    query_free = f"""
        SELECT e."Employee_ID", e."Employee_name", e."{requestor_role}" AS skill
        FROM school_employees e
        JOIN changed_schedule s ON e."Employee_ID" = CAST(s.employee_id AS VARCHAR)
        WHERE s.{leave_day} = '0'
          AND e."Employee_ID" <> %s
    """
    cursor.execute(query_free, (requestor_id,))
    free_employees = cursor.fetchall()

    if not free_employees:
        conn.close()
        return f"No employees are free on {leave_day.capitalize()} to replace {employee_name}."

    free_employees.sort(key=lambda x: x[2], reverse=True)
    best_replacement_id, best_replacement_name, _ = free_employees[0]

    update_requestor = f"""
        UPDATE changed_schedule
        SET {leave_day} = '0'
        WHERE employee_name = %s
    """
    cursor.execute(update_requestor, (employee_name,))

    update_replacement = f"""
        UPDATE changed_schedule
        SET {leave_day} = '1'
        WHERE employee_id = %s
    """
    cursor.execute(update_replacement, (int(best_replacement_id),))

    conn.commit()
    cursor.close()
    conn.close()

    return (f"{best_replacement_name} will replace you as {requestor_role} "
            f"on {leave_day.capitalize()}.")


def process_swap_request(employee_name, from_day, to_day):
    """
    Handle a swap request where employee_name wants to move their shift
    from 'from_day' to 'to_day'.
    """

    conn = psycopg2.connect(
        dbname="postgres",
        user="postgres",
        password="sql123",
        host="localhost",
        port="5432"
    )
    cursor = conn.cursor()

    # ------------- STEP 1: Validate the request
    cursor.execute(f"""
        SELECT {from_day}, {to_day}
        FROM changed_schedule
        WHERE employee_name = %s
    """, (employee_name,))
    current_shifts = cursor.fetchone()

    if not current_shifts:
        conn.close()
        return f"Error: Employee '{employee_name}' not found in changed_schedule."

    has_shift_from = (current_shifts[0] == '1')
    has_shift_to = (current_shifts[1] == '1')

    if not has_shift_from:
        conn.close()
        return f"You do not have a shift on {from_day.capitalize()} to swap from."

    if has_shift_to:
        conn.close()
        return f"You already have a shift on {to_day.capitalize()} — no need to swap."

    # ------------- STEP 2: Find a replacement for FROM day
    cursor.execute("""
        SELECT "Role", "Employee_ID"
        FROM school_employees
        WHERE "Employee_name" = %s
    """, (employee_name,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return f"Error: Employee '{employee_name}' not found in school_employees."
    requestor_role, requestor_id = row

    cursor.execute(f'''
        SELECT e."Employee_ID", e."Employee_name", e."{requestor_role}" AS skill
        FROM school_employees e
        JOIN changed_schedule s ON e."Employee_ID" = CAST(s.employee_id AS VARCHAR)
        WHERE s.{from_day} = '0'
          AND e."Employee_ID" <> %s
        ORDER BY skill DESC
    ''', (requestor_id,))
    free_candidates = cursor.fetchall()
    if not free_candidates:
        conn.close()
        return f"No one is free on {from_day.capitalize()} to replace you."

    best_replacement_id, best_replacement_name, _ = free_candidates[0]

    # ------------- STEP 3: Find the person to give up TO day
    cursor.execute(f'''
        SELECT e."Employee_ID", e."Employee_name", e."{requestor_role}" AS skill
        FROM school_employees e
        JOIN changed_schedule s ON e."Employee_ID" = CAST(s.employee_id AS VARCHAR)
        WHERE s.{to_day} = '1'
          AND e."Employee_ID" <> %s
        ORDER BY skill ASC
    ''', (requestor_id,))
    to_day_candidates = cursor.fetchall()
    if not to_day_candidates:
        conn.close()
        return (f"No one currently works on {to_day.capitalize()} for your role. "
                "So there is no shift to 'take over' there.")

    least_skilled_id, least_skilled_name, _ = to_day_candidates[0]

    # ------------- STEP 4: Update the schedule table
    cursor.execute(f'''
        UPDATE changed_schedule
        SET {from_day} = '0'
        WHERE employee_name = %s
    ''', (employee_name,))

    cursor.execute(f'''
        UPDATE changed_schedule
        SET {from_day} = '1'
        WHERE employee_id = %s
    ''', (best_replacement_id,))

    cursor.execute(f'''
        UPDATE changed_schedule
        SET {to_day} = '0'
        WHERE employee_id = %s
    ''', (least_skilled_id,))

    cursor.execute(f'''
        UPDATE changed_schedule
        SET {to_day} = '1'
        WHERE employee_name = %s
    ''', (employee_name,))

    conn.commit()
    cursor.close()
    conn.close()

    # ------------- STEP 5: Return a friendly confirmation
    return (
        f"Your shift on {from_day.capitalize()} will be taken by {best_replacement_name}, "
        f"and you will take {least_skilled_name}'s shift on {to_day.capitalize()}."
    )


# ----------------------------------------------------
# <<< NEW FOR PREFERENCES >>>  (1) Multiple-day parser
# ----------------------------------------------------
def parse_multiple_days(user_text):
    """
    Look for all days (Monday, Tuesday, etc.) in the user text.
    Returns a list of short codes, e.g. ['mon','tue','thu'].
    """
    day_map = {
        "monday": "mon", "tuesday": "tue", "wednesday": "wed",
        "thursday": "thu", "friday": "fri", "saturday": "sat", "sunday": "sun"
    }
    user_text = user_text.lower()
    found_days = []
    for full_day, short_day in day_map.items():
        if full_day in user_text:
            found_days.append(short_day)
    # remove duplicates if any
    return list(set(found_days))


# ----------------------------------------------------
# <<< NEW FOR PREFERENCES >>>  (2) Update table
# ----------------------------------------------------
def update_preferences(employee_name, days_list):
    """
    Sets all days=0 for that employee in 'preferences' table,
    then sets the specified days=1.
    """
    conn = psycopg2.connect(
        dbname="postgres",
        user="postgres",
        password="sql123",
        host="localhost",
        port="5432"
    )
    cursor = conn.cursor()

    # First set all days to 0
    all_days = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
    set_zero_clause = ", ".join([f"{d} = 0" for d in all_days])
    cursor.execute(f"""
        UPDATE preferences
        SET {set_zero_clause}
        WHERE employee_name = %s
    """, (employee_name,))

    # Now set the user-specified days to 1
    for d in days_list:
        cursor.execute(f"""
            UPDATE preferences
            SET {d} = 1
            WHERE employee_name = %s
        """, (employee_name,))

    conn.commit()
    cursor.close()
    conn.close()
    return "Preferences updated successfully."


# ---------------------------
# Flask routes
# ---------------------------
@app.route('/')
def home():
    return render_template('chatbot.html')


@app.route('/process_leave', methods=['POST'])
def handle_leave():
    try:
        data = request.get_json() or {}
        user_text = data.get("user_prompt", "")
        day = data.get("day", "").strip().lower()
        employee_name = data.get("employee_name", "Maria Gonzalez").strip()

        # Step 1: Attempt day parse
        if not day:
            parsed_day = parse_day_from_gemini(user_text)
            if parsed_day:
                day = parsed_day

        # Step 2: Check for intent
        lower_text = user_text.lower()

        leave_keywords = [
            "need leave", "take leave", "apply leave", "request leave",
            "off", "day off", "leave on", "i want leave", "can i take leave",
            "apply for leave", "want a leave", "leave request", "give me leave"
        ]
        schedule_keywords = [
            "schedule", "shift", "working days", "work on", "do i work",
            "which days", "what days", "do i have shift", "when do i work",
            "do i have a shift", "am i working", "working on", "work friday", "shift friday"
        ]
        swap_keywords = [
            "swap shift", "shift swap", "exchange shift", "switch shift", "swap from"
        ]

        # <<< NEW FOR PREFERENCES >>> Add some preference-related triggers
        preference_keywords = [
            "my preferences", "preference", "my availability", "i want to come",
            "prefer to work on", "i want to work on", "like to work on"
        ]

        is_leave_request = any(kw in lower_text for kw in leave_keywords)
        is_schedule_query = any(kw in lower_text for kw in schedule_keywords)
        is_swap_request = any(kw in lower_text for kw in swap_keywords)
        # <<< NEW FOR PREFERENCES >>>
        is_preference_request = any(kw in lower_text for kw in preference_keywords)

        # Step 3: Route based on intent

        if is_swap_request:
            # Attempt to parse "swap from X to Y" from text
            match = re.search(r"swap\s+from\s+(\w+)\s+to\s+(\w+)", lower_text)
            if match:
                from_text = match.group(1)
                to_text = match.group(2)
                day_map = {
                    "monday": "mon","tuesday": "tue","wednesday": "wed",
                    "thursday": "thu","friday": "fri","saturday": "sat","sunday": "sun"
                }
                from_day = day_map.get(from_text.lower())
                to_day = day_map.get(to_text.lower())
                if from_day and to_day:
                    result = process_swap_request(employee_name, from_day, to_day)
                    return jsonify({"response": result})
                else:
                    return jsonify({
                        "response": "I couldn't parse your swap request. "
                                    "Please specify 'swap from [day] to [day]'."
                    })
            else:
                return jsonify({
                    "response": "I couldn't parse your swap request. "
                                "Please specify 'swap from [day] to [day]'."
                })

        # 👉 Handle preferences next — BEFORE schedule check
        elif is_preference_request:
            pref_days = parse_multiple_days(user_text)
            if not pref_days:
                return jsonify({
                    "response": "I didn't see any days in your preference request. Please say which days you'd like to work."
                })
            update_msg = update_preferences(employee_name, pref_days)
            day_map_rev = {
                "mon": "Monday", "tue": "Tuesday", "wed": "Wednesday",
                "thu": "Thursday", "fri": "Friday", "sat": "Saturday", "sun": "Sunday"
            }
            chosen_days = [day_map_rev[d] for d in pref_days]
            return jsonify({
                "response": f"{update_msg} You prefer to work on: {', '.join(chosen_days)}."
            })

        elif day and is_leave_request:
            # If the user wants leave
            result = process_leave_request(employee_name, day)
            return jsonify({"response": result})

        elif is_schedule_query or day:
            # If the user is checking schedule or mentioned a day (but not a swap)
            schedule_response = check_schedule_query(user_text, default_employee=employee_name)
            return jsonify({"response": schedule_response})

        # <<< NEW FOR PREFERENCES >>>
        elif is_preference_request:
            # Parse multiple days
            pref_days = parse_multiple_days(user_text)
            if not pref_days:
                return jsonify({
                    "response": (
                        "I didn't see any days in your preference request. "
                        "Please say which days you'd like to work."
                    )
                })
            # Update the preferences table
            update_msg = update_preferences(employee_name, pref_days)
            # Build a nice response listing chosen days
            day_map_rev = {
                "mon": "Monday","tue": "Tuesday","wed": "Wednesday","thu": "Thursday",
                "fri": "Friday","sat": "Saturday","sun": "Sunday"
            }
            chosen_days = [day_map_rev[d] for d in pref_days]
            return jsonify({
                "response": f"{update_msg} You prefer to work on: {', '.join(chosen_days)}."
            })

        # -------------------------
        # RAG FALLBACK STEP
        # -------------------------
        rag_answer = rag_qa(user_text)
        if rag_answer:
            return jsonify({"response": rag_answer})

        # If none of the above matched or RAG gave no relevant info, fallback
        response = get_general_response(user_text)
        return jsonify({"response": response})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"response": f"Internal server error: {str(e)}"}), 500


# ---------------------------
# Run on port 5003
# ---------------------------
    


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5003)

