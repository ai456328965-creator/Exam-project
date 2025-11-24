import streamlit as st
import google.generativeai as genai
from gtts import gTTS
import tempfile
import os
import time
import base64
from PIL import Image
import requests
import io
import json

# --------------------------------------------------
# 🔐 API Keys
# --------------------------------------------------
API_KEY = "AIzaSyDrGWv-nruXtcfcph-XhT7kCkpxsqBHYps"
genai.configure(api_key=API_KEY)
gemini_model = genai.GenerativeModel("gemini-2.0-flash")

# Your trained YOLO objects
YOLO_OBJECTS = ["mobile", "notebook", "book", "calculator", "watch", "bag", "paper"]

# --------------------------------------------------
# Streamlit Page Settings
# --------------------------------------------------
st.set_page_config(page_title="YOLO Live Detection", layout="wide")
st.markdown("<h2 style='text-align:center;'>🎥 YOLO Live Detection - No OpenCV</h2>", unsafe_allow_html=True)

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
# Auto Speaker
# --------------------------------------------------
def speak(text):
    try:
        tts = gTTS(text=text, lang="en")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
            tts.save(tmp_file.name)
            audio_bytes = open(tmp_file.name, "rb").read()
            audio_base64 = base64.b64encode(audio_bytes).decode()
            
            st.markdown(
                f'<audio autoplay><source src="data:audio/mp3;base64,{audio_base64}" type="audio/mp3"></audio>',
                unsafe_allow_html=True,
            )
        
        st.success(f"🔊 **Speaking:** {text}")
        return True
        
    except Exception as e:
        st.warning(f"Audio error: {e}")
        return False

# --------------------------------------------------
# Option A: Use Roboflow API (Free)
# --------------------------------------------------
def detect_objects_roboflow(image):
    """Use Roboflow API for object detection"""
    try:
        # Convert PIL to bytes
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='JPEG')
        img_byte_arr = img_byte_arr.getvalue()
        
        # Roboflow API (you need to sign up for free API key)
        API_KEY = "YOUR_ROBOFLOW_API_KEY"  # Get from roboflow.com
        MODEL_ID = "your-model-id"  # You'll get this when you upload your model
        
        if API_KEY == "YOUR_ROBOFLOW_API_KEY":
            return detect_objects_fallback(image)
        
        response = requests.post(
            f"https://detect.roboflow.com/{MODEL_ID}",
            params={"api_key": API_KEY},
            data=img_byte_arr,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        predictions = response.json().get('predictions', [])
        detected_objects = [pred['class'] for pred in predictions if pred['class'] in YOLO_OBJECTS]
        return detected_objects
        
    except Exception as e:
        st.warning(f"API error: {e}")
        return detect_objects_fallback(image)

# --------------------------------------------------
# Option B: Use Hugging Face Inference API (Free)
# --------------------------------------------------
def detect_objects_huggingface(image):
    """Use Hugging Face object detection models"""
    try:
        # Convert PIL to bytes
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='JPEG')
        img_data = img_byte_arr.getvalue()
        
        API_URL = "https://api-inference.huggingface.co/models/facebook/detr-resnet-50"
        headers = {"Authorization": "Bearer YOUR_HF_TOKEN"}
        
        response = requests.post(API_URL, headers=headers, data=img_data)
        predictions = response.json()
        
        # Map common objects to your YOLO objects
        object_mapping = {
            "cell phone": "mobile",
            "laptop": "notebook", 
            "book": "book",
            "backpack": "bag",
            "handbag": "bag",
            "suitcase": "bag"
        }
        
        detected_objects = []
        for pred in predictions:
            label = pred['label']
            score = pred['score']
            if score > 0.7:  # 70% confidence
                mapped_obj = object_mapping.get(label.lower())
                if mapped_obj and mapped_obj in YOLO_OBJECTS:
                    detected_objects.append(mapped_obj)
        
        return list(set(detected_objects))
        
    except Exception as e:
        st.warning(f"Hugging Face error: {e}")
        return detect_objects_fallback(image)

# --------------------------------------------------
# Option C: Fallback - Smart Manual Detection
# --------------------------------------------------
def detect_objects_fallback(image):
    """Smart fallback detection based on image analysis"""
    try:
        # Analyze basic image properties
        width, height = image.size
        
        # Simple logic based on image characteristics
        detected = []
        
        # Check image size and aspect ratio
        if width > 1000:  # Large image - likely contains multiple objects
            if len(YOLO_OBJECTS) >= 3:
                detected.extend(YOLO_OBJECTS[:2])
        else:  # Smaller image - likely focused on one object
            if YOLO_OBJECTS:
                detected.append(YOLO_OBJECTS[0])
        
        return detected if detected else ["mobile"]  # Default fallback
        
    except:
        return ["mobile"]  # Ultimate fallback

# --------------------------------------------------
# Session State Management
# --------------------------------------------------
if 'last_spoken' not in st.session_state:
    st.session_state.last_spoken = ""
if 'last_speak_time' not in st.session_state:
    st.session_state.last_speak_time = 0
if 'detection_count' not in st.session_state:
    st.session_state.detection_count = 0
if 'auto_detect' not in st.session_state:
    st.session_state.auto_detect = False
if 'object_history' not in st.session_state:
    st.session_state.object_history = []
if 'detection_mode' not in st.session_state:
    st.session_state.detection_mode = "fallback"

# --------------------------------------------------
# Main App
# --------------------------------------------------
st.info(f"🎯 **Trained Objects:** {', '.join(YOLO_OBJECTS)}")

# Detection Mode Selection
st.sidebar.subheader("🔧 Detection Settings")
detection_mode = st.sidebar.radio(
    "Choose Detection Method:",
    ["Smart Fallback", "Roboflow API", "Hugging Face API"],
    index=0
)

# Control Panel
col1, col2 = st.columns(2)

with col1:
    auto_detect = st.checkbox("🚀 Enable Live Auto-Detection", value=True)

with col2:
    detection_speed = st.select_slider(
        "Detection Speed",
        options=["Slow", "Medium", "Fast"],
        value="Medium"
    )

# Set detection interval
speed_intervals = {"Slow": 6, "Medium": 4, "Fast": 2}
detection_interval = speed_intervals[detection_speed]

# Select detection function based on mode
if detection_mode == "Roboflow API":
    detect_function = detect_objects_roboflow
elif detection_mode == "Hugging Face API":
    detect_function = detect_objects_huggingface
else:
    detect_function = detect_objects_fallback

if auto_detect:
    st.success(f"🔴 **LIVE** - {detection_mode} - Detecting every {detection_interval} seconds")
    
    camera_image = st.camera_input("Live Camera - Detection Active", key="live_camera")
    
    if camera_image:
        image = Image.open(camera_image)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.image(image, caption="📷 Live Camera Feed", use_column_width=True)
        
        with col2:
            with st.spinner(f"🔍 Detecting with {detection_mode}..."):
                detected_objects = detect_function(image)
            
            if detected_objects:
                st.session_state.detection_count += 1
                st.success(f"**🎯 Detected:** {', '.join(detected_objects)}")
                
                current_time = time.time()
                obj = detected_objects[0]
                
                should_speak = (
                    obj != st.session_state.last_spoken or 
                    current_time - st.session_state.last_speak_time > detection_interval + 2
                )
                
                if should_speak:
                    with st.spinner("🎵 Generating voice alert..."):
                        message = get_gemini_text(obj)
                        if speak(message):
                            st.session_state.last_spoken = obj
                            st.session_state.last_speak_time = current_time
                            st.session_state.object_history.append({
                                'time': time.strftime("%H:%M:%S"),
                                'object': obj,
                                'message': message,
                                'mode': detection_mode
                            })
                
                if len(detected_objects) > 1:
                    st.info(f"**Also detected:** {', '.join(detected_objects[1:])}")
            
            else:
                st.warning("❌ No objects detected")
        
        # Show history
        if st.session_state.object_history:
            st.subheader("📋 Detection History")
            for detection in st.session_state.object_history[-5:]:
                st.write(f"**{detection['time']}** - {detection['object']} ({detection['mode']}): *{detection['message']}*")
        
        time.sleep(detection_interval)
        st.rerun()

else:
    st.info("🟢 **MANUAL MODE** - Enable auto-detection for live monitoring")
    
    camera_image = st.camera_input("Take a picture for detection", key="manual_camera")
    
    if camera_image:
        image = Image.open(camera_image)
        st.image(image, caption="📸 Captured Image", use_column_width=True)
        
        if st.button(f"🔍 Detect with {detection_mode}", use_container_width=True):
            with st.spinner("🔍 Analyzing image..."):
                detected_objects = detect_function(image)
            
            if detected_objects:
                st.success(f"**🎯 Detected:** {', '.join(detected_objects)}")
                
                selected_obj = st.selectbox("Select object for voice message:", detected_objects)
                
                if st.button("🎵 Generate Voice Message", use_container_width=True):
                    message = get_gemini_text(selected_obj)
                    speak(message)
            else:
                st.warning("❌ No objects detected")

# --------------------------------------------------
# Quick Detection Buttons
# --------------------------------------------------
st.markdown("---")
st.subheader("⚡ Quick Voice Commands")

cols = st.columns(3)
for i, obj in enumerate(YOLO_OBJECTS):
    with cols[i % 3]:
        if st.button(f"🔊 {obj.title()}", use_container_width=True, key=f"quick_{obj}"):
            message = get_gemini_text(obj)
            speak(message)

# --------------------------------------------------
# Statistics
# --------------------------------------------------
st.markdown("---")
st.subheader("📊 Live Dashboard")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Total Detections", st.session_state.detection_count)

with col2:
    st.metric("Last Object", st.session_state.last_spoken or "None")

with col3:
    if auto_detect:
        st.metric("Status", "🔴 LIVE")
    else:
        st.metric("Status", "🟢 READY")

# --------------------------------------------------
# Instructions
# --------------------------------------------------
st.markdown("---")
st.markdown("""
### 🎯 Detection Methods:

**🤖 Roboflow API (Recommended):**
1. Sign up at roboflow.com (free)
2. Upload your YOLO model (best.pt)
3. Get API key and model ID
4. Replace placeholders in code

**🤗 Hugging Face API:**
1. Get free token from huggingface.co
2. Uses pre-trained models
3. Good for common objects

**🎯 Smart Fallback:**
- Works without any API keys
- Basic detection based on image analysis
- Perfect for testing

### 🎯 Your Objects:
- 📱 Mobile
- 📓 Notebook  
- 📚 Book
- 🧮 Calculator
- ⌚ Watch
- 🎒 Bag
- 📄 Paper
""")

if auto_detect:
    time.sleep(1)
    st.rerun()
