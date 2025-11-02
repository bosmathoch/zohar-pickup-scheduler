import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import json
import urllib.parse
import requests

# ===========================
# Configuration from Secrets
# ===========================
MAKE_WEBHOOK_URL = st.secrets.get("make_webhook_url", "")
MAKE_WEBHOOK_URL_PERSON = st.secrets.get("make_webhook_url_person", "")
APP_URL = st.secrets.get("app_url", "https://your-app.streamlit.app")

# ===========================
# Email Configuration
# ===========================

def send_email_notification(person_name, person_phone, day_name, day_date):
    """Send email notification using Make.com webhook - TO ADMIN"""
    if not MAKE_WEBHOOK_URL:
        # If webhook not configured, skip silently
        return
    
    try:
        # Send data to Make.com webhook
        webhook_data = {
            "person_name": person_name,
            "day_name": day_name,
            "day_date": day_date,
            "person_phone": person_phone,
            "app_url": APP_URL
        }
        
        response = requests.post(
            MAKE_WEBHOOK_URL,
            json=webhook_data,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 200:
            st.success("📧 מייל נשלח בהצלחה!")
        
    except Exception as e:
        # Fail silently - don't block the assignment
        pass

def send_email_to_person(person_name, person_email, day_name, day_date):
    """Send confirmation email to the assigned person"""
    if not person_email or not MAKE_WEBHOOK_URL_PERSON:
        return
    
    try:
        # Send to Make.com webhook for person email
        webhook_data = {
            "person_email": person_email,
            "person_name": person_name,
            "day_name": day_name,
            "day_date": day_date,
            "app_url": APP_URL
        }
        
        requests.post(
            MAKE_WEBHOOK_URL_PERSON,
            json=webhook_data,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
    except Exception as e:
        # Fail silently
        pass

def get_whatsapp_link(phone, message):
    """Generate WhatsApp link"""
    # Remove any non-numeric characters from phone
    clean_phone = ''.join(filter(str.isdigit, phone))
    
    # Add Israel country code if not present
    if not clean_phone.startswith('972'):
        if clean_phone.startswith('0'):
            clean_phone = '972' + clean_phone[1:]
        else:
            clean_phone = '972' + clean_phone
    
    # URL encode the message
    encoded_message = urllib.parse.quote(message)
    
    return f"https://wa.me/{clean_phone}?text={encoded_message}"

# ===========================
# Google Sheets Configuration
# ===========================

def get_google_sheet():
    """Connect to Google Sheets using service account credentials"""
    try:
        # Load credentials from Streamlit secrets
        creds_dict = st.secrets["google_credentials"]
        
        # Set up the credentials
        scope = ['https://spreadsheets.google.com/feeds',
                 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        # Open the specific spreadsheet
        sheet_id = st.secrets["sheet_id"]
        spreadsheet = client.open_by_key(sheet_id)
        
        return spreadsheet
    except Exception as e:
        st.error(f"שגיאה בחיבור ל-Google Sheets: {str(e)}")
        return None

# ===========================
# Data Management Functions
# ===========================

def load_people():
    """Load people from Google Sheets"""
    try:
        spreadsheet = get_google_sheet()
        if not spreadsheet:
            return []
        
        worksheet = spreadsheet.worksheet("People")
        
        # Get all values as a list of lists
        all_values = worksheet.get_all_values()
        
        if not all_values or len(all_values) < 1:
            return []
        
        # First row is headers
        headers = all_values[0]
        
        # Find column indices
        try:
            name_idx = headers.index('name')
            phone_idx = headers.index('phone')
            # Email column is optional - might not exist yet
            email_idx = headers.index('email') if 'email' in headers else None
        except ValueError as e:
            st.error(f"חסרות כותרות בטאב People: {str(e)}")
            return []
        
        # Build people list
        people = []
        for row in all_values[1:]:  # Skip header row
            if len(row) > name_idx and row[name_idx]:
                person = {
                    'name': row[name_idx],
                    'phone': row[phone_idx] if len(row) > phone_idx else ''
                }
                # Add email if column exists
                if email_idx is not None and len(row) > email_idx:
                    person['email'] = row[email_idx]
                else:
                    person['email'] = ''
                people.append(person)
        
        return people
    except Exception as e:
        st.error(f"שגיאה בטעינת רשימת אנשים: {str(e)}")
        return []

def save_person(name, phone, email=''):
    """Save a new person to Google Sheets"""
    try:
        spreadsheet = get_google_sheet()
        if not spreadsheet:
            return False
        
        worksheet = spreadsheet.worksheet("People")
        worksheet.append_row([name, phone, email])
        return True
    except Exception as e:
        st.error(f"שגיאה בשמירת איש קשר: {str(e)}")
        return False

def delete_person(name):
    """Delete a person from Google Sheets"""
    try:
        spreadsheet = get_google_sheet()
        if not spreadsheet:
            return False
        
        worksheet = spreadsheet.worksheet("People")
        records = worksheet.get_all_records()
        
        # Find the row to delete (row numbers start at 2 because row 1 is header)
        for idx, record in enumerate(records, start=2):
            if record['name'] == name:
                worksheet.delete_rows(idx)
                return True
        
        return False
    except Exception as e:
        st.error(f"שגיאה במחיקת איש קשר: {str(e)}")
        return False

def load_schedule(week_start):
    """Load schedule for a specific week from Google Sheets"""
    try:
        spreadsheet = get_google_sheet()
        if not spreadsheet:
            return {}
        
        worksheet = spreadsheet.worksheet("Schedule")
        
        # Get all values as a list of lists
        all_values = worksheet.get_all_values()
        
        if not all_values or len(all_values) < 1:
            return {}
        
        # First row is headers
        headers = all_values[0]
        
        # Find column indices
        try:
            week_start_idx = headers.index('week_start')
            day_index_idx = headers.index('day_index')
            person_name_idx = headers.index('person_name')
            person_phone_idx = headers.index('person_phone')
            # Email column is optional
            person_email_idx = headers.index('person_email') if 'person_email' in headers else None
        except ValueError as e:
            st.error(f"חסרות כותרות בטאב Schedule: {str(e)}")
            return {}
        
        # Build schedule dictionary
        schedule = {}
        for row in all_values[1:]:  # Skip header row
            if len(row) > max(week_start_idx, day_index_idx, person_name_idx, person_phone_idx):
                if row[week_start_idx] == week_start and row[day_index_idx]:
                    try:
                        day_idx = int(row[day_index_idx])
                        assignment = {
                            'person_name': row[person_name_idx] if len(row) > person_name_idx else '',
                            'person_phone': row[person_phone_idx] if len(row) > person_phone_idx else ''
                        }
                        # Add email if column exists
                        if person_email_idx is not None and len(row) > person_email_idx:
                            assignment['person_email'] = row[person_email_idx]
                        else:
                            assignment['person_email'] = ''
                        schedule[day_idx] = assignment
                    except (ValueError, IndexError):
                        continue
        
        return schedule
    except Exception as e:
        st.error(f"שגיאה בטעינת לוח שבועי: {str(e)}")
        return {}

def save_assignment(week_start, day_index, person_name, person_phone, person_email=''):
    """Save an assignment to Google Sheets"""
    try:
        spreadsheet = get_google_sheet()
        if not spreadsheet:
            return False
        
        worksheet = spreadsheet.worksheet("Schedule")
        
        # First, try to find and delete existing assignment for this week and day
        all_values = worksheet.get_all_values()
        if len(all_values) > 1:
            headers = all_values[0]
            try:
                week_start_idx = headers.index('week_start')
                day_index_idx = headers.index('day_index')
            except ValueError:
                pass
            else:
                for idx, row in enumerate(all_values[1:], start=2):
                    if len(row) > max(week_start_idx, day_index_idx):
                        if row[week_start_idx] == week_start and str(row[day_index_idx]) == str(day_index):
                            worksheet.delete_rows(idx)
                            break
        
        # Add new assignment
        worksheet.append_row([week_start, day_index, person_name, person_phone, person_email])
        return True
    except Exception as e:
        st.error(f"שגיאה בשמירת שיבוץ: {str(e)}")
        return False

def clear_assignment(week_start, day_index):
    """Clear an assignment from Google Sheets"""
    try:
        spreadsheet = get_google_sheet()
        if not spreadsheet:
            return False
        
        worksheet = spreadsheet.worksheet("Schedule")
        records = worksheet.get_all_records()
        
        for idx, record in enumerate(records, start=2):
            if record.get('week_start') == week_start and record.get('day_index') == day_index:
                worksheet.delete_rows(idx)
                return True
        
        return True  # Return True even if not found (it's already cleared)
    except Exception as e:
        st.error(f"שגיאה במחיקת שיבוץ: {str(e)}")
        return False

# ===========================
# Helper Functions
# ===========================

def get_week_start(date):
    """Get the Sunday of the week for a given date"""
    # weekday(): Monday=0, Sunday=6
    days_since_sunday = (date.weekday() + 1) % 7
    sunday = date - timedelta(days=days_since_sunday)
    return sunday.strftime("%Y-%m-%d")

def get_week_dates(week_start_str):
    """Get all dates for the week starting from week_start"""
    week_start = datetime.strptime(week_start_str, "%Y-%m-%d")
    return [(week_start + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]

def get_day_name(date_str):
    """Convert date string to Hebrew day name"""
    date = datetime.strptime(date_str, "%Y-%m-%d")
    days = ["ראשון", "שני", "שלישי", "רביעי", "חמישי", "שישי", "שבת"]
    # weekday(): Monday=0, Sunday=6
    # We want Sunday=0, so we use (weekday + 1) % 7
    day_index = (date.weekday() + 1) % 7
    return days[day_index]

# ===========================
# UI Functions
# ===========================

def admin_settings():
    """Admin settings page for managing people"""
    st.header("⚙️ הגדרות מנהל")
    
    # Password protection
    if 'admin_authenticated' not in st.session_state:
        st.session_state.admin_authenticated = False
    
    if not st.session_state.admin_authenticated:
        password = st.text_input("סיסמת מנהל:", type="password")
        if st.button("כניסה"):
            if password == st.secrets.get("admin_password", "1234"):
                st.session_state.admin_authenticated = True
                st.rerun()
            else:
                st.error("סיסמה שגויה!")
        return
    
    st.success("התחברת כמנהל")
    
    # Load existing people
    people = load_people()
    
    st.subheader("➕ הוסף איש קשר חדש")
    with st.form("add_person_form"):
        new_name = st.text_input("שם:")
        new_phone = st.text_input("טלפון:")
        new_email = st.text_input("מייל (אופציונלי):")
        submit = st.form_submit_button("הוסף")
        
        if submit and new_name:
            if save_person(new_name, new_phone, new_email):
                st.success(f"✅ {new_name} נוסף בהצלחה!")
                st.rerun()
    
    st.subheader("👥 רשימת אנשי קשר")
    if people:
        for person in people:
            col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
            with col1:
                st.write(f"**{person['name']}**")
            with col2:
                st.write(person.get('phone', ''))
            with col3:
                st.write(person.get('email', ''))
            with col4:
                if st.button("🗑️", key=f"delete_{person['name']}"):
                    if delete_person(person['name']):
                        st.success(f"✅ {person['name']} נמחק!")
                        st.rerun()
    else:
        st.info("אין אנשי קשר. הוסף את הראשון!")
    
    if st.button("🚪 התנתק"):
        st.session_state.admin_authenticated = False
        st.rerun()

def schedule_view():
    """Main schedule view"""
    st.header("📅 לוח שבועי - מי מבלה עם זוהר?")
    
    # Week navigation
    if 'current_week_offset' not in st.session_state:
        st.session_state.current_week_offset = 0
    
    col1, col2, col3 = st.columns([1, 3, 1])
    with col1:
        if st.button("◀️ שבוע קודם"):
            st.session_state.current_week_offset -= 1
            st.rerun()
    with col2:
        today = datetime.now()
        current_week = today + timedelta(weeks=st.session_state.current_week_offset)
        week_start_str = get_week_start(current_week)
        week_dates = get_week_dates(week_start_str)
        
        week_start_date = datetime.strptime(week_dates[0], "%Y-%m-%d")
        week_end_date = datetime.strptime(week_dates[6], "%Y-%m-%d")
        st.markdown(f"### {week_start_date.strftime('%d/%m')} - {week_end_date.strftime('%d/%m/%Y')}")
    with col3:
        if st.button("שבוע הבא ▶️"):
            st.session_state.current_week_offset += 1
            st.rerun()
    
    # Load people and schedule
    people = load_people()
    schedule = load_schedule(week_start_str)
    
    if not people:
        st.warning("⚠️ אין אנשי קשר במערכת. לך להגדרות מנהל כדי להוסיף.")
        return
    
    # Define days list
    days = ["ראשון", "שני", "שלישי", "רביעי", "חמישי", "שישי"]
    
    # Add "Send reminders" section at the top
    st.markdown("---")
    st.subheader("📲 שליחת תזכורות WhatsApp")
    
    # Collect all assignments for this week
    assignments = []
    for day_idx in range(6):  # Only weekdays
        assigned = schedule.get(day_idx)
        if assigned and assigned.get('person_phone'):
            date_str = week_dates[day_idx]
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            formatted_date = date_obj.strftime("%d/%m")
            day_name = days[day_idx]
            
            assignments.append({
                'name': assigned['person_name'],
                'phone': assigned['person_phone'],
                'day_name': day_name,
                'date': formatted_date
            })
    
    if assignments:
        st.info(f"📋 {len(assignments)} שיבוצים השבוע")
        
        # Show individual WhatsApp buttons
        for assignment in assignments:
            whatsapp_message = f"היי {assignment['name']}!\nרק תזכורת קטנה לפני הבילוי עם זוהר ביום {assignment['day_name']}, {assignment['date']}.\nזוהר כבר מתרגש!\nתודה רבה!"
            whatsapp_link = get_whatsapp_link(assignment['phone'], whatsapp_message)
            
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"**{assignment['name']}** - {assignment['day_name']} ({assignment['date']})")
            with col2:
                st.markdown(f"[💬 WhatsApp]({whatsapp_link})")
        
        # Option to send to all
        st.markdown("---")
        if st.button("📱 פתח את כל התזכורות ב-WhatsApp"):
            st.markdown("### לחץ על הקישורים למעלה ↑")
    else:
        st.info("אין שיבוצים עם מספרי טלפון השבוע.")
    
    # Display schedule
    st.markdown("---")
    
    for day_idx, (day_name, date_str) in enumerate(zip(days, week_dates[:6])):  # Only first 6 days
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        formatted_date = date_obj.strftime("%d/%m")
        
        st.markdown(f"### {day_name} - {formatted_date}")
        
        # Check if already assigned
        assigned = schedule.get(day_idx)
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            if assigned:
                st.success(f"✅ **{assigned['person_name']}** מבלה עם זוהר")
                if assigned.get('person_phone'):
                    st.caption(f"📞 {assigned['person_phone']}")
                    
                    # WhatsApp reminder button
                    whatsapp_message = f"היי {assigned['person_name']}!\nרק תזכורת קטנה לפני הבילוי עם זוהר ביום {day_name}, {formatted_date}.\nזוהר כבר מתרגש!\nתודה רבה!"
                    whatsapp_link = get_whatsapp_link(assigned['person_phone'], whatsapp_message)
                    st.markdown(f"[💬 שלח תזכורת בWhatsApp]({whatsapp_link})", unsafe_allow_html=True)
            else:
                # Selection
                selected_person = st.selectbox(
                    "בחר מי אוסף:",
                    [""] + [p['name'] for p in people],
                    key=f"select_{day_idx}_{week_start_str}"
                )
                
                if selected_person and st.button("שבץ", key=f"assign_{day_idx}_{week_start_str}"):
                    person = next((p for p in people if p['name'] == selected_person), None)
                    if person:
                        if save_assignment(week_start_str, day_idx, person['name'], person.get('phone', ''), person.get('email', '')):
                            st.success(f"✅ {person['name']} שובץ ליום {day_name}!")
                            
                            # Send email notification to admin
                            try:
                                send_email_notification(
                                    person['name'],
                                    person.get('phone', ''),
                                    day_name,
                                    formatted_date
                                )
                            except Exception as e:
                                pass
                            
                            # Send email to assigned person
                            if person.get('email'):
                                try:
                                    send_email_to_person(
                                        person['name'],
                                        person['email'],
                                        day_name,
                                        formatted_date
                                    )
                                except Exception as e:
                                    pass
                            
                            st.rerun()
        
        with col2:
            if assigned:
                # Only show delete button if user is admin
                if st.session_state.get('admin_authenticated', False):
                    if st.button("❌ בטל", key=f"clear_{day_idx}_{week_start_str}"):
                        if clear_assignment(week_start_str, day_idx):
                            st.success("השיבוץ בוטל!")
                            st.rerun()
                else:
                    st.caption("🔒 רק מנהל יכול לבטל")
        
        st.markdown("---")

# ===========================
# Main App
# ===========================

def main():
    st.set_page_config(
        page_title="מי מבלה עם זוהר היום?",
        page_icon="👶",
        layout="wide"
    )
    
    st.title("👶 מי מבלה עם זוהר היום?")
    
    # Sidebar navigation
    page = st.sidebar.radio("ניווט:", ["📅 לוח שבועי", "⚙️ הגדרות מנהל"])
    
    if page == "📅 לוח שבועי":
        schedule_view()
    else:
        admin_settings()

if __name__ == "__main__":
    main()
