import streamlit as st
import google.generativeai as genai
from gtts import gTTS
import tempfile
import os
import time
import numpy as np
from PIL import Image
import requests
import io

# -------------------------------
# 🔐 Gemini API Key
# -------------------------------
API_KEY = "AIzaSyDrGWv-nruXtcfcph-XhT7kCkpxsqBHYps"
genai.configure(api_key=API_KEY)
gemini_model = genai.GenerativeModel("gemini-2.0-flash")

# -------------------------------
# Streamlit Page
# -------------------------------
st.set_page_config(page_title="AI Object Detection with Voice", layout="wide")
st.markdown(
    "<h2 style='text-align:center;'>📷 AI Object Detection with Voice Feedback</h2>",
    unsafe_allow_html=True
)

# -------------------------------
# Gemini Text Generator
# -------------------------------
def get_gemini_text(obj_name):
    prompt = f"This is a {obj_name}. Tell the user politely to remove it in one short sentence."
    try:
        reply = gemini_model.generate_content(prompt)
        return reply.text.strip()
    except Exception as e:
        return f"Please remove the {obj_name} from the area."

# -------------------------------
# Auto Speaker
# -------------------------------
def speak(text):
    try:
        tts = gTTS(text=text, lang="en")
        path = os.path.join(tempfile.gettempdir(), "voice.mp3")
        tts.save(path)
        st.audio(path, autoplay=True)
    except Exception as e:
        st.warning(f"Could not generate audio: {e}")

# -------------------------------
# Simple object detection using Gemini Vision
# -------------------------------
def detect_objects_gemini(image):
    """Use Gemini's vision capabilities for object detection"""
    try:
        # Convert PIL image to bytes
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        img_byte_arr = img_byte_arr.getvalue()
        
        # Create the prompt for Gemini
        prompt = """Look at this image and list all the main objects you see. 
        Return only a comma-separated list of object names, nothing else."""
        
        # Use Gemini with vision
        vision_model = genai.GenerativeModel("gemini-1.5-flash")
        response = vision_model.generate_content([
            prompt,
            {"mime_type": "image/png", "data": img_byte_arr}
        ])
        
        # Parse the response
        objects_text = response.text.strip()
        detected_objects = [obj.strip() for obj in objects_text.split(',')]
        
        return detected_objects[:3]  # Return top 3 objects
        
    except Exception as e:
        st.error(f"Detection error: {e}")
        return []

# -------------------------------
# Manual object detection (fallback)
# -------------------------------
def manual_object_detection():
    """Manual object selection as fallback"""
    common_objects = ["phone", "laptop", "book", "bottle", "cup", "glass", "person", "bag", "chair"]
    selected_objects = st.multiselect("Or select objects manually:", common_objects)
    return selected_objects

# -------------------------------
# Session State for Speech Control
# -------------------------------
if 'last_spoken' not in st.session_state:
    st.session_state.last_spoken = ""
if 'last_detection_time' not in st.session_state:
    st.session_state.last_detection_time = 0

# -------------------------------
# Main App
# -------------------------------
st.subheader("📸 Upload or Capture Image")

# Image input options
option = st.radio("Choose input method:", 
                 ["Upload Image", "Use Camera", "Manual Selection"])

detected_objects = []

if option == "Upload Image":
    uploaded_file = st.file_uploader("Choose an image", type=['jpg', 'jpeg', 'png'])
    if uploaded_file:
        image = Image.open(uploaded_file)
        st.image(image, caption="Uploaded Image", use_column_width=True)
        
        if st.button("Detect Objects"):
            with st.spinner("Analyzing image with AI..."):
                detected_objects = detect_objects_gemini(image)

elif option == "Use Camera":
    camera_image = st.camera_input("Take a picture")
    if camera_image:
        image = Image.open(camera_image)
        st.image(image, caption="Captured Image", use_column_width=True)
        
        if st.button("Detect Objects"):
            with st.spinner("Analyzing image with AI..."):
                detected_objects = detect_objects_gemini(image)

elif option == "Manual Selection":
    st.info("Select objects you want to detect from the list below")
    detected_objects = manual_object_detection()

# Display results and handle speech
if detected_objects:
    st.success(f"Detected objects: {', '.join(detected_objects)}")
    
    # Let user select which object to speak about
    if len(detected_objects) > 1:
        selected_obj = st.selectbox("Select object for voice message:", detected_objects)
    else:
        selected_obj = detected_objects[0]
    
    # Speak about the selected object
    current_time = time.time()
    
    if st.button("Generate Voice Message") or (current_time - st.session_state.last_detection_time > 30):
        with st.spinner("Generating voice message..."):
            message = get_gemini_text(selected_obj)
            st.info(f"**Voice Message:** {message}")
            speak(message)
        
        st.session_state.last_spoken = selected_obj
        st.session_state.last_detection_time = current_time

elif option != "Manual Selection":
    st.info("Upload an image or use camera to detect objects")

# -------------------------------
# Instructions
# -------------------------------
st.markdown("---")
st.markdown("""
### How to use:
1. **Upload Image**: Upload any image file (JPG, PNG)
2. **Use Camera**: Take a picture with your webcam
3. **Manual Selection**: Select objects from the list manually
4. Click "Detect Objects" to analyze the image
5. Click "Generate Voice Message" to get audio feedback

### Features:
- ✅ AI-powered object detection using Gemini Vision
- ✅ AI-generated polite voice messages
- ✅ Text-to-speech functionality
- ✅ Multiple input methods
- ✅ Cloud-compatible (no complex dependencies)
""")
