import os
import requests
import re
import qrcode
import tempfile
from io import BytesIO
from fpdf import FPDF
from geopy.geocoders import Nominatim
from dotenv import load_dotenv

load_dotenv()

INVALID_MAP_KEYWORDS = [
    "arrival", "departure", "return", "home", "back", "stay", "rest", "break",
    "relax", "travel", "journey", "checkout", "overnight", "hotel"
]

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


def extract_unique_cities(text):
    pattern = r"(?:Day \d+:|City:|in |to )([A-Z][a-zA-Z\s]+)"
    found = re.findall(pattern, text)
    cleaned = [c.strip().lower() for c in found]
    filtered = [c for c in cleaned if all(k not in c for k in INVALID_MAP_KEYWORDS)]
    return list(dict.fromkeys(filtered))  # Remove duplicates


def fetch_osm_map(city_name):
    geolocator = Nominatim(user_agent="ai-tour-agent")
    location = geolocator.geocode(city_name)
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
        if response.status_code == 200:
            temp_map = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
            temp_map.write(response.content)
            temp_map.close()
            return temp_map.name, (lat, lon)
    except Exception:
        return None, (lat, lon)
    return None, (lat, lon)


def generate_qr_code(city_name):
    query = city_name.replace(" ", "+")
    url = f"https://www.google.com/maps/search/?api=1&query={query}"
    qr_img = qrcode.make(url)
    temp_qr = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    qr_img.save(temp_qr.name)
    return temp_qr.name


class PDF(FPDF):
    def __init__(self):
        super().__init__()
        self.add_font("DejaVu", "", "DejaVuSans.ttf", uni=True)
        self.add_font("DejaVu", "B", "DejaVuSans-Bold.ttf", uni=True)
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


def generate_pdf(text, destination_input):
    pdf = PDF()
    pdf.add_page()
    paragraphs = clean_text(text)

    for para in paragraphs:
        lower = para.lower()
        if lower.startswith("day "):
            pdf.chapter_title("📅 " + para.strip("**").strip())
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
            pdf.chapter_body(para)

    # Add maps and QR for each city
    cities = extract_unique_cities(text)
    for city in cities:
        map_path, _ = fetch_osm_map(city)
        if map_path:
            pdf.chapter_title(f"🗺️ Map Preview: {city.title()}")
            pdf.insert_image(map_path)
            os.unlink(map_path)
        qr_path = generate_qr_code(city)
        if qr_path:
            pdf.chapter_title(f"📱 Google Maps: {city.title()}")
            pdf.insert_image(qr_path, w=60)
            os.unlink(qr_path)

    buffer = BytesIO()
    pdf_output = pdf.output(dest="S")
    buffer.write(pdf_output)
    buffer.seek(0)
    return buffer
