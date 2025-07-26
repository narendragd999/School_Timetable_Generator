import streamlit as st
import pandas as pd
import numpy as np
from datetime import time
import pdfkit
from io import BytesIO
import base64

# Initialize session state for storing data
if 'timetable' not in st.session_state:
    st.session_state.timetable = {}
if 'teacher_timetable' not in st.session_state:
    st.session_state.teacher_timetable = {}
if 'manual_changes' not in st.session_state:
    st.session_state.manual_changes = {}

# School schedule configuration
SCHOOL_START = time(10, 0)
SCHOOL_END = time(16, 0)
ASSEMBLY = (time(10, 0), time(10, 10))
LUNCH = (time(13, 55), time(14, 15))
DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
PERIODS = [
    (time(10, 0), time(10, 10)),   # Assembly (10 min)
    (time(10, 10), time(10, 55)),  # Period 1 (45 min)
    (time(10, 55), time(11, 40)),  # Period 2 (45 min)
    (time(11, 40), time(12, 25)),  # Period 3 (45 min)
    (time(12, 25), time(13, 10)),  # Period 4 (45 min)
    (time(13, 10), time(13, 55)),  # Period 5 (45 min)
    (time(13, 55), time(14, 15)),  # Lunch (20 min)
    (time(14, 15), time(15, 0)),   # Period 6 (45 min)
    (time(15, 0), time(15, 45)),   # Period 7 (45 min)
    (time(15, 45), time(16, 0))    # Period 8 (15 min)
]
PERIOD_LABELS = [
    f"Assembly (10:00–10:10)",
    f"Period 1 (10:10–10:55)",
    f"Period 2 (10:55–11:40)",
    f"Period 3 (11:40–12:25)",
    f"Period 4 (12:25–13:10)",
    f"Period 5 (13:10–13:55)",
    f"Lunch (13:55–14:15)",
    f"Period 6 (14:15–15:00)",
    f"Period 7 (15:00–15:45)",
    f"Period 8 (15:45–16:00)"
]

# Function to generate timetable
def generate_timetable(classes, sections, subjects, teachers, periods_per_subject, class_teachers):
    timetable = {}
    teacher_timetable = {t: {d: ['Free'] * len(PERIODS) for d in DAYS} for t in teachers}
    
    for cls in range(1, classes + 1):
        for sec in sections:
            class_key = f"Class {cls}{sec}"
            timetable[class_key] = {d: ['Assembly'] + ['Free'] * (len(PERIODS) - 1) for d in DAYS}
            class_teacher_key = f"Class {cls}{sec}"
            class_teacher = class_teachers.get(class_teacher_key, None)
            
            # Assign class teacher to first teaching period (after assembly)
            for day in DAYS:
                if class_teacher:
                    timetable[class_key][day][1] = f"{class_teacher} (Class Teacher)"
                    teacher_timetable[class_teacher][day][1] = class_key
                    
            # Assign lunch
            for day in DAYS:
                timetable[class_key][day][6] = 'Lunch'
                if class_teacher:
                    teacher_timetable[class_teacher][day][6] = 'Lunch'
                
            # Calculate total required periods
            total_periods = sum(subjects[cls-1].values())
            available_periods = 6 * 8  # 6 days, 8 teaching periods
            if total_periods > available_periods:
                st.warning(f"Class {cls}{sec}: Total required periods ({total_periods}) exceeds available periods ({available_periods}). Some subjects may not be fully assigned.")
            elif total_periods < available_periods - 6:  # Account for class teacher periods
                st.info(f"Class {cls}{sec}: Only {total_periods} periods assigned out of {available_periods - 6} available (excluding class teacher). Expect some 'Free' periods.")
            
            # Assign subjects for 8 teaching periods
            for subject, periods in subjects[cls-1].items():
                teacher = [t for t, subs in teachers.items() if subject in subs]
                if not teacher:
                    st.warning(f"No teacher available for subject '{subject}' in Class {cls}{sec}. Skipping.")
                    continue
                teacher = teacher[0]
                assigned = 0
                attempts = 0
                max_attempts = 100  # Prevent infinite loops
                # Try to distribute across days
                days_list = DAYS.copy()
                np.random.shuffle(days_list)
                for day in days_list:
                    available_periods = [1, 2, 3, 4, 5, 7, 8, 9]  # Teaching periods
                    np.random.shuffle(available_periods)
                    for period in available_periods:
                        if assigned >= periods:
                            break
                        if timetable[class_key][day][period] == 'Free' and teacher_timetable[teacher][day][period] == 'Free':
                            timetable[class_key][day][period] = subject
                            teacher_timetable[teacher][day][period] = class_key
                            assigned += 1
                        attempts += 1
                        if attempts > max_attempts:
                            st.warning(f"Could not assign all {periods} periods for {subject} in Class {cls}{sec}. Assigned {assigned} periods.")
                            break
                    if attempts > max_attempts:
                        break
    
    return timetable, teacher_timetable

# Function to export to Excel
def export_to_excel(timetable, teacher_timetable):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        for class_key, schedule in timetable.items():
            df = pd.DataFrame(schedule, index=PERIOD_LABELS)
            df.to_excel(writer, sheet_name=class_key)
        for teacher, schedule in teacher_timetable.items():
            df = pd.DataFrame(schedule, index=PERIOD_LABELS)
            df.to_excel(writer, sheet_name=teacher)
    return output.getvalue()

# Function to export to PDF
def export_to_pdf(timetable, teacher_timetable):
    html_content = """
    <html>
    <head><style>
    table { border-collapse: collapse; width: 100%; }
    th, td { border: 1px solid black; padding: 5px; text-align: center; }
    </style></head>
    <body>
    """
    for class_key, schedule in timetable.items():
        html_content += f"<h2>{class_key}</h2>"
        df = pd.DataFrame(schedule, index=PERIOD_LABELS)
        html_content += df.to_html()
    for teacher, schedule in teacher_timetable.items():
        html_content += f"<h2>{teacher}</h2>"
        df = pd.DataFrame(schedule, index=PERIOD_LABELS)
        html_content += df.to_html()
    html_content += "</body></html>"
    
    pdf_file = BytesIO()
    pdfkit.from_string(html_content, pdf_file)
    return pdf_file.getvalue()

# Streamlit app
st.title("Rajasthan School Timetable Generator")

# Input form
with st.form("timetable_form"):
    classes = st.number_input("Number of Classes (1-5)", min_value=1, max_value=12, value=5)
    sections = st.text_input("Sections (e.g., A,B,C)", value="A").split(',')
    subjects_input = st.text_area(
        "Subjects per class (e.g., Class 1: Maths:4,English:4,Hindi:4; Class 2: Maths:5,English:5,Hindi:5)", 
        value="Class 1: Maths:4,English:4,Hindi:4,PE:2,Art:2; Class 2: Maths:5,English:5,Hindi:5,PE:2,Art:2; Class 3: Maths:5,English:5,Hindi:5,PE:2,Art:2; Class 4: Maths:5,English:5,Hindi:5,PE:2,Art:2; Class 5: Maths:5,English:5,Hindi:5,PE:2,Art:2"
    )
    teachers_input = st.text_area(
        "Teachers and Subjects (e.g., T1:Maths,Science; T2:English,Hindi)", 
        value="T1:Maths; T2:English; T3:Hindi; T4:PE; T5:Art"
    )
    class_teachers = st.text_area(
        "Class Teachers (e.g., Class 1A:T1, Class 1B:T2)", 
        value="Class 1A:T1,Class 2A:T2, Class 3A:T3, Class 4A:T4, Class 5A:T5"
    )
    submitted = st.form_submit_button("Generate Timetable")

if submitted:
    # Parse inputs with enhanced validation
    subjects = []
    for cls in range(1, classes + 1):
        sub_dict = {}
        class_prefix = f"Class {cls}:"
        matching_line = None
        for line in subjects_input.split(';'):
            line = line.strip()
            if line.startswith(class_prefix):
                matching_line = line
                break

        if not matching_line:
            st.error(f"No entry found for Class {cls}. Please provide subjects in the format: Class {cls}: Subject1:Periods,...")
            st.stop()

        try:
            _, subject_part = matching_line.split(":", 1)
            subject_list = subject_part.split(',')
            for sub in subject_list:
                sub = sub.strip()
                if not sub:
                    continue
                try:
                    name, periods = sub.split(':')
                    name = name.strip()
                    periods = periods.strip()
                    if not name:
                        st.warning(f"Missing subject name in '{sub}' for Class {cls}. Skipping.")
                        continue
                    if not periods.isdigit() or int(periods) <= 0:
                        st.warning(f"Invalid period count in '{sub}' for Class {cls}. Skipping.")
                        continue
                    sub_dict[name] = int(periods)
                except ValueError:
                    st.warning(f"Invalid subject format '{sub}' in Class {cls}. Expected: Subject:Periods")
                    continue
        except ValueError:
            st.error(f"Invalid format for Class {cls}: '{matching_line}'. Skipping this class.")
            st.stop()

        if not sub_dict:
            st.error(f"No valid subjects found for Class {cls}.")
            st.stop()

        subjects.append(sub_dict)

    teachers = {}
    for line in teachers_input.split(';'):
        line = line.strip()
        if not line:
            continue
        try:
            t, subs = line.split(':')
            t = t.strip()
            if not t:
                st.error(f"Missing teacher name in '{line}'. Skipping this teacher.")
                continue
            subs = [s.strip() for s in subs.split(',') if s.strip()]
            if not subs:
                st.error(f"No subjects provided for teacher '{t}'. Skipping this teacher.")
                continue
            teachers[t] = subs
        except ValueError:
            st.error(f"Invalid teacher format for '{line}'. Expected format: Teacher:Subject1,Subject2 (e.g., T1:Maths,Science). Skipping this teacher.")
            continue
    
    class_teachers_dict = {}
    for line in class_teachers.split(','):
        line = line.strip()
        if not line:
            continue
        try:
            cls, teacher = line.split(':')
            cls = cls.strip()
            teacher = teacher.strip()
            if not cls or not teacher:
                st.error(f"Invalid class teacher format for '{line}'. Expected format: Class:Teacher (e.g., Class 1A:T1). Skipping this entry.")
                continue
            class_teachers_dict[cls] = teacher
        except ValueError:
            st.error(f"Invalid class teacher format for '{line}'. Expected format: Class:Teacher (e.g., Class 1A:T1). Skipping this entry.")
            continue
    
    if not teachers:
        st.error("No valid teachers provided. Please check the input format.")
        st.stop()
    
    # Generate timetable
    st.session_state.timetable, st.session_state.teacher_timetable = generate_timetable(
        classes, sections, subjects, teachers, None, class_teachers_dict
    )

# Display and filter timetable
if st.session_state.timetable:
    st.subheader("View Timetable")
    view_type = st.selectbox("View by", ["Class", "Teacher"])
    if view_type == "Class":
        class_key = st.selectbox("Select Class", list(st.session_state.timetable.keys()))
        df = pd.DataFrame(st.session_state.timetable[class_key], index=PERIOD_LABELS)
        st.table(df)
        
        # Manual adjustment
        st.subheader("Adjust Timetable")
        day = st.selectbox("Select Day", DAYS)
        period = st.selectbox("Select Period", [label for label in PERIOD_LABELS if label not in ['Assembly (10:00–10:10)', 'Lunch (13:55–14:15)']], index=0)
        new_subject = st.text_input("New Subject/Teacher")
        if st.button("Apply Change"):
            st.session_state.timetable[class_key][day][PERIOD_LABELS.index(period)] = new_subject
            st.session_state.manual_changes[(class_key, day, period)] = new_subject
            st.success("Timetable updated!")
    
    else:
        teacher = st.selectbox("Select Teacher", list(st.session_state.teacher_timetable.keys()))
        df = pd.DataFrame(st.session_state.teacher_timetable[teacher], index=PERIOD_LABELS)
        st.table(df)
    
    # Day-wise toggle
    st.subheader("Day-wise View")
    selected_day = st.selectbox("Select Day for All Classes", DAYS)
    for class_key in st.session_state.timetable:
        st.write(f"**{class_key}**")
        df = pd.DataFrame({selected_day: st.session_state.timetable[class_key][selected_day]}, index=PERIOD_LABELS)
        st.table(df)
    
    # Export options
    st.subheader("Export Timetable")
    if st.button("Export to Excel"):
        excel_data = export_to_excel(st.session_state.timetable, st.session_state.teacher_timetable)
        st.download_button("Download Excel", excel_data, file_name="timetable.xlsx", mime="application/vnd.ms-excel")
    
    if st.button("Export to PDF"):
        pdf_data = export_to_pdf(st.session_state.timetable, st.session_state.teacher_timetable)
        st.download_button("Download PDF", pdf_data, file_name="timetable.pdf", mime="application/pdf")