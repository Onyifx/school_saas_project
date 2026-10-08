import requests
import time

# Target account assigned in database
TARGET_ACCOUNT = "9939184840" 

# Dynamic transaction reference to prevent duplicate database key errors
unique_ref = f"test_ref_{int(time.time())}"

mock_paystack_payload = {
    "event": "charge.success",
    "data": {
        "amount": 15000000,  # N150,000 in kobo
        "reference": unique_ref,
        "authorization": {
            "receiver_bank_account_number": TARGET_ACCOUNT
        }
    }
}

print(f"💸 Simulating parent transferring N150,000 (Ref: {unique_ref})...")
response = requests.post("http://localhost:8005/webhook/paystack", json=mock_paystack_payload)

print("Server Reply:", response.text)