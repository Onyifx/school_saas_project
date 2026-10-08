import os
import requests
from dotenv import load_dotenv
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# Load environment variables
load_dotenv()

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

def generate_pdf_receipt(student_name: str, amount_paid: float, reference: str):
    """
    Generates an official PDF receipt using ReportLab.
    """
    filename = f"receipt_{reference}.pdf"
    c = canvas.Canvas(filename, pagesize=letter)
    
    # Header
    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, 750, "OFFICIAL SCHOOL FEES RECEIPT")
    c.setLineWidth(1)
    c.line(50, 740, 550, 740)
    
    # Details
    c.setFont("Helvetica", 12)
    c.drawString(50, 700, f"Student Name:      {student_name}")
    c.drawString(50, 675, f"Amount Paid:       N{amount_paid:,.2f}")
    c.drawString(50, 650, f"Payment Reference: {reference}")
    c.drawString(50, 625, "Payment Status:    FULLY CLEARED / SUCCESS")
    
    # Footer
    c.line(50, 590, 550, 590)
    c.setFont("Helvetica-Oblique", 10)
    c.drawString(50, 570, "Thank you for your payment. This is a computer-generated receipt.")
    
    c.save()
    print(f"📄 PDF Receipt generated successfully: {filename}")
    return filename


def send_discord_notification(student_name: str, amount_paid: float, reference: str):
    """
    Sends a real-time execution report to your private Discord channel.
    """
    if not DISCORD_WEBHOOK_URL:
        print("⚠️ DISCORD_WEBHOOK_URL not set in .env. Skipping phone alert.")
        return

    payload = {
        "embeds": [{
            "title": "💰 School Fee Payment Confirmed!",
            "description": f"**Student:** {student_name}\n**Amount:** ₦{amount_paid:,.2f}\n**Ref:** `{reference}`",
            "color": 3066993  # Green
        }]
    }
    
    try:
        requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=5)
        print("📱 Notification alert sent!")
    except Exception as e:
        print("❌ Discord Notification Error:", e)


if __name__ == "__main__":
    # Test generating a receipt manually
    generate_pdf_receipt("Emeka Okonkwo", 150000.00, "test_ref_12345ABC")