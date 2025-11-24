import streamlit as st
from ultralytics import YOLO
import google.generativeai as genai
from gtts import gTTS
import tempfile
import os
import time
import av
import queue
from streamlit_webrtc import webrtc_streamer, VideoProcessorBase, RTCConfiguration

# --------------------------------------------------
# 🔐 Gemini API Key
# --------------------------------------------------
API_KEY = "AIzaSyDrGWv-nruXtcfcph-XhT7kCkpxsqBHYps"
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
    try:
        reply = gemini_model.generate_content(prompt)
        return reply.text.strip()
    except Exception as e:
        return f"Please remove the {obj_name}."

# --------------------------------------------------
# Auto Speaker
# --------------------------------------------------
def speak(text):
    try:
        tts = gTTS(text=text, lang="en")
        path = os.path.join(tempfile.gettempdir(), "voice.mp3")
        tts.save(path)
        # Use HTML audio with autoplay
        st.markdown(f"""
        <audio autoplay>
            <source src="{path}" type="audio/mpeg">
        </audio>
        """, unsafe_allow_html=True)
    except Exception as e:
        st.warning(f"Audio error: {e}")

# --------------------------------------------------
# Video Processor for YOLO
# --------------------------------------------------
class YOLOVideoProcessor(VideoProcessorBase):
    def __init__(self):
        self.last_spoken = ""
        self.speak_delay = 5  # seconds
        self.last_speak_time = 0
        self.detection_queue = queue.Queue()

    def recv(self, frame):
        img = frame.to_ndarray(format="bgr24")
        
        # YOLO Prediction
        results = model.predict(img, conf=0.5, verbose=False)
        
        detected = []
        for box in results[0].boxes:
            cls = int(box.cls[0])
            class_name = model.names[cls]
            detected.append(class_name)
            
            # Draw bounding box
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            import cv2
            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(img, class_name, (x1, y1-10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # Handle speech in main thread
        if detected:
            current_time = time.time()
            obj = detected[0]
            if (obj != self.last_spoken and 
                current_time - self.last_speak_time > self.speak_delay):
                self.detection_queue.put(obj)
                self.last_spoken = obj
                self.last_speak_time = current_time
        
        return av.VideoFrame.from_ndarray(img, format="bgr24")

# --------------------------------------------------
# RTC Configuration
# --------------------------------------------------
RTC_CONFIGURATION = RTCConfiguration({
    "iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]
})

# --------------------------------------------------
# Main App
# --------------------------------------------------
st.info("🔴 Click 'START' below to begin live camera detection")

# Initialize session state
if 'processor' not in st.session_state:
    st.session_state.processor = None
if 'last_spoken' not in st.session_state:
    st.session_state.last_spoken = ""
if 'last_speak_time' not in st.session_state:
    st.session_state.last_speak_time = 0

# WebRTC Streamer
ctx = webrtc_streamer(
    key="yolo-live",
    video_processor_factory=YOLOVideoProcessor,
    rtc_configuration=RTC_CONFIGURATION,
    media_stream_constraints={"video": True, "audio": False},
)

# Handle speech from the video processor
if ctx.video_processor:
    st.session_state.processor = ctx.video_processor
    try:
        if not st.session_state.processor.detection_queue.empty():
            obj = st.session_state.processor.detection_queue.get_nowait()
            if obj != st.session_state.last_spoken:
                with st.spinner("Generating voice message..."):
                    message = get_gemini_text(obj)
                    st.success(f"🔊 Speaking: {message}")
                    speak(message)
                st.session_state.last_spoken = obj
                st.session_state.last_speak_time = time.time()
    except:
        pass

# Instructions
st.markdown("---")
st.markdown("""
### 🎯 Instructions:
1. **Click 'START'** to activate your camera
2. **Allow camera permissions** when prompted by your browser
3. **Point camera** at objects to detect
4. **Listen** for automatic voice alerts

### ✅ Features:
- Real-time YOLO object detection
- Live camera feed in browser
- AI-generated voice messages via Gemini
- Automatic speech for detected objects
- Cloud compatible
""")
