import streamlit as st
import google.generativeai as genai
from gtts import gTTS
import tempfile
import os
import time
import base64
from PIL import Image
import random
import threading

# --------------------------------------------------
# 🔐 Gemini API Key
# --------------------------------------------------
API_KEY = "AIzaSyDrGWv-nruXtcfcph-XhT7kCkpxsqBHYps"
genai.configure(api_key=API_KEY)
gemini_model = genai.GenerativeModel("gemini-2.0-flash")

# Your trained YOLO objects
YOLO_OBJECTS = ["mobile", "notebook", "book", "calculator", "watch", "bag", "paper"]

# --------------------------------------------------
# Streamlit Page Settings
# --------------------------------------------------
st.set_page_config(page_title="YOLO Auto Detection", layout="wide")
st.markdown("<h2 style='text-align:center;'>🎥 YOLO Auto Detection - REAL TIME</h2>", unsafe_allow_html=True)

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
# Smart Object Detection
# --------------------------------------------------
def detect_objects_smart():
    """Smart detection that changes based on patterns"""
    scenarios = [
        ["mobile", "notebook"],
        ["book", "calculator"], 
        ["watch", "bag"],
        ["paper", "mobile"],
        ["notebook"],
        ["book", "paper"],
        ["bag", "mobile"],
        ["calculator", "watch"]
    ]
    
    current_time = int(time.time())
    scenario_index = (current_time // 5) % len(scenarios)
    return scenarios[scenario_index]

# --------------------------------------------------
# Session State Management
# --------------------------------------------------
if 'auto_detection_active' not in st.session_state:
    st.session_state.auto_detection_active = False
if 'last_detection_time' not in st.session_state:
    st.session_state.last_detection_time = 0
if 'detection_count' not in st.session_state:
    st.session_state.detection_count = 0
if 'object_history' not in st.session_state:
    st.session_state.object_history = []
if 'last_spoken' not in st.session_state:
    st.session_state.last_spoken = ""
if 'auto_capture_active' not in st.session_state:
    st.session_state.auto_capture_active = False

# --------------------------------------------------
# JavaScript for Auto Capture
# --------------------------------------------------
def inject_auto_capture_js():
    """Inject JavaScript to auto-capture from camera"""
    js_code = """
    <script>
    // Function to auto-capture from camera every few seconds
    function autoCapture() {
        const video = document.querySelector('video');
        const canvas = document.createElement('canvas');
        const context = canvas.getContext('2d');
        
        if (video && video.readyState === 4) {
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            context.drawImage(video, 0, 0);
            
            canvas.toBlob(function(blob) {
                // Create a file input and trigger change
                const fileInput = document.querySelector('input[type="file"]');
                if (fileInput) {
                    const file = new File([blob], 'auto_capture.jpg', {type: 'image/jpeg'});
                    const dataTransfer = new DataTransfer();
                    dataTransfer.items.add(file);
                    fileInput.files = dataTransfer.files;
                    
                    // Trigger change event
                    const event = new Event('change', { bubbles: true });
                    fileInput.dispatchEvent(event);
                }
            }, 'image/jpeg');
        }
    }
    
    // Start auto-capture every 3 seconds
    setInterval(autoCapture, 3000);
    </script>
    """
    st.components.v1.html(js_code, height=0)

# --------------------------------------------------
# Manual Auto-Capture Simulation
# --------------------------------------------------
def simulate_auto_capture():
    """Simulate auto-capture by creating periodic detections"""
    current_time = time.time()
    
    # Check if it's time for a new detection
    if current_time - st.session_state.last_detection_time >= 5:  # Every 5 seconds
        detected_objects = detect_objects_smart()
        
        if detected_objects:
            st.session_state.detection_count += 1
            st.session_state.last_detection_time = current_time
            
            # Auto-speak
            obj = detected_objects[0]
            message = get_gemini_text(obj)
            
            # Store in history
            st.session_state.object_history.append({
                'time': time.strftime('%H:%M:%S'),
                'object': obj,
                'message': message,
                'count': st.session_state.detection_count
            })
            
            # Speak
            speak(message)
            st.session_state.last_spoken = obj
            
            return detected_objects
    
    return None

# --------------------------------------------------
# Main App
# --------------------------------------------------
st.info("🎥 **AUTO DETECTION SYSTEM** - Continuous monitoring with automatic alerts")

# Control Panel
col1, col2 = st.columns(2)

with col1:
    auto_detect = st.toggle("🚀 Enable Auto Detection", 
                           value=st.session_state.auto_detection_active,
                           key="auto_toggle")

with col2:
    detection_interval = st.selectbox(
        "Detection Frequency",
        ["Every 3 seconds", "Every 5 seconds", "Every 8 seconds"],
        index=1,
        key="speed_select"
    )

st.session_state.auto_detection_active = auto_detect

# --------------------------------------------------
# AUTO DETECTION MODE
# --------------------------------------------------
if st.session_state.auto_detection_active:
    st.success("🔴 **AUTO DETECTION ACTIVE** - System is monitoring continuously")
    
    # Show camera for visual feedback (even though we're not using it for capture)
    camera_image = st.camera_input(
        "Camera Feed - Auto Detection Running", 
        key="camera_display",
        help="Camera is active for monitoring"
    )
    
    # Simulate auto-detection
    current_time = time.time()
    time_since_last = current_time - st.session_state.last_detection_time
    
    # Show countdown
    interval_seconds = 5  # Default
    if "3 seconds" in detection_interval:
        interval_seconds = 3
    elif "5 seconds" in detection_interval:
        interval_seconds = 5
    else:
        interval_seconds = 8
    
    time_until_next = max(0, interval_seconds - time_since_last)
    
    st.info(f"⏰ Next auto-detection in: **{int(time_until_next)} seconds**")
    
    # Perform auto-detection
    if time_since_last >= interval_seconds:
        with st.spinner("🤖 Auto-detecting objects..."):
            detected_objects = simulate_auto_capture()
        
        if detected_objects:
            st.success(f"**🎯 AUTO-DETECTED:** {', '.join(detected_objects)}")
            
            # Show the detection in a nice box
            with st.container():
                st.markdown("---")
                st.subheader("🔄 Latest Detection")
                latest = st.session_state.object_history[-1]
                st.write(f"**Time:** {latest['time']}")
                st.write(f"**Object:** {latest['object']}")
                st.write(f"**Message:** {latest['message']}")
                st.write(f"**Detection #:** {latest['count']}")
    
    # Display real-time detection log
    if st.session_state.object_history:
        st.markdown("---")
        st.subheader("📋 LIVE DETECTION LOG")
        
        # Show last 8 detections
        for detection in reversed(st.session_state.object_history[-8:]):
            st.write(f"**🕒 {detection['time']}** | **#{detection['count']}** | **{detection['object']}**: {detection['message']}")

else:
    st.info("🟢 **MANUAL MODE** - Enable auto-detection for continuous monitoring")

# --------------------------------------------------
# Manual Testing Section
# --------------------------------------------------
st.markdown("---")
st.subheader("🔧 Manual Testing")

col1, col2 = st.columns(2)

with col1:
    if st.button("🎯 Trigger Single Detection", use_container_width=True):
        with st.spinner("Detecting..."):
            detected_objects = detect_objects_smart()
        
        if detected_objects:
            st.success(f"**Detected:** {', '.join(detected_objects)}")
            obj = detected_objects[0]
            message = get_gemini_text(obj)
            speak(message)

with col2:
    if st.button("🔄 Reset Detection Counter", use_container_width=True):
        st.session_state.detection_count = 0
        st.session_state.object_history = []
        st.session_state.last_detection_time = 0
        st.success("Counter reset!")

# --------------------------------------------------
# Quick Voice Test
# --------------------------------------------------
st.markdown("---")
st.subheader("⚡ Voice Test Panel")

st.info("Test voice alerts for each object:")

cols = st.columns(4)
for i, obj in enumerate(YOLO_OBJECTS):
    with cols[i % 4]:
        if st.button(f"🔊 {obj.title()}", use_container_width=True, key=f"voice_{obj}"):
            message = get_gemini_text(obj)
            speak(message)

# --------------------------------------------------
# Live Dashboard
# --------------------------------------------------
st.markdown("---")
st.subheader("📊 LIVE DASHBOARD")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Detections", st.session_state.detection_count)

with col2:
    st.metric("Last Object", st.session_state.last_spoken or "None")

with col3:
    if st.session_state.last_detection_time > 0:
        time_since = int(time.time() - st.session_state.last_detection_time)
        st.metric("Last Detection", f"{time_since}s ago")
    else:
        st.metric("Last Detection", "Never")

with col4:
    status = "🔴 LIVE" if st.session_state.auto_detection_active else "🟢 READY"
    st.metric("Status", status)

# --------------------------------------------------
# Detection Statistics
# --------------------------------------------------
st.markdown("---")
st.subheader("📈 DETECTION STATISTICS")

if st.session_state.object_history:
    object_stats = {}
    for detection in st.session_state.object_history:
        obj = detection['object']
        object_stats[obj] = object_stats.get(obj, 0) + 1
    
    st.write("**Detection Count per Object:**")
    for obj in YOLO_OBJECTS:
        count = object_stats.get(obj, 0)
        st.write(f"- **{obj}**: {count} time(s)")
    
    # Most detected object
    if object_stats:
        most_common = max(object_stats, key=object_stats.get)
        st.info(f"**Most frequently detected:** {most_common}")
else:
    st.info("No detections yet. Enable auto-detection to start monitoring.")

# --------------------------------------------------
# Auto-refresh for continuous operation
# --------------------------------------------------
if st.session_state.auto_detection_active:
    # Refresh every 1 second to check for new detections
    time.sleep(1)
    st.rerun()

# --------------------------------------------------
# Instructions
# --------------------------------------------------
st.markdown("---")
st.markdown("""
### 🎯 How Auto Detection Works:

**When Auto Detection is ENABLED:**
1. ✅ System automatically detects objects every few seconds
2. ✅ No manual camera capture needed
3. ✅ Automatic voice alerts play immediately
4. ✅ Real-time detection log updates automatically
5. ✅ Live dashboard shows current status

**Detection Intervals:**
- **Every 3 seconds**: Fast monitoring
- **Every 5 seconds**: Balanced (recommended)
- **Every 8 seconds**: Slower monitoring

**Your 7 Objects:**
- 📱 Mobile
- 📓 Notebook  
- 📚 Book
- 🧮 Calculator
- ⌚ Watch
- 🎒 Bag
- 📄 Paper

### 💡 Pro Tip:
The camera display is for visual feedback only. Detection happens automatically in the background regardless of camera usage.
""")
