import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY")

def generate_saas_invoice(school_name: str, admin_email: str, student_count: int, fee_per_student: int):
    """
    Calculates the per-student SaaS fee and generates a Paystack payment link.
    """
    print(f"🔄 Calculating subscription for {school_name}...")
    
    # 1. Calculate total (e.g., 350 students * ₦1,500 = ₦525,000)
    total_amount = student_count * fee_per_student
    
    # 2. Paystack requires the amount in kobo (lowest denomination)
    amount_in_kobo = total_amount * 100 

    url = "https://api.paystack.co/transaction/initialize"
    
    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json"
    }
    
    # 3. Configure the Paystack payload for NGN (until USD is activated on the dashboard)
    payload = {
        "email": admin_email,
        "amount": amount_in_kobo,
        "currency": "NGN", 
        "reference": f"saas_sub_{school_name.replace(' ', '_').lower()}_{student_count}",
        "callback_url": "http://localhost:8501" 
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        result = response.json()
        
        if result.get("status"):
            payment_url = result["data"]["authorization_url"]
            print(f"\n✅ SaaS Invoice generated successfully!")
            print(f"🏢 Client: {school_name}")
            print(f"💰 Total Due: ₦{total_amount:,} ({student_count} students @ ₦{fee_per_student:,}/student)")
            print(f"🔗 Send this secure payment link to the school admin:")
            print(f"👉 {payment_url}\n")
            return payment_url
        else:
            print(f"❌ Paystack Error: {result.get('message')}")
            return None
            
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return None

if __name__ == "__main__":
    print("🚀 Starting SaaS Per-Student Billing Engine...\n")
    
    generate_saas_invoice(
        school_name="Maypride Secondary School",
        admin_email="maypridenps2006@yahoo.co.uk",
        student_count=350, 
        fee_per_student=1500  # Adjusted to NGN 1,500 per student
    )