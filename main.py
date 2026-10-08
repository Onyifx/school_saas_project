from fastapi import FastAPI, Request, HTTPException
import uvicorn
from database import record_payment_in_db, supabase
from notifications import generate_pdf_receipt, send_discord_notification

app = FastAPI(title="School SaaS Webhook Listener")

@app.get("/")
def read_root():
    return {"status": "Online", "message": "School SaaS API is running."}

@app.post("/paystack-webhook")
@app.post("/webhook/paystack")
async def paystack_webhook(request: Request):
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event_type = payload.get("event")

    if event_type == "charge.success":
        try:
            data = payload.get("data", {})
            
            amount_in_kobo = data.get("amount", 0)
            amount_paid = amount_in_kobo / 100  
            reference = data.get("reference")
            
            authorization = data.get("authorization", {})
            account_number = authorization.get("receiver_bank_account_number")

            if not account_number:
                return {"status": "ignored", "message": "Not a virtual account payment"}

            print(f"\n🔔 WEBHOOK ALERT: N{amount_paid} received in account {account_number}")

            # 1. Record payment in database
            record_payment_in_db(account_number=account_number, amount_paid=amount_paid, reference=reference)

            # 2. Lookup student name safely
            student_res = supabase.table("students").select("student_name").eq("account_number", account_number).execute()
            student_name = student_res.data[0]["student_name"] if (student_res.data and len(student_res.data) > 0) else "Student"

            # 3. Generate PDF Receipt
            generate_pdf_receipt(student_name=student_name, amount_paid=amount_paid, reference=reference)

            # 4. Send Instant Alert
            send_discord_notification(student_name=student_name, amount_paid=amount_paid, reference=reference)

            return {"status": "success", "message": "Payment recorded, receipt generated, alert sent"}

        except Exception as e:
            print(f"❌ Webhook Processing Error: {e}")
            return {"status": "error", "detail": str(e)}

    return {"status": "ignored", "message": "Unhandled event type"}

if __name__ == "__main__":
    print("🚀 Starting Webhook Server on port 8005...")
    uvicorn.run("main:app", host="0.0.0.0", port=8005, reload=True)