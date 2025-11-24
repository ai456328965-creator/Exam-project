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
        return [obj for obj in detected_objects if obj]  # Remove empty strings
        
    except Exception as e:
        st.error(f"Detection error: {e}")
        return []

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
        
        st.info(f"🔊 **Voice Message:** {text}")
        
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

# --------------------------------------------------
# Main App - Live Camera Section
# --------------------------------------------------
st.info("🎥 Use your camera for real-time detection")

# Camera input
camera_image = st.camera_input("Take a picture for real-time detection", key="live_camera")

if camera_image and not st.session_state.processing:
    st.session_state.processing = True
    
    try:
        # Display the captured image
        image = Image.open(camera_image)
        st.image(image, caption="Live Camera Feed - Processing...", use_column_width=True)
        
        # Detect objects
        with st.spinner("🔍 AI is analyzing the image..."):
            detected_objects = detect_objects_with_gemini(image)
        
        if detected_objects:
            st.success(f"**Detected Objects:** {', '.join(detected_objects)}")
            
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
            else:
                st.info(f"Object '{obj}' was recently mentioned. Wait for new detection.")
        else:
            st.warning("No objects detected in the image")
            
    except Exception as e:
        st.error(f"Processing error: {e}")
    
    st.session_state.processing = False

# --------------------------------------------------
# Manual Image Upload Section
# --------------------------------------------------
st.markdown("---")
st.subheader("📸 Alternative: Upload Image for Detection")

uploaded_file = st.file_uploader("Or choose an image file", type=['jpg', 'jpeg', 'png'])
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

# --------------------------------------------------
# Manual Object Selection (Fallback)
# --------------------------------------------------
st.markdown("---")
st.subheader("🛠️ Manual Mode")

st.info("If camera detection isn't working, you can manually select objects:")

manual_objects = st.multiselect(
    "Select objects manually:",
    ["phone", "laptop", "bottle", "cup", "book", "person", "bag", "chair", "table", "glass"]
)

if manual_objects and st.button("Generate Manual Voice Message"):
    selected_obj = manual_objects[0]
    message = get_gemini_text(selected_obj)
    speak(message)

# --------------------------------------------------
# Instructions
# --------------------------------------------------
st.markdown("---")
st.markdown("""
### 🎯 How to Use:

**Live Camera Mode (Recommended):**
1. Allow camera access when prompted
2. Point camera at objects - the system automatically detects and speaks
3. New detections trigger voice alerts every 10 seconds

**Image Upload Mode:**
1. Upload any image file (JPG, PNG)
2. Click "Detect Objects in Image" 
3. Select which object to generate voice message for
4. Click "Generate Voice Message"

**Manual Mode:**
1. Select objects from the list
2. Click "Generate Manual Voice Message"

### ✅ Features:
- **AI-powered object detection** using Gemini Vision
- **Real-time camera processing**
- **Auto-generated voice messages**
- **Text-to-speech functionality** 
- **Cloud compatible** - no complex dependencies
- **Multiple input methods**

### 🔄 For Real-time Detection:
- Keep the camera pointed at objects
- System automatically processes every new image
- Voice alerts for new detections
- 10-second cooldown between same object alerts
""")

# Auto-refresh for continuous detection
st.markdown("---")
auto_refresh = st.checkbox("Enable auto-refresh for continuous detection", value=True)

if auto_refresh:
    st.write("🔄 Camera will automatically refresh for continuous detection")
    time.sleep(5)  # Wait 5 seconds before allowing next capture
    st.rerun()
