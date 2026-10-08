import os
from dotenv import load_dotenv
from supabase import create_client, Client
from paystack_utils import create_virtual_account

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_KEY in .env file.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def register_new_student(student_name: str, student_class: str, parent_phone: str, parent_email: str):
    """
    1. Calls Paystack to create a Dedicated Virtual Account.
    2. Saves the student details and generated Account Number into Supabase.
    """
    print(f"🔄 Creating Virtual Account for {student_name}...")
    account_info = create_virtual_account(student_name, parent_email, parent_phone)

    if not account_info:
        print("❌ Could not generate Virtual Account. Registration aborted.")
        return None

    # Insert student record into Supabase
    student_payload = {
        "student_name": student_name,
        "student_class": student_class,
        "parent_phone": parent_phone,
        "parent_email": parent_email,
        "account_number": account_info["account_number"],
        "bank_name": account_info["bank_name"]
    }

    try:
        response = supabase.table("students").insert(student_payload).execute()
        print("✅ Student successfully registered in Supabase database!")
        print("Student Data:", response.data)
        return response.data
    except Exception as e:
        print("❌ Supabase Insert Error:", e)
        return None


def record_payment_in_db(account_number: str, amount_paid: float, reference: str):
    """
    Finds student by account number and records their payment.
    """
    try:
        # Find student by Virtual Account Number
        student_res = supabase.table("students").select("id, student_name").eq("account_number", account_number).execute()
        
        if not student_res.data:
            print(f"⚠️ No student found with Account Number: {account_number}")
            return None

        student = student_res.data[0]
        student_id = student["id"]

        # Insert Payment Record
        payment_payload = {
            "student_id": student_id,
            "amount_paid": amount_paid,
            "transaction_reference": reference
        }

        payment_res = supabase.table("payments").insert(payment_payload).execute()
        print(f"🎉 Payment of ₦{amount_paid} recorded for {student['student_name']}!")
        return payment_res.data

    except Exception as e:
        print("❌ Payment Record Error:", e)
        return None


if __name__ == "__main__":
    # Test registering a real test student
    register_new_student(
        student_name="Emeka Okonkwo",
        student_class="JSS 2A",
        parent_phone="08099887766",
        parent_email="emeka_parent@gmail.com"
    )