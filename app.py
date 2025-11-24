import streamlit as st
import google.generativeai as genai
from gtts import gTTS
import tempfile
import os
import time
import queue
from PIL import Image
import av
import numpy as np
from streamlit_webrtc import webrtc_streamer, VideoProcessorBase, RTCConfiguration

# --------------------------------------------------
# 🔐 Gemini API Key
# --------------------------------------------------
API_KEY = "AIzaSyDrGWv-nruXtcfcph-XhT7kCkpxsqBHYps"
genai.configure(api_key=API_KEY)
gemini_model = genai.GenerativeModel("gemini-1.5-flash")

# --------------------------------------------------
# Streamlit Page Settings
# --------------------------------------------------
st.set_page_config(page_title="AI Live Detection with Voice", layout="wide")
st.markdown("<h2 style='text-align:center;'>📷 AI Real-Time Detection with Auto Voice (Gemini Vision)</h2>", unsafe_allow_html=True)

# --------------------------------------------------
# Gemini Text Generator
# --------------------------------------------------
def get_gemini_text(obj_name):
    prompt = f"This is a {obj_name}. Tell the user politely to remove it in one short sentence."
    try:
        reply = gemini_model.generate_content(prompt)
        return reply.text.strip()
    except Exception as e:
        return f"Please remove the {obj_name}."

# --------------------------------------------------
# Object Detection using Gemini Vision
# --------------------------------------------------
def detect_objects_with_gemini(image):
    """Use Gemini Vision to detect objects in the image"""
    try:
        prompt = """Look at this image and identify all visible objects. 
        Return ONLY a comma-separated list of the main objects you see. 
        Example: person, laptop, phone, bottle
        Do not include any other text."""
        
        response = gemini_model.generate_content([prompt, image])
        objects_text = response.text.strip()
        
        # Parse the response
        detected_objects = [obj.strip() for obj in objects_text.split(',')]
        return detected_objects[:3]  # Return top 3 objects
        
    except Exception as e:
        st.error(f"Detection error: {e}")
        return []

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
        <audio autoplay controls style="display: none;">
            <source src="data:audio/mp3;base64,{path}" type="audio/mpeg">
        </audio>
        """, unsafe_allow_html=True)
        
        # Also display the text
        st.info(f"🔊 **Voice Message:** {text}")
        
    except Exception as e:
        st.warning(f"Audio error: {e}")

# --------------------------------------------------
# Video Processor for Live Detection
# --------------------------------------------------
class LiveDetectionProcessor(VideoProcessorBase):
    def __init__(self):
        self.last_spoken = ""
        self.speak_delay = 10  # seconds between speeches
        self.last_speak_time = 0
        self.detection_queue = queue.Queue()
        self.frame_counter = 0
        self.detection_interval = 30  # Process every 30 frames

    def recv(self, frame):
        img = frame.to_ndarray(format="bgr24")
        self.frame_counter += 1
        
        # Only process every N frames to reduce API calls
        if self.frame_counter % self.detection_interval == 0:
            try:
                # Convert to PIL Image for Gemini
                pil_image = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
                
                # Detect objects using Gemini Vision
                detected_objects = detect_objects_with_gemini(pil_image)
                
                # Handle speech logic
                if detected_objects:
                    current_time = time.time()
                    obj = detected_objects[0]  # Use first detected object
                    
                    if (obj != self.last_spoken and 
                        current_time - self.last_speak_time > self.speak_delay):
                        self.detection_queue.put(obj)
                        self.last_spoken = obj
                        self.last_speak_time = current_time
                        
            except Exception as e:
                # Continue processing frames even if detection fails
                pass
        
        return frame

# --------------------------------------------------
# RTC Configuration
# --------------------------------------------------
RTC_CONFIGURATION = RTCConfiguration({
    "iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]
})

# --------------------------------------------------
# Manual OpenCV import (only if needed for drawing)
# --------------------------------------------------
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    st.warning("OpenCV not available for drawing bounding boxes")

# --------------------------------------------------
# Main App
# --------------------------------------------------
st.info("🎥 Click 'START' below to begin live camera detection with AI")

# Initialize session state
if 'last_spoken' not in st.session_state:
    st.session_state.last_spoken = ""
if 'last_speak_time' not in st.session_state:
    st.session_state.last_speak_time = 0
if 'processor' not in st.session_state:
    st.session_state.processor = None

# WebRTC Streamer
ctx = webrtc_streamer(
    key="ai-live-detection",
    video_processor_factory=LiveDetectionProcessor,
    rtc_configuration=RTC_CONFIGURATION,
    media_stream_constraints={"video": True, "audio": False},
)

# Handle speech from the video processor
if ctx.video_processor:
    st.session_state.processor = ctx.video_processor
    
    # Check for new detections
    try:
        if not st.session_state.processor.detection_queue.empty():
            obj = st.session_state.processor.detection_queue.get_nowait()
            
            if obj != st.session_state.last_spoken:
                with st.spinner("🔄 Generating voice message..."):
                    message = get_gemini_text(obj)
                    st.success(f"**Detected:** {obj}")
                    speak(message)
                
                st.session_state.last_spoken = obj
                st.session_state.last_speak_time = time.time()
                
    except Exception as e:
        st.warning(f"Speech handling error: {e}")

# Alternative: Single Image Upload
st.markdown("---")
st.subheader("📸 Alternative: Upload Image for Detection")

uploaded_file = st.file_uploader("Choose an image file", type=['jpg', 'jpeg', 'png'])
if uploaded_file:
    image = Image.open(uploaded_file)
    st.image(image, caption="Uploaded Image", use_column_width=True)
    
    if st.button("Detect Objects in Image"):
        with st.spinner("🔍 Analyzing image with AI..."):
            detected_objects = detect_objects_with_gemini(image)
            
        if detected_objects:
            st.success(f"**Detected Objects:** {', '.join(detected_objects)}")
            
            # Let user choose which object to speak about
            selected_obj = st.selectbox("Select object for voice message:", detected_objects)
            
            if st.button("Generate Voice Message"):
                message = get_gemini_text(selected_obj)
                speak(message)
        else:
            st.warning("No objects detected in the image")

# Instructions
st.markdown("---")
st.markdown("""
### 🎯 How to Use:

**Live Camera Mode:**
1. Click **'START'** to activate your camera
2. Allow camera permissions in your browser
3. Point camera at objects - detection happens automatically
4. Listen for AI-generated voice alerts

**Image Upload Mode:**
1. Upload any image file
2. Click "Detect Objects in Image"
3. Select which object to generate voice message for
4. Click "Generate Voice Message"

### ✅ Features:
- **Live camera detection** using Gemini Vision AI
- **Real-time object recognition**
- **AI-generated polite voice messages**
- **Text-to-speech functionality**
- **Cloud compatible** - no complex dependencies
- **Multiple input methods** (camera + upload)
""")
