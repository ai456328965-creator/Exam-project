import streamlit as st
import google.generativeai as genai
from gtts import gTTS
import tempfile
import os
import time
import base64
from PIL import Image
import numpy as np
import cv2

# --------------------------------------------------
# 🔐 Gemini API Key
# --------------------------------------------------
API_KEY = "AIzaSyDrGWv-nruXtcfcph-XhT7kCkpxsqBHYps"
genai.configure(api_key=API_KEY)
gemini_model = genai.GenerativeModel("gemini-2.0-flash")

# --------------------------------------------------
# Streamlit Page Settings
# --------------------------------------------------
st.set_page_config(page_title="YOLO Live Detection", layout="wide")
st.markdown("<h2 style='text-align:center;'>🎥 YOLO Live Detection - Real Time</h2>", unsafe_allow_html=True)

# Your trained YOLO objects
YOLO_OBJECTS = ["mobile", "notebook", "book", "calculator", "watch", "bag", "paper"]

# --------------------------------------------------
# Load YOLO Model
# --------------------------------------------------
@st.cache_resource
def load_model():
    try:
        from ultralytics import YOLO
        model = YOLO("best.pt")
        st.success("✅ YOLO Model Loaded Successfully!")
        return model
    except Exception as e:
        st.error(f"❌ Failed to load YOLO model: {e}")
        return None

model = load_model()

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
            
            # Auto-play audio using HTML
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
# Real YOLO Object Detection
# --------------------------------------------------
def detect_objects_yolo(image):
    """Real YOLO object detection"""
    if model is None:
        return []
    
    try:
        # Convert PIL to numpy array (OpenCV format)
        img_array = np.array(image)
        
        # Convert RGB to BGR for OpenCV
        if len(img_array.shape) == 3:
            img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        else:
            img_bgr = img_array
        
        # Run YOLO prediction
        results = model.predict(img_bgr, conf=0.5, verbose=False)
        
        detected_objects = []
        
        # Process detections
        for r in results:
            boxes = r.boxes
            if boxes is not None:
                for box in boxes:
                    cls = int(box.cls[0])
                    conf = float(box.conf[0])
                    class_name = model.names[cls]
                    
                    # Only include if confidence > 0.5 and in our object list
                    if conf > 0.5 and class_name in YOLO_OBJECTS:
                        detected_objects.append(class_name)
        
        return list(set(detected_objects))  # Remove duplicates
        
    except Exception as e:
        st.error(f"Detection error: {e}")
        return []

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

# --------------------------------------------------
# Main App - Real Live Detection
# --------------------------------------------------
st.info(f"🎯 **Trained to detect:** {', '.join(YOLO_OBJECTS)}")

if model is None:
    st.error("❌ YOLO model not loaded. Please check if 'best.pt' is in your directory.")
    st.stop()

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
speed_intervals = {"Slow": 5, "Medium": 3, "Fast": 2}
detection_interval = speed_intervals[detection_speed]

if auto_detect:
    st.success(f"🔴 **LIVE** - Real YOLO detection every {detection_interval} seconds")
    
    # Live camera feed
    camera_image = st.camera_input("Live Camera - Real YOLO Detection Active", key="live_camera")
    
    if camera_image:
        # Display camera feed
        image = Image.open(camera_image)
        
        # Create columns for side-by-side display
        col1, col2 = st.columns(2)
        
        with col1:
            st.image(image, caption="📷 Live Camera Feed", use_column_width=True)
        
        with col2:
            # Detect objects using real YOLO
            with st.spinner("🔍 YOLO is detecting objects..."):
                detected_objects = detect_objects_yolo(image)
            
            if detected_objects:
                st.session_state.detection_count += 1
                
                # Display detection results
                st.success(f"**🎯 YOLO Detected:** {', '.join(detected_objects)}")
                
                # Auto-speak logic
                current_time = time.time()
                obj = detected_objects[0]  # Speak about first detected object
                
                # Speak if new object or cooldown passed
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
                                'confidence': 'High'
                            })
                
                # Show all detected objects
                if len(detected_objects) > 1:
                    st.info(f"**Also detected:** {', '.join(detected_objects[1:])}")
                
            else:
                st.warning("❌ No objects detected")
        
        # Show recent detection history
        if len(st.session_state.object_history) > 0:
            st.subheader("📋 Detection History")
            for detection in st.session_state.object_history[-5:]:  # Last 5 detections
                st.write(f"**{detection['time']}** - {detection['object']}: *{detection['message']}*")
        
        # Auto-refresh for continuous detection
        time.sleep(detection_interval)
        st.rerun()

else:
    st.info("🟢 **MANUAL MODE** - Enable auto-detection for live monitoring")
    
    camera_image = st.camera_input("Take a picture for detection", key="manual_camera")
    
    if camera_image:
        image = Image.open(camera_image)
        st.image(image, caption="📸 Captured Image", use_column_width=True)
        
        if st.button("🔍 Detect Objects with YOLO", use_container_width=True):
            with st.spinner("🔍 YOLO is analyzing image..."):
                detected_objects = detect_objects_yolo(image)
            
            if detected_objects:
                st.success(f"**🎯 YOLO Detected:** {', '.join(detected_objects)}")
                
                # Let user choose which object to speak about
                if detected_objects:
                    selected_obj = st.selectbox("Select object for voice message:", detected_objects)
                    
                    if st.button("🎵 Generate Voice Message", use_container_width=True):
                        message = get_gemini_text(selected_obj)
                        speak(message)
            else:
                st.warning("❌ No objects detected in the image")

# --------------------------------------------------
# Quick Detection Buttons for all 7 objects
# --------------------------------------------------
st.markdown("---")
st.subheader("⚡ Quick Voice Commands")

# Create buttons for all 7 objects
cols = st.columns(3)
for i, obj in enumerate(YOLO_OBJECTS):
    with cols[i % 3]:
        if st.button(f"🔊 {obj.title()}", use_container_width=True, key=f"quick_{obj}"):
            message = get_gemini_text(obj)
            speak(message)

# --------------------------------------------------
# Live Statistics
# --------------------------------------------------
st.markdown("---")
st.subheader("📊 Live Detection Dashboard")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Detections", st.session_state.detection_count)

with col2:
    st.metric("Last Object", st.session_state.last_spoken or "None")

with col3:
    time_since_last = int(time.time() - st.session_state.last_speak_time)
    st.metric("Last Alert", f"{time_since_last}s ago")

with col4:
    if auto_detect:
        st.metric("Status", "🔴 LIVE")
    else:
        st.metric("Status", "🟢 READY")

# --------------------------------------------------
# Object Detection Statistics
# --------------------------------------------------
st.markdown("---")
st.subheader("📈 Object Detection Statistics")

# Calculate detection frequency
object_counts = {}
for detection in st.session_state.object_history:
    obj = detection['object']
    object_counts[obj] = object_counts.get(obj, 0) + 1

if object_counts:
    st.write("**Detection Frequency:**")
    for obj in YOLO_OBJECTS:
        count = object_counts.get(obj, 0)
        st.write(f"- {obj}: {count} time(s)")
else:
    st.info("No detections yet. Enable live detection to see statistics.")

# --------------------------------------------------
# Instructions
# --------------------------------------------------
st.markdown("---")
st.markdown("""
### 🎯 How to Use Real YOLO Detection:

**🚀 Auto Live Mode:**
1. Enable "Live Auto-Detection"
2. Point camera at objects (mobile, notebook, book, calculator, watch, bag, paper)
3. Real YOLO model detects objects automatically
4. System speaks alerts using Gemini AI
5. Watch real-time detection history

**📸 Manual Mode:**
1. Take a picture with camera
2. Click "Detect Objects with YOLO"
3. Select object from dropdown
4. Click "Generate Voice Message"

**⚡ Quick Commands:**
- Test voice alerts for specific objects
- Perfect for verifying detection

### 🎯 Your YOLO Model Objects:
- 📱 Mobile
- 📓 Notebook  
- 📚 Book
- 🧮 Calculator
- ⌚ Watch
- 🎒 Bag
- 📄 Paper

### ⚙️ Real YOLO Detection:
- **Confidence threshold:** 50%
- **Real-time processing**
- **Actual object detection** (not simulated)
- **Automatic voice feedback**
""")

# Continuous refresh for auto mode
if auto_detect:
    time.sleep(1)
    st.rerun()
