%pip install opencv-python-headless
import streamlit as st
import cv2
from ultralytics import YOLO
import google.generativeai as genai
from gtts import gTTS
import tempfile
import os
import time

# --------------------------------------------------
# 🔐 Your API key is stored internally (NOT SHOWN IN UI)
# --------------------------------------------------
API_KEY = "AIzaSyDrGWv-nruXtcfcph-XhT7kCkpxsqBHYps"   # <-- Your key stays hidden

# Configure Gemini
genai.configure(api_key=API_KEY)
gemini_model = genai.GenerativeModel("gemini-2.0-flash")

# --------------------------------------------------
# Streamlit Page Settings
# --------------------------------------------------
st.set_page_config(page_title="YOLO + Gemini Voice", layout="wide")
st.markdown("<h2 style='text-align:center;'>📷 YOLO Real-Time Detection with Auto Voice (Gemini)</h2>", unsafe_allow_html=True)

# --------------------------------------------------
# Load YOLO Model
# --------------------------------------------------
@st.cache_resource
def load_model():
    return YOLO("best.pt")

model = load_model()

# --------------------------------------------------
# Gemini Text Generator
# --------------------------------------------------
def get_gemini_text(obj_name):
    prompt = f"This is a {obj_name}. Tell the user politely to remove it."
    reply = gemini_model.generate_content(prompt)
    return reply.text.strip()

# --------------------------------------------------
# Auto Speaker
# --------------------------------------------------
def speak(text):
    tts = gTTS(text=text, lang="en")
    path = os.path.join(tempfile.gettempdir(), "voice.mp3")
    tts.save(path)
    st.audio(path, autoplay=True)

# --------------------------------------------------
# CAMERA BUTTON
# --------------------------------------------------
start_camera = st.button("🎥 Start Camera")

frame_placeholder = st.empty()
last_spoken = ""
speak_delay = 2  # seconds

# --------------------------------------------------
# CAMERA LOOP
# --------------------------------------------------
if start_camera:

    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        st.error("❌ Camera not found.")
        st.stop()

    st.success("✅ Camera Started")

    while True:
        ret, frame = cap.read()
        if not ret:
            st.error("❌ Could not read from camera.")
            break

        # YOLO Prediction
        results = model.predict(frame, conf=0.5, verbose=False)

        detected = []

        for box in results[0].boxes:
            cls = int(box.cls[0])
            class_name = model.names[cls]
            detected.append(class_name)

            # Draw box on frame
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0,255,0), 2)
            cv2.putText(frame, class_name, (x1, y1-10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)

        # Show frame on the page
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_placeholder.image(frame_rgb, channels="RGB")

        # If object detected → auto speak
        if detected:
            obj = detected[0]
            if obj != last_spoken:
                message = get_gemini_text(obj)
                speak(message)
                last_spoken = obj
                time.sleep(speak_delay)

        # If Streamlit stops → exit loop
        if not st.session_state.get("run", True):
            break

    cap.release()
    st.stop()
