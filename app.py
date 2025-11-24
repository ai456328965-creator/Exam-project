import streamlit as st
from ultralytics import YOLO
import google.generativeai as genai
from gtts import gTTS
import tempfile
import os
import time
import cv2
import numpy as np
from PIL import Image

# -------------------------------
# 🔐 Gemini API Key
# -------------------------------
API_KEY = "AIzaSyDrGWv-nruXtcfcph-XhT7kCkpxsqBHYps"
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
# YOLO Detection Function
# -------------------------------
def detect_objects(image):
    # Convert PIL Image to numpy array
    img_array = np.array(image)
    
    # Convert RGB to BGR for OpenCV
    img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
    
    # YOLO Prediction
    results = model.predict(img_bgr, conf=0.5, verbose=False)
    
    detected = []
    for box in results[0].boxes:
        cls = int(box.cls[0])
        class_name = model.names[cls]
        detected.append(class_name)
        
        # Draw rectangle
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        cv2.rectangle(img_bgr, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(img_bgr, class_name, (x1, y1-10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)
    
    # Convert back to RGB for display
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    
    return img_rgb, detected

# -------------------------------
# Session State for Speech Control
# -------------------------------
if 'last_spoken' not in st.session_state:
    st.session_state.last_spoken = ""
if 'last_detection_time' not in st.session_state:
    st.session_state.last_detection_time = 0

# -------------------------------
# Camera Input
# -------------------------------
st.subheader("📸 Camera Feed")

# Option 1: Upload image
uploaded_file = st.file_uploader("Or upload an image", type=['jpg', 'jpeg', 'png'])

# Option 2: Use camera
camera_image = st.camera_input("Take a picture")

# Process the image
image_to_process = None
if camera_image:
    image_to_process = camera_image
elif uploaded_file:
    image_to_process = uploaded_file

if image_to_process:
    # Open the image
    image = Image.open(image_to_process)
    
    # Display original image
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Original Image")
        st.image(image, use_column_width=True)
    
    # Detect objects
    with st.spinner("Detecting objects..."):
        processed_image, detected_objects = detect_objects(image)
    
    with col2:
        st.subheader("Processed Image")
        st.image(processed_image, use_column_width=True)
    
    # Display results and handle speech
    if detected_objects:
        st.success(f"Detected: {', '.join(detected_objects)}")
        
        # Speak about the first detected object
        current_time = time.time()
        obj = detected_objects[0]
        
        # Only speak if it's a new object or enough time has passed
        if (obj != st.session_state.last_spoken or 
            current_time - st.session_state.last_detection_time > 10):
            
            with st.spinner("Generating voice message..."):
                message = get_gemini_text(obj)
                st.info(f"Voice Message: {message}")
                speak(message)
            
            st.session_state.last_spoken = obj
            st.session_state.last_detection_time = current_time
    else:
        st.info("No objects detected")

# -------------------------------
# Instructions
# -------------------------------
st.markdown("---")
st.markdown("""
### Instructions:
1. Allow camera access when prompted
2. Point the camera at objects to detect
3. The system will automatically generate and speak a message when objects are detected
4. You can also upload images using the file uploader

### Features:
- ✅ Real-time object detection using YOLO
- ✅ AI-generated voice messages using Gemini
- ✅ Text-to-speech functionality
- ✅ Visual bounding boxes and labels
""")
