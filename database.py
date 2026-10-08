import os
import hashlib
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
from supabase import create_client, Client
from paystack_utils import create_virtual_account

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SENDER_NAME = os.getenv("SENDER_NAME", "School SaaS Portal")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_KEY in .env file.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def hash_password(password: str) -> str:
    """Hashes passwords securely using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()

# --- AUTHENTICATION FUNCTIONS ---

def register_school(school_name: str, admin_email: str, password: str):
    """Registers a new school account in Supabase."""
    clean_email = admin_email.strip().lower()
    
    # Check if email already exists
    existing = supabase.table("schools").select("id").eq("admin_email", clean_email).execute()
    if existing.data and len(existing.data) > 0:
        return {"success": False, "message": "An account with this email already exists."}

    payload = {
        "school_name": school_name.strip(),
        "admin_email": clean_email,
        "password_hash": hash_password(password)
    }

    try:
        res = supabase.table("schools").insert(payload).execute()
        if res.data:
            return {"success": True, "school": res.data[0]}
        return {"success": False, "message": "Failed to create school profile."}
    except Exception as e:
        return {"success": False, "message": str(e)}

def login_school(admin_email: str, password: str):
    """Verifies school admin credentials."""
    clean_email = admin_email.strip().lower()
    hashed = hash_password(password)

    try:
        res = supabase.table("schools").select("*").eq("admin_email", clean_email).eq("password_hash", hashed).execute()
        if res.data and len(res.data) > 0:
            return {"success": True, "school": res.data[0]}
        return {"success": False, "message": "Invalid email address or password."}
    except Exception as e:
        return {"success": False, "message": str(e)}

def send_password_reset_otp(admin_email: str):
    """Generates a temporary reset OTP and emails it to the school admin."""
    clean_email = admin_email.strip().lower()
    
    res = supabase.table("schools").select("id, school_name").eq("admin_email", clean_email).execute()
    if not res.data:
        return {"success": False, "message": "No school found with that email address."}

    school = res.data[0]
    otp = str(random.randint(100000, 999999))

    if not SMTP_USER or not SMTP_PASSWORD:
        return {"success": False, "message": "SMTP email configuration missing in .env."}

    try:
        msg = MIMEMultipart()
        msg['From'] = f"{SENDER_NAME} <{SMTP_USER}>"
        msg['To'] = clean_email
        msg['Subject'] = "Password Reset OTP - School SaaS Portal"

        body = f"""Hello {school['school_name']},

You requested a password reset for your School SaaS Admin account.

Your 6-digit Password Reset OTP code is: {otp}

If you did not request this, please ignore this email.

Best regards,
School SaaS Support Team
"""
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()

        return {"success": True, "otp": otp, "school_id": school['id']}
    except Exception as e:
        return {"success": False, "message": f"SMTP Error: {e}"}

def reset_school_password(admin_email: str, new_password: str):
    """Updates password for a verified email address."""
    clean_email = admin_email.strip().lower()
    hashed = hash_password(new_password)

    try:
        res = supabase.table("schools").update({"password_hash": hashed}).eq("admin_email", clean_email).execute()
        if res.data:
            return {"success": True}
        return {"success": False, "message": "Password update failed."}
    except Exception as e:
        return {"success": False, "message": str(e)}

# --- STUDENT & PAYMENT FUNCTIONS ---

def register_new_student(student_name: str, student_class: str, parent_phone: str, parent_email: str, school_id: str, expected_fee: float = 0.0):
    """Generates a Paystack Virtual Account and assigns the student to a specific school with expected fee tracking."""
    account_info = create_virtual_account(student_name, parent_email, parent_phone)

    if not account_info:
        return None

    student_payload = {
        "student_name": student_name,
        "student_class": student_class,
        "parent_phone": parent_phone,
        "parent_email": parent_email,
        "account_number": account_info["account_number"],
        "bank_name": account_info["bank_name"],
        "school_id": school_id,
        "expected_fee": expected_fee
    }

    try:
        response = supabase.table("students").insert(student_payload).execute()
        return response.data
    except Exception as e:
        print("❌ Supabase Insert Error:", e)
        return None

def record_payment_in_db(account_number: str, amount_paid: float, reference: str):
    """Records payment and logs the N1,000 SaaS platform reconciliation fee."""
    try:
        student_res = supabase.table("students").select("id, school_id, student_name").eq("account_number", account_number).execute()
        
        if not student_res.data:
            return None

        student = student_res.data[0]
        student_id = student["id"]
        school_id = student.get("school_id")

        # 1. Insert fee payment
        payment_payload = {
            "student_id": student_id,
            "amount_paid": amount_paid,
            "transaction_reference": reference
        }
        payment_res = supabase.table("payments").insert(payment_payload).execute()

        # 2. Log N1,000 SaaS pay-as-you-go fee into saas_ledger
        if school_id:
            ledger_payload = {
                "school_id": school_id,
                "student_id": student_id,
                "transaction_reference": reference,
                "fee_amount": 1000
            }
            supabase.table("saas_ledger").insert(ledger_payload).execute()

        return payment_res.data

    except Exception as e:
        print("❌ Payment Record Error:", e)
        return None