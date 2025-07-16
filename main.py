import streamlit as st
import google.generativeai as genai
from dotenv import load_dotenv
from itinerary_utils import generate_pdf
import os
import re

# Load API keys
load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel(model_name="models/gemini-1.5-flash")

# Streamlit UI Setup
st.set_page_config(page_title="AI Tour Planner", page_icon="🌍", layout="centered")

# Simple Styling
st.markdown("""
    <style>
    html, body {
        margin: 0;
        padding: 0;
        height: 100%;
        background: radial-gradient(circle at top, #fceabb, #f8b500);
        font-family: 'Segoe UI', sans-serif;
    }

    .stApp {
        background: transparent;
    }

    .stButton > button {
        background: linear-gradient(to right, #ff6f00, #ffb74d);
        color: white;
        font-size: 17px;
        font-weight: 600;
        padding: 0.8rem 1.8rem;
        border: none;
        border-radius: 40px;
        margin-top: 1.8rem;
        box-shadow: 0 4px 14px rgba(0,0,0,0.2);
        transition: all 0.3s ease;
    }

    .stButton > button:hover {
        background: linear-gradient(to right, #ff9100, #ffc107);
        transform: translateY(-2px);
    }

    .stDownloadButton > button {
        background-color: #222;
        color: #fff;
        border: none;
        font-weight: bold;
        border-radius: 12px;
        padding: 0.7rem 1.4rem;
        margin-top: 1rem;
        transition: background 0.3s ease;
    }

    .stDownloadButton > button:hover {
        background-color: #444;
    }
    </style>
""", unsafe_allow_html=True)

# Title
st.markdown("<h1 style='text-align: center;'>🗺️ AI Tour Management Agent</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; font-size:18px;'>Plan your perfect trip with hotels, food, maps & QR — AI-powered!</p>", unsafe_allow_html=True)
st.markdown("---")

# Input Form
with st.form("trip_form"):
    route = st.text_input("📍 Travel Route (From → To)", placeholder="e.g., Hyderabad to Delhi to Agra")
    days = st.number_input("📅 Trip duration (in days)", min_value=1, step=1)
    interests = st.text_area("🎯 Interests / Activities", placeholder="e.g., adventure, temples, local food")
    budget = st.text_input("💰 Budget (optional)", placeholder="e.g., ₹30000 or $500")
    submitted = st.form_submit_button("✨ Generate Itinerary")

if submitted:
    with st.spinner("🧳 Planning your adventure..."):

        # Extract cities from "from to to" pattern
        city_list = [c.strip() for c in re.split(r"\s*to\s*", route, flags=re.IGNORECASE) if c.strip()]
        location_summary = " → ".join(city_list)

        # Gemini Prompt (includes low-budget hotel suggestion)
        if len(city_list) == 1:
            prompt = f"""
            Plan a {days}-day trip to {location_summary}.
            Interests: {interests}.
            Budget: {budget if budget else 'not specified'}.

            Please include:
            1. A brief destination overview
            2. A day-wise itinerary (Morning, Afternoon, Evening)
            3. 2–3 hotel recommendations (low-budget, mid-range, and luxury)
            4. 2–3 popular food or local eating places per day or per city
            5. Optional cultural tips or must-do experiences
            6. A final trip budget estimate
            """
        else:
            prompt = f"""
            Plan a {days}-day trip covering the following cities: {location_summary}.
            Interests: {interests}.
            Budget: {budget if budget else 'not specified'}.

            Instructions:
            1. Distribute days wisely between the cities
            2. Include travel transitions like "Travel from City A to City B in the evening"
            3. For each city:
                - Overview
                - 2–3 hotels (low-budget, mid-range, and luxury)
                - 2–3 food places (must-try local options)
            4. For each day:
                - Morning, Afternoon, Evening plan
                - Include eating spots where relevant
            5. Wrap up with a total estimated budget
            """

        # Generate itinerary using Gemini
        response = model.generate_content(prompt)
        itinerary = response.text

        st.success("🎉 Your customized itinerary is ready!")
        st.markdown("### 📝 Itinerary Plan")
        st.markdown(itinerary)

        # Extract destination for QR/map
        extracted_cities = re.findall(r"(?:Day \d+:|City:|in ) ([A-Z][a-zA-Z\s]+)", itinerary)
        unique_cities = list(dict.fromkeys([city.strip() for city in extracted_cities if city.strip()]))
        map_target = unique_cities[0] if unique_cities else city_list[0]

        # Generate downloadable PDF
        st.download_button(
            "📄 Download Itinerary as PDF",
            generate_pdf(itinerary, map_target),
            file_name="tour_itinerary.pdf"
        )
