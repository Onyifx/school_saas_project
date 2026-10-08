import os
import requests
import random
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY")

HEADERS = {
    "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
    "Content-Type": "application/json"
}

def create_virtual_account(student_name: str, parent_email: str, parent_phone: str):
    """
    1. Creates a customer on Paystack using parent details.
    2. Generates a Dedicated Virtual Account (DVA) tied to that customer.
    """
    if not PAYSTACK_SECRET_KEY:
        print("❌ Error: PAYSTACK_SECRET_KEY is missing in .env file.")
        return None

    # Step 1: Create or fetch Paystack Customer
    customer_url = "https://api.paystack.co/customer"
    name_parts = student_name.strip().split(" ", 1)
    first_name = name_parts[0]
    last_name = name_parts[1] if len(name_parts) > 1 else "Student"

    customer_payload = {
        "email": parent_email,
        "first_name": first_name,
        "last_name": last_name,
        "phone": parent_phone
    }

    try:
        cust_response = requests.post(customer_url, json=customer_payload, headers=HEADERS, timeout=10)
        cust_data = cust_response.json()

        if not cust_data.get("status"):
            print("❌ Paystack Customer Error:", cust_data.get("message"))
            return None

        customer_code = cust_data["data"]["customer_code"]

        # Step 2: Request Dedicated Virtual Account
        dva_url = "https://api.paystack.co/dedicated_account"
        dva_payload = {
            "customer": customer_code,
            "preferred_bank": "wema-bank" 
        }

        dva_response = requests.post(dva_url, json=dva_payload, headers=HEADERS, timeout=10)
        dva_data = dva_response.json()

        # --- FALLBACK FOR TEST MODE ---
        if not dva_data.get("status"):
            error_msg = dva_data.get("message", "")
            print(f"⚠️ Paystack DVA Error: {error_msg}")
            
            if "Dedicated NUBAN is not available" in error_msg or "test mode" in error_msg.lower():
                print("🔧 MOCKING VIRTUAL ACCOUNT FOR DEVELOPMENT PURPOSES...")
                # Generate a random 10-digit account number starting with 99
                mock_account = f"99{random.randint(10000000, 99999999)}"
                return {
                    "account_number": mock_account,
                    "bank_name": "Test Wema Bank",
                    "customer_code": customer_code
                }
            return None

        # Extract generated details for Live/Verified Accounts
        account_data = dva_data["data"]
        account_number = account_data["account_number"]
        bank_name = account_data["bank"]["name"]

        print(f"✅ Generated Account: {account_number} ({bank_name}) for {student_name}")
        return {
            "account_number": account_number,
            "bank_name": bank_name,
            "customer_code": customer_code
        }

    except Exception as e:
        print("❌ API Connection Error:", e)
        return None


if __name__ == "__main__":
    # Test with sample student data
    test_result = create_virtual_account(
        student_name="David Ogunleye",
        parent_email="parent_test@gmail.com",
        parent_phone="08012345678"
    )
    print("\nTest Result Output:", test_result)