import os
import re
import tempfile
import requests
from io import BytesIO
from dotenv import load_dotenv
from fpdf import FPDF
import qrcode
from geopy.geocoders import Nominatim

load_dotenv()

FONT_PATH = "DejaVuSans.ttf"

class PDF(FPDF):
    def __init__(self):
        super().__init__()
        self.add_font("DejaVu", "", FONT_PATH, uni=True)
        self.add_font("DejaVu", "B", FONT_PATH, uni=True)
        self.set_auto_page_break(auto=True, margin=15)

    def add_title_page(self, title, subtitle):
        self.add_page()
        self.set_font("DejaVu", "B", 22)
        self.cell(0, 20, title, ln=True, align="C")
        self.set_font("DejaVu", "", 14)
        self.cell(0, 10, subtitle, ln=True, align="C")
        self.ln(10)
        self.set_draw_color(200, 200, 200)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(10)

    def add_section(self, header, body):
        self.set_font("DejaVu", "B", 14)
        self.cell(0, 10, header, ln=True)
        self.set_font("DejaVu", "", 12)
        self.multi_cell(0, 8, body)
        self.ln(4)

    def insert_image(self, path, w=180):
        if os.path.exists(path):
            self.image(path, w=w)
            self.ln(5)

def clean_paragraphs(text):
    lines = text.splitlines()
    paragraphs = []
    current = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if current:
                paragraphs.append(" ".join(current))
                current = []
        elif stripped.startswith("*"):
            if current:
                paragraphs.append(" ".join(current))
                current = []
            paragraphs.append("• " + stripped.strip("* ").strip())
        else:
            current.append(stripped)
    if current:
        paragraphs.append(" ".join(current))
    return paragraphs

def extract_unique_cities(text):
    city_patterns = re.findall(r"(?:Day \d+:|in|to|from)\s+([A-Z][a-zA-Z\s]+)", text)
    cleaned = [c.strip().replace("–", "-") for c in city_patterns]
    return list(dict.fromkeys(cleaned))  # Remove duplicates

def fetch_osm_map(city):
    geolocator = Nominatim(user_agent="ai-tour-agent")
    location = geolocator.geocode(city)
    if not location:
        return None
    lat, lon = location.latitude, location.longitude
    key = os.getenv("LOCATIONIQ_API_KEY")
    if not key:
        return None
    map_url = f"https://maps.locationiq.com/v3/staticmap?key={key}&center={lat},{lon}&zoom=12&size=600x300&format=png"
    try:
        response = requests.get(map_url)
        if response.status_code == 200:
            temp_map = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
            temp_map.write(response.content)
            temp_map.close()
            return temp_map.name
    except requests.RequestException:
        return None
    return None

def generate_qr_code_route(city_list):
    if len(city_list) < 2:
        return None
    route = "+to+".join([c.replace(" ", "+") for c in city_list])
    url = f"https://www.google.com/maps/dir/{route}"
    qr_img = qrcode.make(url)
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    qr_img.save(temp.name)
    return temp.name

def generate_pdf(text, user_input_cities):
    pdf = PDF()
    pdf.set_font("DejaVu", size=12)

    title = "🗺️ AI Travel Itinerary"
    subtitle = f"For: {', '.join(user_input_cities)}"
    pdf.add_title_page(title, subtitle)

    # Parse sections from AI text
    paragraphs = clean_paragraphs(text)
    for para in paragraphs:
        lower = para.lower()
        if lower.startswith("day"):
            pdf.add_section(para, "")
        elif any(k in lower for k in ["overview", "budget", "estimate", "note"]):
            pdf.add_section(para.title(), "")
        else:
            pdf.set_font("DejaVu", "", 11)
            pdf.multi_cell(0, 7, para)
            pdf.ln(2)

    # Map Previews
    unique_cities = extract_unique_cities(text)
    for city in unique_cities:
        map_img = fetch_osm_map(city)
        if map_img:
            pdf.add_section(f"🗺️ Map Preview: {city}", "")
            pdf.insert_image(map_img)
            os.unlink(map_img)

    # QR Code for full route
    qr = generate_qr_code_route(user_input_cities)
    if qr:
        pdf.add_section("📍 Google Maps Route", "")
        pdf.insert_image(qr, w=80)
        os.unlink(qr)

    # Output
    buffer = BytesIO()
    pdf_output = pdf.output(dest="S")
    buffer.write(pdf_output)
    buffer.seek(0)
    return buffer
