from flask import Flask, render_template, request, send_file
from pymongo import MongoClient
from bson.objectid import ObjectId
import qrcode
import os

from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

app = Flask(__name__)

# MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["concertDB"]
collection = db["bookings"]

# ---------------- HOME ----------------
@app.route("/")
def home():
    return render_template("index.html")

# ---------------- BOOKING + QR ----------------
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

    # 🔥 IMPORTANT (auto ngrok URL)
    ticket_url = request.host_url + "ticket/" + booking_id

    qr = qrcode.make(ticket_url)
    qr_path = f"static/qr_codes/{booking_id}.png"
    qr.save(qr_path)

    return render_template("checkout.html", booking=booking, qr=qr_path)

# ---------------- TICKET ----------------
@app.route("/ticket/<id>")
def ticket(id):
    booking = collection.find_one({"_id": ObjectId(id)})
    return render_template("ticket.html", booking=booking)

# ---------------- DOWNLOAD PDF ----------------
@app.route("/download/<id>")
def download(id):
    booking = collection.find_one({"_id": ObjectId(id)})

    filename = f"ticket_{id}.pdf"
    doc = SimpleDocTemplate(filename)

    styles = getSampleStyleSheet()

    content = []
    content.append(Paragraph(f"Name: {booking['name']}", styles["Normal"]))
    content.append(Paragraph(f"Ticket: {booking['ticket']}", styles["Normal"]))
    content.append(Paragraph(f"Seat: {booking['seat']}", styles["Normal"]))
    content.append(Paragraph(f"Price: ₹{booking['price']}", styles["Normal"]))

    doc.build(content)

    return send_file(filename, as_attachment=True)

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)