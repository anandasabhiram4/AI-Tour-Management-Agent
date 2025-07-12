import os
import re
import qrcode
import tempfile
import requests
from io import BytesIO
from PIL import Image
from geopy.geocoders import Nominatim
from dotenv import load_dotenv
from fpdf import FPDF
from fpdf.fonts import FontFace

load_dotenv()


def fetch_osm_map(destination):
    geolocator = Nominatim(user_agent="ai-tour-agent")
    location = geolocator.geocode(destination)

    if not location:
        return None, None

    lat, lon = location.latitude, location.longitude
    api_key = os.getenv("LOCATIONIQ_API_KEY")
    if not api_key:
        return None, (lat, lon)

    map_url = (
        f"https://maps.locationiq.com/v3/staticmap"
        f"?key={api_key}&center={lat},{lon}&zoom=13&size=600x300&format=png"
    )

    response = requests.get(map_url, timeout=5)
    if response.status_code == 200:
        temp_map = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        temp_map.write(response.content)
        temp_map.close()
        return temp_map.name, (lat, lon)

    return None, (lat, lon)


def generate_qr_code(destination):
    url = f"https://www.google.com/maps/search/?api=1&query={destination.replace(' ', '+')}"
    qr = qrcode.make(url)
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    qr.save(temp.name)
    return temp.name


def clean_text(text):
    lines = text.splitlines()
    merged = []
    current = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("*"):
            if current:
                merged.append(" ".join(current))
                current = []
            merged.append(stripped)
        elif stripped == "":
            if current:
                merged.append(" ".join(current))
                current = []
        else:
            current.append(stripped)

    if current:
        merged.append(" ".join(current))

    return merged


def generate_pdf(text, destination):
    pdf = FPDF(format="A4")
    pdf.add_page()

    # Set font (DejaVuSans.ttf must exist in root directory)
    font_path = "DejaVuSans.ttf"
    pdf.add_font("DejaVu", "", font_path, uni=True)
    pdf.set_font("DejaVu", "", 12)

    paragraphs = clean_text(text)

    for para in paragraphs:
        lower = para.lower()
        if lower.startswith("day "):
            pdf.set_font("DejaVu", "", 12)
            pdf.cell(0, 10, "📅 " + para.strip("**").strip(), ln=True)
        elif "destination overview" in lower:
            pdf.set_font("DejaVu", "", 12)
            pdf.cell(0, 10, "📍 Destination Overview", ln=True)
        elif "daily itinerary" in lower:
            pdf.set_font("DejaVu", "", 12)
            pdf.cell(0, 10, "🗓️ Daily Itinerary", ln=True)
        elif "budget estimate" in lower:
            pdf.set_font("DejaVu", "", 12)
            pdf.cell(0, 10, "💰 Budget Estimate", ln=True)
        elif "notes" in lower:
            pdf.set_font("DejaVu", "", 12)
            pdf.cell(0, 10, "📝 Notes", ln=True)
        elif para.strip().startswith("*"):
            pdf.set_font("DejaVu", "", 11)
            pdf.multi_cell(0, 8, "• " + para.strip("* ").strip())
        else:
            pdf.set_font("DejaVu", "", 11)
            pdf.multi_cell(0, 8, para.strip())

    # Add map
    map_path, _ = fetch_osm_map(destination)
    if map_path:
        pdf.set_font("DejaVu", "", 12)
        pdf.cell(0, 10, "🗺️ Map Preview", ln=True)
        pdf.image(map_path, w=180)
        os.unlink(map_path)

    # Add QR code
    qr_path = generate_qr_code(destination)
    if qr_path:
        pdf.set_font("DejaVu", "", 12)
        pdf.cell(0, 10, "📱 Open in Google Maps", ln=True)
        pdf.image(qr_path, w=60)
        os.unlink(qr_path)

    # Return as in-memory buffer
    buffer = BytesIO()
    buffer.write(pdf.output(dest="S").encode("latin1"))
    buffer.seek(0)
    return buffer
