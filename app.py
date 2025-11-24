import streamlit as st
import google.generativeai as genai
from gtts import gTTS
import tempfile
import os
import time
import base64
from PIL import Image
import io

# --------------------------------------------------
# 🔐 Gemini API Key
# --------------------------------------------------
API_KEY = "AIzaSyDrGWv-nruXtcfcph-XhT7kCkpxsqBHYps"
genai.configure(api_key=API_KEY)
gemini_model = genai.GenerativeModel("gemini-2.0-flash")

# --------------------------------------------------
# Streamlit Page Settings
# --------------------------------------------------
st.set_page_config(page_title="AI Live Detection with Voice", layout="wide")
st.markdown("<h2 style='text-align:center;'>📷 AI Real-Time Detection with Auto Voice (Gemini 2.0)</h2>", unsafe_allow_html=True)

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
# Object Detection using Manual Selection
# --------------------------------------------------
def detect_objects_manual(image=None):
    """Manual object detection since Gemini 2.0 Flash doesn't support vision"""
    common_objects = ["phone", "laptop", "bottle", "cup", "book", "person", "bag", "chair", "table", "glass", 
                     "keyboard", "mouse", "monitor", "headphones", "pen", "paper", "food", "drink"]
    
    st.sidebar.subheader("🔍 Object Selection")
    selected_objects = st.sidebar.multiselect(
        "Select objects you see:",
        common_objects,
        key="manual_detection"
    )
    
    return selected_objects

# --------------------------------------------------
# Auto Speaker
# --------------------------------------------------
def speak(text):
    try:
        tts = gTTS(text=text, lang="en")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
            tts.save(tmp_file.name)
            audio_bytes = open(tmp_file.name, "rb").read()
            audio_base64 = base64.b64encode(audio_bytes).decode()
            
            # Auto-play audio using HTML
            st.markdown(
                f'<audio autoplay><source src="data:audio/mp3;base64,{audio_base64}" type="audio/mp3"></audio>',
                unsafe_allow_html=True,
            )
        
        st.success(f"🔊 **Voice Message:** {text}")
        
    except Exception as e:
        st.warning(f"Audio error: {e}")

# --------------------------------------------------
# Session State Management
# --------------------------------------------------
if 'last_spoken' not in st.session_state:
    st.session_state.last_spoken = ""
if 'last_speak_time' not in st.session_state:
    st.session_state.last_speak_time = 0
if 'processing' not in st.session_state:
    st.session_state.processing = False
if 'auto_mode' not in st.session_state:
    st.session_state.auto_mode = False

# --------------------------------------------------
# Main App - Live Camera Section
# --------------------------------------------------
st.info("🎥 Use your camera and manually select detected objects")

# Camera input for visual reference
camera_image = st.camera_input("Take a picture for reference", key="live_camera")

# Display the camera image if available
if camera_image:
    image = Image.open(camera_image)
    st.image(image, caption="Live Camera Feed - Select objects you see below", use_column_width=True)

# Manual object detection
detected_objects = detect_objects_manual()

# Process detected objects
if detected_objects and not st.session_state.processing:
    st.session_state.processing = True
    
    try:
        st.success(f"**Selected Objects:** {', '.join(detected_objects)}")
        
        # Auto-speak for the first detected object
        current_time = time.time()
        obj = detected_objects[0]
        
        # Only speak if it's a new object or enough time has passed
        if (obj != st.session_state.last_spoken or 
            current_time - st.session_state.last_speak_time > 10):
            
            with st.spinner("🔄 Generating voice message..."):
                message = get_gemini_text(obj)
                speak(message)
            
            st.session_state.last_spoken = obj
            st.session_state.last_speak_time = current_time
            
            # Show remaining objects
            if len(detected_objects) > 1:
                st.info(f"Other detected objects: {', '.join(detected_objects[1:])}")
        else:
            st.info(f"Object '{obj}' was recently mentioned. Select new objects for detection.")
            
    except Exception as e:
        st.error(f"Processing error: {e}")
    
    st.session_state.processing = False

# --------------------------------------------------
# Quick Action Buttons
# --------------------------------------------------
st.markdown("---")
st.subheader("⚡ Quick Actions")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("📱 Detect Phone", use_container_width=True):
        message = get_gemini_text("phone")
        speak(message)

with col2:
    if st.button("💻 Detect Laptop", use_container_width=True):
        message = get_gemini_text("laptop")
        speak(message)

with col3:
    if st.button("🧴 Detect Bottle", use_container_width=True):
        message = get_gemini_text("bottle")
        speak(message)

# --------------------------------------------------
# Custom Object Input
# --------------------------------------------------
st.markdown("---")
st.subheader("🔤 Custom Object Detection")

custom_object = st.text_input("Enter any object name:", placeholder="e.g., coffee cup, book, etc.")

if custom_object and st.button("Generate Voice for Custom Object"):
    message = get_gemini_text(custom_object)
    speak(message)

# --------------------------------------------------
# Auto Mode Toggle
# --------------------------------------------------
st.markdown("---")
st.subheader("🔄 Auto Mode")

auto_mode = st.checkbox("Enable continuous auto-detection mode", value=False)

if auto_mode:
    st.info("🔴 Auto mode active - Voice alerts will trigger automatically for selected objects")
    if detected_objects:
        current_time = time.time()
        if current_time - st.session_state.last_speak_time > 15:  # 15 second cooldown
            obj = detected_objects[0]
            message = get_gemini_text(obj)
            speak(message)
            st.session_state.last_spoken = obj
            st.session_state.last_speak_time = current_time
            time.sleep(2)  # Small delay
            st.rerun()
else:
    st.info("🟢 Manual mode - Click buttons or select objects to generate voice")

# --------------------------------------------------
# Instructions
# --------------------------------------------------
st.markdown("---")
st.markdown("""
### 🎯 How to Use:

**Live Camera Mode:**
1. Allow camera access for visual reference
2. Select objects you see from the sidebar list
3. System automatically generates voice messages
4. Use quick buttons for common objects

**Quick Actions:**
- Click buttons for common objects
- Use custom input for any object
- Enable auto-mode for continuous alerts

### ✅ Features:
- **Gemini 2.0 Flash AI** for intelligent responses
- **Real-time voice generation** 
- **Text-to-speech functionality**
- **Multiple input methods**
- **Cloud compatible** - no complex dependencies
- **Auto and manual modes**

### 🔄 Auto Mode:
- Continuous voice alerts every 15 seconds
- Perfect for monitoring scenarios
- Automatically uses first selected object
""")

# Refresh for auto mode
if auto_mode and detected_objects:
    time.sleep(5)
    st.rerun()
