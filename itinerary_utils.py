import os
import re
import tempfile
import requests
from io import BytesIO
from fpdf import FPDF
import qrcode
from geopy.geocoders import Nominatim
from dotenv import load_dotenv

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

    try:
        response = requests.get(map_url, timeout=5)
        response.raise_for_status()
        temp_map = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        temp_map.write(response.content)
        temp_map.close()
        return temp_map.name, (lat, lon)
    except:
        return None, (lat, lon)


def generate_qr_code(destination):
    url = f"https://www.google.com/maps/search/?api=1&query={destination.replace(' ', '+')}"
    qr_img = qrcode.make(url)
    temp_qr = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    qr_img.save(temp_qr.name)
    return temp_qr.name


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


class PDF(FPDF):
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=15)
        self.set_font("Helvetica", size=12)

    def chapter_title(self, title):
        self.set_font("Helvetica", "B", 12)
        safe_title = re.sub(r"[^\x00-\x7F]", "", title)  # Remove emojis
        self.cell(0, 10, safe_title.strip(), ln=True)
        self.ln(1)

    def chapter_body(self, body):
        self.set_font("Helvetica", "", 11)
        safe_body = re.sub(r"[^\x00-\x7F]", "", body)
        self.multi_cell(0, 8, safe_body.strip())
        self.ln()

    def insert_image(self, path, w=180):
        if os.path.exists(path):
            self.image(path, w=w)
            self.ln(5)


def generate_pdf(text, destination):
    pdf = PDF()
    pdf.add_page()

    paragraphs = clean_text(text)

    for para in paragraphs:
        lower = para.lower()
        if lower.startswith("day "):
            pdf.chapter_title(para.replace("**", "").strip())
        elif "destination overview" in lower:
            pdf.chapter_title("Destination Overview")
        elif "daily itinerary" in lower:
            pdf.chapter_title("Daily Itinerary")
        elif "budget estimate" in lower:
            pdf.chapter_title("Budget Estimate")
        elif "notes" in lower:
            pdf.chapter_title("Notes")
        elif para.strip().startswith("*"):
            pdf.chapter_body("• " + para.strip("* ").strip())
        else:
            pdf.chapter_body(para.strip())

    # Add Map
    map_path, _ = fetch_osm_map(destination)
    if map_path:
        pdf.chapter_title("Map Preview")
        pdf.insert_image(map_path)

    # Add QR Code
    qr_path = generate_qr_code(destination)
    if qr_path:
        pdf.chapter_title("Open in Google Maps")
        pdf.insert_image(qr_path, w=60)

    # Return PDF as BytesIO
    buffer = BytesIO()
    buffer.write(pdf.output(dest="S").encode("latin1"))
    buffer.seek(0)

    # Cleanup
    if map_path: os.unlink(map_path)
    if qr_path: os.unlink(qr_path)

    return buffer
