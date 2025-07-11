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

# Premium Web-Style UI
st.markdown("""
    <style>
    /* Remove default Streamlit block container padding & shadows */
section.main > div {
    padding: 0 !important;
    box-shadow: none !important;
    border: none !important;
    background: transparent !important;
}

/* Remove white background or border inside st-form */
.stForm {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}

/* Remove background from result text block */
.stMarkdown {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}

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

    h1.hero-title {
        font-size: 48px;
        text-align: center;
        color: #ffffff;
        margin-top: 2rem;
        font-weight: 800;
        text-shadow: 2px 4px 12px rgba(0,0,0,0.3);
    }

    p.hero-subtitle {
        text-align: center;
        font-size: 20px;
        color: #fff9f0;
        margin-top: -0.8rem;
        margin-bottom: 2rem;
        font-weight: 400;
    }

    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }

    .stTextInput > div > div > input,
    .stTextArea textarea,
    .stNumberInput input {
        background-color: #ffffffcc;
        padding: 0.9rem;
        border-radius: 12px;
        border: 1px solid #ccc;
        font-size: 16px;
        transition: box-shadow 0.3s ease;
    }

    .stTextInput > div > div > input:focus,
    .stTextArea textarea:focus,
    .stNumberInput input:focus {
        box-shadow: 0 0 0 2px #ff6f00;
        border: 1px solid #ff6f00;
    }

    .stTextInput label, .stNumberInput label, .stTextArea label {
        font-weight: bold;
        font-size: 15px;
        color: #222;
        margin-bottom: 0.5rem;
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

    h3 {
        font-size: 20px;
        margin-top: 1rem;
        color: #333;
        font-weight: 600;
    }
    </style>
""", unsafe_allow_html=True)


# Title
st.markdown("<h1 style='text-align: center;'>🗺️ AI Tour Management Agent</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; font-size:18px;'>Plan your perfect trip with hotels, food, maps & QR — AI-powered!</p>", unsafe_allow_html=True)
st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)


# Input Form
with st.form("trip_form"):
    cities = st.text_input("📍 Destination(s)", placeholder="e.g., Manali or Delhi, Agra, Jaipur")
    days = st.number_input("📅 Trip duration (in days)", min_value=1, step=1)
    interests = st.text_area("🎯 Interests / Activities", placeholder="e.g., adventure, temples, local food")
    budget = st.text_input("💰 Budget (optional)", placeholder="e.g., ₹30000 or $500")
    submitted = st.form_submit_button("✨ Generate Itinerary")

if submitted:
    with st.spinner("🧳 Planning your adventure..."):

        city_list = [city.strip() for city in cities.split(",") if city.strip()]
        location_summary = ", ".join(city_list)

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

        # Extract actual city/cities from Gemini response
        extracted_cities = re.findall(r"(?:Day \d+:|City:|in ) ([A-Z][a-zA-Z\s]+)", itinerary)
        unique_cities = list(dict.fromkeys([city.strip() for city in extracted_cities if city.strip()]))
        map_target = unique_cities[0] if unique_cities else city_list[0]

        # Generate downloadable PDF using extracted destination
        st.download_button(
            "📄 Download Itinerary as PDF",
            generate_pdf(itinerary, map_target),
            file_name="tour_itinerary.pdf"
        )
