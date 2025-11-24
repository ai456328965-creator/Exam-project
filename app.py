import streamlit as st
from ultralytics import YOLO
import google.generativeai as genai
from gtts import gTTS
import tempfile
import os
import time
from streamlit_webrtc import webrtc_streamer, VideoTransformerBase, RTCConfiguration

# -------------------------------
# 🔐 Gemini API Key
# -------------------------------
API_KEY = "AIzaSyDrGWv-nruXtcfcph-XhT7kCkpxsqBHYps"  # Keep hidden
genai.configure(api_key=API_KEY)
gemini_model = genai.GenerativeModel("gemini-2.0-flash")

# -------------------------------
# Streamlit Page
# -------------------------------
st.set_page_config(page_title="YOLO + Gemini Voice", layout="wide")
st.markdown(
    "<h2 style='text-align:center;'>📷 YOLO Real-Time Detection with Auto Voice (Gemini)</h2>",
    unsafe_allow_html=True
)

# -------------------------------
# Load YOLO Model
# -------------------------------
@st.cache_resource
def load_model():
    return YOLO("best.pt")

model = load_model()

# -------------------------------
# Gemini Text Generator
# -------------------------------
def get_gemini_text(obj_name):
    prompt = f"This is a {obj_name}. Tell the user politely to remove it."
    reply = gemini_model.generate_content(prompt)
    return reply.text.strip()

# -------------------------------
# Auto Speaker
# -------------------------------
def speak(text):
    tts = gTTS(text=text, lang="en")
    path = os.path.join(tempfile.gettempdir(), "voice.mp3")
    tts.save(path)
    st.audio(path, autoplay=True)

# -------------------------------
# Video Transformer for YOLO Detection
# -------------------------------
class YOLOTransformer(VideoTransformerBase):
    def __init__(self):
        self.last_spoken = ""
        self.speak_delay = 2  # seconds

    def transform(self, frame):
        import numpy as np
        img = frame.to_ndarray(format="bgr24")  # frame in BGR

        # YOLO Prediction
        results = model.predict(img, conf=0.5, verbose=False)

        detected = []
        for box in results[0].boxes:
            cls = int(box.cls[0])
            class_name = model.names[cls]
            detected.append(class_name)

            # Draw rectangle
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            import cv2  # only for drawing, optional
            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(img, class_name, (x1, y1-10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)

        # Auto speak
        if detected:
            obj = detected[0]
            if obj != self.last_spoken:
                message = get_gemini_text(obj)
                speak(message)
                self.last_spoken = obj
                time.sleep(self.speak_delay)

        return img

# -------------------------------
# Start Webcam
# -------------------------------
RTC_CONFIGURATION = RTCConfiguration({"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]})
webrtc_streamer(key="yolo", video_transformer_factory=YOLOTransformer, rtc_configuration=RTC_CONFIGURATION)
