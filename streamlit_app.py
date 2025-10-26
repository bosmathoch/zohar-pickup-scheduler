import streamlit as st
import json
import os
from datetime import datetime, timedelta
import urllib.parse

# Page config
st.set_page_config(
    page_title="מי לוקח את זוהר היום?",
    page_icon="👦",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for modern design
st.markdown("""
<style>
    /* RTL Support */
    .main {
        direction: rtl;
        text-align: right;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Modern colors */
    :root {
        --primary-color: #6366f1;
        --success-color: #10b981;
        --danger-color: #ef4444;
    }
    
    /* Title styling */
    h1 {
        color: #6366f1 !important;
        text-align: center !important;
        font-size: 2.5rem !important;
        margin-bottom: 0.5rem !important;
    }
    
    /* Subtitle */
    .subtitle {
        text-align: center;
        color: #64748b;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }
    
    /* Week info */
    .week-info {
        background: #f0f4ff;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
        font-weight: 600;
        color: #6366f1;
        margin-bottom: 2rem;
    }
    
    /* Day cards */
    .day-card {
        background: white;
        padding: 1.5rem;
        border-radius: 15px;
        border: 3px solid #e2e8f0;
        text-align: center;
        margin: 0.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    .day-card.available {
        background: #d1fae5;
        border-color: #10b981;
    }
    
    .day-card.taken {
        background: #fee2e2;
        border-color: #ef4444;
    }
    
    .day-name {
        font-size: 1.3rem;
        font-weight: bold;
        margin-bottom: 0.3rem;
    }
    
    .day-date {
        color: #64748b;
        font-size: 0.9rem;
        margin-bottom: 0.5rem;
    }
    
    .day-status {
        padding: 0.5rem;
        border-radius: 8px;
        font-weight: 600;
        margin-top: 0.5rem;
    }
    
    .status-available {
        background: #a7f3d0;
        color: #065f46;
    }
    
    .status-taken {
        background: #fecaca;
        color: #991b1b;
    }
    
    /* Buttons */
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        font-weight: 600;
        padding: 0.5rem 1rem;
    }
    
    /* People list */
    .person-item {
        background: #f1f5f9;
        padding: 0.8rem;
        border-radius: 8px;
        margin: 0.3rem 0;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
</style>
""", unsafe_allow_html=True)

# Data file
DATA_FILE = 'pickup_data.json'
ADMIN_PASSWORD = "zohar2024"  # שני את הסיסמה כאן

def load_data():
    """טעינת נתונים מהקובץ"""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {'people': [], 'schedule': {}}
    return {'people': [], 'schedule': {}}

def save_data(data):
    """שמירת נתונים לקובץ"""
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_week_start(week_offset=0):
    """קבלת תחילת שבוע"""
    today = datetime.now()
    week_start = today - timedelta(days=today.weekday())
    week_start = week_start + timedelta(weeks=week_offset)
    return week_start.strftime('%Y-%m-%d')

def format_week_range(week_start_str):
    """עיצוב טווח השבוע"""
    week_start = datetime.strptime(week_start_str, '%Y-%m-%d')
    week_end = week_start + timedelta(days=4)
    return f"שבוע {week_start.strftime('%d/%m/%Y')} - {week_end.strftime('%d/%m/%Y')}"

def get_date_for_day(week_start_str, day_index):
    """קבלת תאריך ליום מסוים"""
    week_start = datetime.strptime(week_start_str, '%Y-%m-%d')
    date = week_start + timedelta(days=day_index)
    return date.strftime('%d/%m')

def send_whatsapp(person, day_name):
    """יצירת קישור WhatsApp"""
    message = f"""היי {person['name']}! 👋

תזכורת: מחר ({day_name}) תורך לאסוף את זוהר מהגן.
שעות: 15:30 - 18:00

תודה! 🙏"""
    
    encoded_message = urllib.parse.quote(message)
    
    if person.get('phone'):
        phone = ''.join(filter(str.isdigit, person['phone']))
        url = f"https://wa.me/972{phone}?text={encoded_message}"
    else:
        url = f"https://wa.me/?text={encoded_message}"
    
    return url

# Initialize session state
if 'week_offset' not in st.session_state:
    st.session_state.week_offset = 0

if 'admin_mode' not in st.session_state:
    st.session_state.admin_mode = False

if 'show_people_section' not in st.session_state:
    st.session_state.show_people_section = False

# Load data
data = load_data()
people = data.get('people', [])
schedule = data.get('schedule', {})

# Get current week
current_week = get_week_start(st.session_state.week_offset)

# Header
st.markdown("# מי לוקח את זוהר היום? 👦")
st.markdown('<div class="subtitle">שעות: 15:30 - 18:00 | ימים א\'-ה\'</div>', unsafe_allow_html=True)

# Week navigation
col_prev, col_week, col_next = st.columns([1, 3, 1])

with col_prev:
    if st.button("◀ שבוע קודם", use_container_width=True):
        st.session_state.week_offset -= 1
        st.rerun()

with col_week:
    st.markdown(f'<div class="week-info">{format_week_range(current_week)}</div>', unsafe_allow_html=True)

with col_next:
    if st.button("שבוע הבא ▶", use_container_width=True):
        st.session_state.week_offset += 1
        st.rerun()

# People management (admin only)
with st.expander("👨‍👩‍👧 ניהול אנשים (מנהל בלבד)", expanded=st.session_state.show_people_section):
    
    # Admin authentication
    if not st.session_state.admin_mode:
        password = st.text_input("סיסמת מנהל:", type="password", key="admin_password_input")
        if st.button("כניסה"):
            if password == ADMIN_PASSWORD:
                st.session_state.admin_mode = True
                st.session_state.show_people_section = True
                st.rerun()
            else:
                st.error("סיסמה שגויה!")
    else:
        st.success("מצב מנהל פעיל ✓")
        
        # Add person
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            new_name = st.text_input("שם:", key="new_person_name")
        with col2:
            new_phone = st.text_input("טלפון (אופציונלי):", key="new_person_phone")
        with col3:
            st.write("")
            st.write("")
            if st.button("➕ הוסף", use_container_width=True):
                if new_name:
                    people.append({'name': new_name, 'phone': new_phone})
                    data['people'] = people
                    save_data(data)
                    st.success(f"{new_name} נוסף בהצלחה!")
                    st.rerun()
                else:
                    st.error("נא להזין שם")
        
        # Show people list
        if people:
            st.write("**רשימת אנשים:**")
            for i, person in enumerate(people):
                col_name, col_delete = st.columns([4, 1])
                with col_name:
                    phone_text = f" • {person['phone']}" if person.get('phone') else ""
                    st.write(f"👤 {person['name']}{phone_text}")
                with col_delete:
                    if st.button("✕", key=f"delete_{i}"):
                        people.pop(i)
                        data['people'] = people
                        save_data(data)
                        st.rerun()
        else:
            st.info("עדיין לא הוספת אנשים")
        
        # Logout
        if st.button("יציאה ממצב מנהל"):
            st.session_state.admin_mode = False
            st.session_state.show_people_section = False
            st.rerun()

st.markdown("---")

# Schedule display
st.markdown("### 📅 לוח השבוע")

days = ['ראשון', 'שני', 'שלישי', 'רביעי', 'חמישי']

# Display days in grid (RTL: right to left)
cols = st.columns(5)

for i in range(5):
    # RTL: display from right to left (4-i)
    with cols[4-i]:
        day_date = get_date_for_day(current_week, i)
        week_day_key = f"{current_week}_{i}"
        assigned = schedule.get(week_day_key)
        is_available = not assigned
        
        # Day card
        card_class = "available" if is_available else "taken"
        status_class = "status-available" if is_available else "status-taken"
        
        st.markdown(f"""
        <div class="day-card {card_class}">
            <div class="day-name">{days[i]}</div>
            <div class="day-date">{day_date}</div>
        </div>
        """, unsafe_allow_html=True)
        
        if is_available:
            st.markdown(f'<div class="day-status {status_class}">✅ זמין</div>', unsafe_allow_html=True)
            
            # Select person
            if people:
                selected = st.selectbox(
                    "בחר מי יאסף:",
                    [""] + [p['name'] for p in people],
                    key=f"select_{i}",
                    label_visibility="collapsed"
                )
                
                if selected and st.button("✓ שבץ", key=f"assign_{i}", use_container_width=True):
                    person = next(p for p in people if p['name'] == selected)
                    schedule[week_day_key] = person
                    data['schedule'] = schedule
                    save_data(data)
                    st.success(f"{selected} משובץ ליום {days[i]}!")
                    st.rerun()
            else:
                st.warning("אין אנשים ברשימה")
        else:
            st.markdown(f'<div class="day-status {status_class}">👤 {assigned["name"]}</div>', unsafe_allow_html=True)
            
            # WhatsApp button
            whatsapp_url = send_whatsapp(assigned, days[i])
            st.markdown(f'<a href="{whatsapp_url}" target="_blank"><button style="width:100%; background:#25D366; color:white; border:none; padding:0.5rem; border-radius:8px; cursor:pointer; font-weight:600; margin:0.3rem 0;">📱 שלח תזכורת</button></a>', unsafe_allow_html=True)
            
            # Clear button (admin only)
            if st.session_state.admin_mode:
                if st.button("ביטול", key=f"clear_{i}", use_container_width=True):
                    del schedule[week_day_key]
                    data['schedule'] = schedule
                    save_data(data)
                    st.rerun()

# Reset week (admin only)
if st.session_state.admin_mode:
    st.markdown("---")
    if st.button("🔄 אפס שבוע (מחיקת כל השיבוצים)", use_container_width=True):
        if st.checkbox("אני בטוח שאני רוצה למחוק הכל"):
            schedule = {}
            data['schedule'] = schedule
            save_data(data)
            st.success("השבוע אופס בהצלחה!")
            st.rerun()

# Footer
st.markdown("---")
st.markdown('<div style="text-align: center; color: #64748b; font-size: 0.9rem;">אפליקציית תזמון איסוף מהגן • נבנתה עם ❤️</div>', unsafe_allow_html=True)
