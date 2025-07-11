import os
import requests
from io import BytesIO
from dotenv import load_dotenv

load_dotenv()

def fetch_osm_map(destination):
    api_key = os.getenv("LOCATIONIQ_API_KEY")
    if not api_key:
        return None

    # 1. Geocode the destination name to lat/lon
    geocode_url = f"https://us1.locationiq.com/v1/search.php?key={api_key}&q={destination}&format=json"
    try:
        geocode_resp = requests.get(geocode_url)
        geocode_resp.raise_for_status()
    except requests.exceptions.RequestException:
        return None

    try:
        data = geocode_resp.json()
        lat = data[0]["lat"]
        lon = data[0]["lon"]
    except (KeyError, IndexError, ValueError):
        return None

    # 2. Get the static map using lat/lon
    map_url = (
        f"https://maps.locationiq.com/v3/staticmap"
        f"?key={api_key}&center={lat},{lon}&zoom=13&size=600x300&format=png"
    )

    try:
        map_resp = requests.get(map_url)
        map_resp.raise_for_status()
        img_bytes = BytesIO(map_resp.content)
        img_bytes.seek(0)
        return img_bytes
    except requests.exceptions.RequestException:
        return None
from fpdf import FPDF
from io import BytesIO
from matplotlib import font_manager
import re
import qrcode
from PIL import Image
import requests
from geopy.geocoders import Nominatim
import tempfile
import os
from dotenv import load_dotenv

load_dotenv()


class PDF(FPDF):
    def __init__(self):
        super().__init__()
        # Load system-safe fonts (regular + bold)
        regular_path = font_manager.findfont("DejaVu Sans")
        bold_path = font_manager.findfont("DejaVu Sans:bold")

        self.add_font("DejaVu", "", regular_path, uni=True)
        self.add_font("DejaVu", "B", bold_path, uni=True)

        self.set_font("DejaVu", "", 12)
        self.set_auto_page_break(auto=True, margin=15)

    def chapter_title(self, title):
        self.set_font("DejaVu", "B", 12)
        self.cell(0, 10, title.strip(), ln=True)
        self.ln(1)

    def chapter_body(self, body):
        self.set_font("DejaVu", "", 11)
        self.multi_cell(0, 8, body.strip())
        self.ln()

    def insert_image(self, path, w=180):
        if os.path.exists(path):
            self.image(path, w=w)
            self.ln(5)


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


def fetch_osm_map(destination):
    geolocator = Nominatim(user_agent="ai-tour-agent")
    location = geolocator.geocode(destination)

    if not location:
        return None, None

    lat, lon = location.latitude, location.longitude
    api_key = os.getenv("LOCATIONIQ_API_KEY")
    if not api_key:
        return None, (lat, lon)

    # LocationIQ Static Map URL
    map_url = (
        f"https://maps.locationiq.com/v3/staticmap"
        f"?key={api_key}&center={lat},{lon}&zoom=13&size=600x300&format=png"
    )

    response = requests.get(map_url)
    if response.status_code == 200:
        temp_map = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        temp_map.write(response.content)
        temp_map.close()
        return temp_map.name, (lat, lon)

    return None, (lat, lon)


def generate_qr_code(destination):
    google_maps_url = f"https://www.google.com/maps/search/?api=1&query={destination.replace(' ', '+')}"
    qr_img = qrcode.make(google_maps_url)
    temp_qr = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    qr_img.save(temp_qr.name)
    return temp_qr.name


def generate_pdf(text, destination):
    pdf = PDF()
    pdf.add_page()

    paragraphs = clean_text(text)

    for para in paragraphs:
        lower = para.lower()
        if lower.startswith("day "):
            pdf.chapter_title("📅 " + para.replace("**", "").strip())
        elif "destination overview" in lower:
            pdf.chapter_title("📍 Destination Overview")
        elif "daily itinerary" in lower:
            pdf.chapter_title("🗓️ Daily Itinerary")
        elif "budget estimate" in lower:
            pdf.chapter_title("💰 Budget Estimate")
        elif "notes" in lower:
            pdf.chapter_title("📝 Notes")
        elif para.strip().startswith("*"):
            pdf.chapter_body("• " + para.strip("* ").strip())
        else:
            pdf.chapter_body(para.strip())

    # Add Static Map from LocationIQ
    map_path, coords = fetch_osm_map(destination)
    if map_path:
        pdf.chapter_title("🗺️ Map Preview")
        pdf.insert_image(map_path)

    # Add QR Code to Google Maps
    qr_path = generate_qr_code(destination)
    if qr_path:
        pdf.chapter_title("📱 Open in Google Maps")
        pdf.insert_image(qr_path, w=60)

    # Output PDF
    buffer = BytesIO()
    pdf.output(buffer)
    buffer.seek(0)

    # Cleanup temp files
    if map_path: os.unlink(map_path)
    if qr_path: os.unlink(qr_path)

    return buffer
