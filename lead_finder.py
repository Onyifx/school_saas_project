import os
import re
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from database import supabase

load_dotenv()

# Environment Variables
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SENDER_NAME = os.getenv("SENDER_NAME", "School Fees SaaS")

# Sample search queries targeting Nigerian private schools
SEARCH_QUERIES = [
    "private secondary schools in Lagos contact email phone address",
    "private primary schools in Enugu contact email phone address",
    "top private schools in Abuja contact email phone address",
    "private schools in Port Harcourt contact email phone address",
    "private schools in Ibadan contact email phone address"
]

def send_smtp_email(target_email: str, school_name: str) -> bool:
    """Sends a professional B2B cold email pitch to the school."""
    if not SMTP_USER or not SMTP_PASSWORD:
        print("⚠️ SMTP credentials missing in .env. Skipping email dispatch.")
        return False

    try:
        msg = MIMEMultipart()
        msg['From'] = f"{SENDER_NAME} <{SMTP_USER}>"
        msg['To'] = target_email
        msg['Subject'] = f"Eliminate Unidentified Bank Transfers at {school_name}"

        body = f"""Hello Management Team at {school_name},

We help private primary and secondary schools across Nigeria completely eliminate the frustration of 'unidentified bank transfers' during fee collection terms.

Our Automated Dedicated Virtual Account (DVA) system:
1. Assigns a permanent, unique virtual account number to each student.
2. Instantly reconciles every transfer made by parents in real-time.
3. Automatically generates PDF receipts and sends instant alerts to administrators.

Would you be open to a quick 5-minute demonstration or physical presentation at your office this week?

Best regards,
Automated School Fees Reconciliation Team
Phone: +234 800 000 0000
"""
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        print(f"📧 Cold email pitch successfully sent to {target_email} ({school_name})")
        return True
    except Exception as e:
        print(f"❌ Failed to send SMTP email to {target_email}: {e}")
        return False

def send_discord_lead_alert(school_name: str, email: str, whatsapp: str, calling: str, address: str, emailed: bool):
    """Sends a detailed lead card to Discord for manual phone/physical follow-ups."""
    if not DISCORD_WEBHOOK_URL:
        print("⚠️ Discord Webhook URL missing.")
        return

    status_text = "✅ Pitched via SMTP Email" if emailed else "⚠️ Email Missing / Pitch Pending"

    payload = {
        "username": "School Lead Finder Bot",
        "avatar_url": "https://cdn-icons-png.flaticon.com/512/3135/3135715.png",
        "embeds": [
            {
                "title": f"🏫 New Private School Lead: {school_name}",
                "color": 3066993,  # Emerald Green
                "fields": [
                    {"name": "📧 Email Address", "value": email if email else "Not Listed", "inline": True},
                    {"name": "💬 WhatsApp Number", "value": whatsapp if whatsapp else "Not Specified", "inline": True},
                    {"name": "📞 Calling / Office Line", "value": calling if calling else "Not Specified", "inline": True},
                    {"name": "📍 Physical Address", "value": address if address else "Not Listed", "inline": False},
                    {"name": "🚀 Pitch Status", "value": status_text, "inline": False}
                ],
                "footer": {"text": "Targeting Private Primary & Secondary Schools in Nigeria"}
            }
        ]
    }

    try:
        requests.post(DISCORD_WEBHOOK_URL, json=payload)
        print(f"🔔 Lead card for '{school_name}' routed to Discord.")
    except Exception as e:
        print(f"❌ Discord Lead Alert Failed: {e}")

def parse_contact_details(text: str):
    """Extracts email, categorizes phone numbers, and locates physical address."""
    # 1. Extract Email
    emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
    email = emails[0] if emails else ""

    # 2. Extract Nigerian Phone Numbers
    phone_pattern = r'(?:\+?234|0)[789][01]\d{8}'
    phones = re.findall(phone_pattern, text)
    phones = list(set(phones))  # Deduplicate

    whatsapp_num = ""
    calling_num = ""

    for phone in phones:
        # Check context around the phone number for WhatsApp indicators
        phone_index = text.find(phone)
        context = text[max(0, phone_index - 50): min(len(text), phone_index + 50)].lower()
        
        if "whatsapp" in context or "chat" in context or "wa.me" in context:
            if not whatsapp_num:
                whatsapp_num = phone
        else:
            if not calling_num:
                calling_num = phone

    if phones and not whatsapp_num and not calling_num:
        calling_num = phones[0]

    # 3. Extract Physical Address (Looks for street/road/location keywords)
    address = ""
    lines = text.split('\n')
    for line in lines:
        line_clean = line.strip()
        if any(keyword in line_clean.lower() for keyword in ["street", "road", "close", "avenue", "plot", "state", "lagos", "enugu", "abuja"]):
            if len(line_clean) > 15 and len(line_clean) < 150:
                address = line_clean
                break

    return email, whatsapp_num, calling_num, address

def search_and_process_leads():
    """Scrapes search results and processes new school leads."""
    print("\n🔍 Running Hourly School Lead Finder Engine...")
    
    # Simple Web Scraper targeting school listings
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    for query in SEARCH_QUERIES:
        print(f"🔎 Querying: '{query}'")
        url = f"https://html.duckduckgo.com/html/?q={query.replace(' ', '+')}"
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, "html.parser")
            results = soup.find_all("a", class_="result__snippet")

            for result in results[:3]:  # Process top 3 results per query
                text_content = result.get_text()
                
                # Simple extraction of school name from result snippet
                words = text_content.split()
                if len(words) < 5:
                    continue
                
                school_name = " ".join(words[:4]).replace("...", "").strip()
                if not school_name or len(school_name) < 3:
                    continue

                # Check if school already exists in database
                existing = supabase.table("leads").select("id").eq("school_name", school_name).execute()
                if existing.data and len(existing.data) > 0:
                    print(f"⏩ School '{school_name}' already processed. Skipping.")
                    continue

                # Parse details
                email, whatsapp, calling, address = parse_contact_details(text_content)

                # Fallback values if snippet lacks full contact info
                if not email and not calling and not address:
                    continue

                # Pitch via SMTP if email exists
                email_pitched = False
                if email:
                    email_pitched = send_smtp_email(target_email=email, school_name=school_name)

                # Record Lead in Supabase
                supabase.table("leads").insert({
                    "school_name": school_name,
                    "email": email,
                    "whatsapp_number": whatsapp,
                    "calling_number": calling,
                    "physical_address": address,
                    "email_pitched": email_pitched
                }).execute()

                # Alert Discord with Lead Details
                send_discord_lead_alert(
                    school_name=school_name,
                    email=email,
                    whatsapp=whatsapp,
                    calling=calling,
                    address=address,
                    emailed=email_pitched
                )

                time.sleep(2)  # Respectful pause between operations

        except Exception as e:
            print(f"❌ Error during lead query '{query}': {e}")

if __name__ == "__main__":
    # Runs continuously every 3600 seconds (1 hour)
    print("🚀 School Lead Finder Background Service Started!")
    while True:
        search_and_process_leads()
        print("⏰ Execution finished. Waiting 1 hour for the next run...")
        time.sleep(3600)