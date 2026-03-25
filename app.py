from dotenv import load_dotenv
import os
load_dotenv()
from flask import Flask, render_template, request, redirect, session, send_file
from pymongo import MongoClient
from bson.objectid import ObjectId
from bson.errors import InvalidId   # ✅ FIX ADDED
import qrcode
import os

# EMAIL
import smtplib
from email.message import EmailMessage

# PDF
from reportlab.platypus import SimpleDocTemplate, Paragraph, Image, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

app = Flask(__name__)
app.secret_key = "secret123"

# ---------------- DATABASE ----------------
client = MongoClient("mongodb://localhost:27017/")
db = client["concertDB"]
collection = db["bookings"]

# ---------------- ADMIN LOGIN ----------------
ADMIN_USER = "admin"
ADMIN_PASS = "1234"

# ---------------- EMAIL FUNCTION ----------------
def send_email(receiver_email, booking, qr_path):
    sender_email = os.getenv("EMAIL_USER")
    app_password = os.getenv("EMAIL_PASS")

    msg = EmailMessage()
    msg['Subject'] = "Your Concert Ticket Confirmation"
    msg['From'] = sender_email
    msg['To'] = receiver_email

    # ✅ CLEAN & SIMPLE EMAIL
    msg.add_alternative(f"""
    <html>
    <body style="margin:0; padding:0; font-family:Arial; background:#f4f4f4;">

    <div style="max-width:450px; margin:auto; background:white; padding:20px; border-radius:8px;">

        <h2 style="text-align:center; margin-bottom:5px;">🎤 Anirudh Live Concert</h2>
        <p style="text-align:center; color:#555; margin-top:0;">Booking Confirmation</p>

        <hr>

        <p><b>Name:</b> {booking['name']}</p>
        <p><b>Booking ID:</b> {booking.get('_id','')}</p>
        <p><b>Ticket Type:</b> {booking['ticket']}</p>
        <p><b>Seat:</b> {booking['seat']}</p>
        <p><b>Amount Paid:</b> ₹{booking['price']}</p>

        <hr>

        <p><b>Event Details:</b></p>
        <p>📍 Palace Grounds, Bengaluru</p>
        <p>⏰ 7:00 PM</p>

        <hr>

        <p style="font-size:13px; color:#555;">
        Your QR code is attached with this email. Please present it at entry.
        </p>

        <p style="font-size:12px; color:#888; text-align:center;">
        This is a system generated ticket. Do not share.
        </p>

    </div>

    </body>
    </html>
    """, subtype='html')

    # ATTACH QR
    with open(qr_path, 'rb') as f:
        msg.add_attachment(f.read(), maintype='image', subtype='png', filename='qr.png')

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(sender_email, app_password)
        smtp.send_message(msg)

# ---------------- HOME ----------------
@app.route("/")
def home():
    return render_template("index.html")

# ---------------- CHECKOUT ----------------
@app.route("/checkout", methods=["POST"])
def checkout():
    data = request.form

    booking = {
        "name": data["name"],
        "email": data["email"],
        "phone": data["phone"],
        "address": data["address"],
        "ticket": data["ticket"],
        "price": data["price"],
        "seat": data["seat"]
    }

    result = collection.insert_one(booking)
    booking_id = str(result.inserted_id)

    os.makedirs("static/qr_codes", exist_ok=True)

    ticket_url = request.host_url + "ticket/" + booking_id

    qr = qrcode.make(ticket_url)
    qr_path = f"static/qr_codes/{booking_id}.png"
    qr.save(qr_path)

    send_email(data["email"], booking, qr_path)

    return render_template("checkout.html", booking=booking, qr=qr_path)

# ---------------- TICKET PAGE (FIXED) ----------------
@app.route("/ticket/<id>")
def ticket(id):
    try:
        booking = collection.find_one({"_id": ObjectId(id)})
    except InvalidId:
        return "Invalid Ticket ID ❌"

    if not booking:
        return "Ticket Not Found ❌"

    return render_template("ticket.html", booking=booking)

# ---------------- PDF DOWNLOAD (FIXED) ----------------
@app.route("/download/<id>")
def download(id):
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from bson.errors import InvalidId

    try:
        booking = collection.find_one({"_id": ObjectId(id)})
    except InvalidId:
        return "Invalid Ticket ID ❌"

    if not booking:
        return "Ticket Not Found ❌"

    filename = f"ticket_{id}.pdf"

    # Delete old file
    if os.path.exists(filename):
        os.remove(filename)

    c = canvas.Canvas(filename, pagesize=A4)
    width, height = A4

    # 🔥 BACKGROUND IMAGE (FULL PAGE)
    bg_path = "static/anirudh_ticket.jpg"
    if os.path.exists(bg_path):
        c.drawImage(bg_path, 0, 0, width=width, height=height)

    # 🔥 DARK OVERLAY (for readability)
    c.setFillColorRGB(0, 0, 0, alpha=0.6)
    c.rect(0, 0, width, height, fill=1)

    # 🎟 CENTER TICKET CARD
    card_x = 80
    card_y = 150
    card_w = width - 160
    card_h = 450

    # GOLD BORDER
    c.setStrokeColorRGB(0.83, 0.69, 0.22)  # gold
    c.setLineWidth(3)
    c.setFillColorRGB(0.05, 0.05, 0.05)  # dark card
    c.roundRect(card_x, card_y, card_w, card_h, 20, fill=1)

    # TITLE
    c.setFillColorRGB(0.83, 0.69, 0.22)
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(width/2, card_y + card_h - 40, "ANIRUDH LIVE")

    # VIP TEXT
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(width/2, card_y + card_h - 70, "VIP ENTRY PASS")

    # EVENT DETAILS
    c.setFillColorRGB(1,1,1)
    c.setFont("Helvetica", 11)
    c.drawString(card_x + 30, card_y + card_h - 110, "Venue: Palace Grounds, Bengaluru")
    c.drawString(card_x + 30, card_y + card_h - 130, "Time: 7:00 PM")

    # USER DETAILS
    y = card_y + card_h - 180
    c.setFont("Helvetica-Bold", 12)

    details = [
        ("Booking ID", str(booking["_id"])),
        ("Name", booking["name"]),
        ("Ticket", booking["ticket"]),
        ("Seat", booking["seat"]),
        ("Amount", f"₹{booking['price']}"),
        ("Gate", "VIP Gate"),
        ("Valid Till", "10:30 PM")
    ]

    for label, value in details:
        c.drawString(card_x + 30, y, f"{label}:")
        c.drawRightString(card_x + card_w - 30, y, value)
        y -= 25

    # QR CODE
    qr_path = f"static/qr_codes/{id}.png"
    if os.path.exists(qr_path):
        c.drawImage(qr_path, width/2 - 60, card_y + 40, width=120, height=120)

    # FOOTER
    c.setFont("Helvetica", 10)
    c.drawCentredString(width/2, card_y + 20, "Scan at entry only • Do not share")

    c.save()

    return send_file(filename, as_attachment=True)
# ---------------- ADMIN LOGIN ----------------
@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        if request.form["username"] == ADMIN_USER and request.form["password"] == ADMIN_PASS:
            session["admin"] = True
            return redirect("/dashboard")
    return render_template("admin.html")

# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():
    if not session.get("admin"):
        return redirect("/admin")

    bookings = list(collection.find())
    return render_template("dashboard.html", bookings=bookings)

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect("/admin")

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)