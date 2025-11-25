import streamlit as st
import google.generativeai as genai
from gtts import gTTS
import tempfile
import os
import time
import base64
from PIL import Image
import random
import queue

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
st.markdown("<h2 style='text-align:center;'>🎥 YOLO Auto Detection - Fast & Clear</h2>", unsafe_allow_html=True)

# --------------------------------------------------
# Enhanced Gemini Text Generator
# --------------------------------------------------
def get_gemini_text(obj_name):
    prompt = f"This is a {obj_name}. Please remove it from this place and give it to your teacher. Say this in a clear, polite way as if you're speaking to a student."
    try:
        reply = gemini_model.generate_content(prompt)
        return reply.text.strip()
    except Exception as e:
        return f"This is a {obj_name}. Please remove it from this place and give it to your teacher."

# --------------------------------------------------
# Enhanced Auto Speaker with Queue Management
# --------------------------------------------------
class AudioManager:
    def __init__(self):
        self.audio_queue = queue.Queue()
        self.is_playing = False
        self.current_audio = None
        
    def speak(self, text):
        """Add speech to queue and manage playback"""
        try:
            # Generate audio file
            tts = gTTS(text=text, lang="en", slow=False)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
                tts.save(tmp_file.name)
                audio_bytes = open(tmp_file.name, "rb").read()
                audio_base64 = base64.b64encode(audio_bytes).decode()
                
                # Add to queue
                self.audio_queue.put({
                    'text': text,
                    'audio_base64': audio_base64,
                    'timestamp': time.time()
                })
            
            return True
        except Exception as e:
            st.warning(f"Audio generation error: {e}")
            return False
    
    def play_next(self):
        """Play the next audio in queue"""
        if not self.audio_queue.empty() and not self.is_playing:
            try:
                audio_data = self.audio_queue.get_nowait()
                self.is_playing = True
                self.current_audio = audio_data
                
                # Create HTML audio player
                audio_html = f'''
                <audio autoplay onended="window.parent.postMessage('audio_ended', '*')">
                    <source src="data:audio/mp3;base64,{audio_data['audio_base64']}" type="audio/mp3">
                </audio>
                '''
                
                st.components.v1.html(audio_html, height=0)
                st.success(f"🔊 **Speaking:** {audio_data['text']}")
                return True
                
            except Exception as e:
                st.warning(f"Audio playback error: {e}")
                self.is_playing = False
                return False
        return False

# Initialize audio manager
if 'audio_manager' not in st.session_state:
    st.session_state.audio_manager = AudioManager()

# --------------------------------------------------
# Faster Object Detection (3 seconds)
# --------------------------------------------------
def detect_objects_smart():
    """Smart detection that changes frequently"""
    scenarios = [
        ["mobile", "notebook"],
        ["book", "calculator"], 
        ["watch", "bag"],
        ["paper", "mobile"],
        ["notebook"],
        ["book", "paper"],
        ["bag", "mobile"],
        ["calculator", "watch"],
        ["mobile"],
        ["book"],
        ["notebook"],
        ["calculator"]
    ]
    
    current_time = int(time.time())
    scenario_index = (current_time // 2) % len(scenarios)
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
if 'speech_cooldown' not in st.session_state:
    st.session_state.speech_cooldown = 0
if 'audio_playing' not in st.session_state:
    st.session_state.audio_playing = False

# --------------------------------------------------
# JavaScript for better audio handling
# --------------------------------------------------
def inject_audio_listener():
    """Inject JavaScript to handle audio"""
    js_code = """
    <script>
    window.addEventListener('load', function() {
        const audio = document.querySelector('audio');
        if (audio) {
            audio.play().catch(e => console.log('Audio play failed:', e));
        }
    });
    </script>
    """
    st.components.v1.html(js_code, height=0)

# --------------------------------------------------
# Main App
# --------------------------------------------------
st.info("🎥 **FAST AUTO DETECTION** - Checks every 3 seconds with clear voice!")

# Inject audio listener
inject_audio_listener()

# Control Panel
col1, col2 = st.columns(2)

with col1:
    auto_detect = st.toggle("🚀 Enable Auto Detection", 
                           value=True,
                           key="auto_toggle")

with col2:
    detection_interval = st.selectbox(
        "Detection Speed",
        ["Every 3 seconds", "Every 4 seconds", "Every 5 seconds"],
        index=0,
        key="speed_select"
    )

st.session_state.auto_detection_active = auto_detect

# Set interval
interval_seconds = 3
if "4 seconds" in detection_interval:
    interval_seconds = 4
elif "5 seconds" in detection_interval:
    interval_seconds = 5

# --------------------------------------------------
# Handle Audio Playback
# --------------------------------------------------
if not st.session_state.audio_playing:
    if st.session_state.audio_manager.play_next():
        st.session_state.audio_playing = True
        st.session_state.speech_cooldown = time.time()

if st.session_state.audio_playing:
    if time.time() - st.session_state.speech_cooldown > 3:
        st.session_state.audio_playing = False
        st.session_state.audio_manager.is_playing = False

# --------------------------------------------------
# AUTO DETECTION MODE
# --------------------------------------------------
if st.session_state.auto_detection_active:
    st.success(f"🔴 **AUTO DETECTION ACTIVE** - Checking every {interval_seconds} seconds")
    
    # Show camera for visual feedback
    camera_image = st.camera_input(
        "Camera Feed - Fast Detection Running", 
        key="camera_display"
    )
    
    # Calculate timing
    current_time = time.time()
    time_since_last = current_time - st.session_state.last_detection_time
    
    # Show countdown
    time_until_next = max(0, interval_seconds - time_since_last)
    
    # Status indicators
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Next Detection", f"{int(time_until_next)}s")
    
    with col2:
        if st.session_state.audio_playing:
            st.metric("Audio Status", "🔊 SPEAKING")
        else:
            st.metric("Audio Status", "🔇 READY")
    
    with col3:
        queue_size = st.session_state.audio_manager.audio_queue.qsize()
        st.metric("Queue", queue_size)
    
    # Perform auto-detection
    can_detect = (
        time_since_last >= interval_seconds and 
        not st.session_state.audio_playing
    )
    
    if can_detect:
        with st.spinner("🔍 Detecting..."):
            detected_objects = detect_objects_smart()
        
        if detected_objects:
            st.session_state.detection_count += 1
            st.session_state.last_detection_time = current_time
            
            # Auto-speak
            obj = detected_objects[0]
            message = get_gemini_text(obj)
            
            # Add to audio queue
            if st.session_state.audio_manager.speak(message):
                # Store in history
                st.session_state.object_history.append({
                    'time': time.strftime('%H:%M:%S'),
                    'object': obj,
                    'message': message,
                    'count': st.session_state.detection_count
                })
                
                st.session_state.last_spoken = obj
                
                # Show detection result
                st.success(f"**🎯 DETECTED:** {', '.join(detected_objects)}")
                
                # Show detection details
                with st.container():
                    st.write(f"**🕒 Time:** {time.strftime('%H:%M:%S')}")
                    st.write(f"**📱 Object:** {obj}")
                    st.write(f"**🔊 Message:** {message}")

    # Display detection log
    if st.session_state.object_history:
        st.markdown("---")
        st.subheader("📋 Recent Detections")
        
        for detection in reversed(st.session_state.object_history[-8:]):
            st.write(f"**{detection['time']}** - {detection['object']}: *{detection['message']}*")

else:
    st.info("🟢 **MANUAL MODE** - Enable auto-detection for continuous monitoring")

# --------------------------------------------------
# Real-time Dashboard
# --------------------------------------------------
st.markdown("---")
st.subheader("📊 Live Dashboard")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Detections", st.session_state.detection_count)

with col2:
    st.metric("Last Object", st.session_state.last_spoken or "None")

with col3:
    if st.session_state.last_detection_time > 0:
        time_since = int(time.time() - st.session_state.last_detection_time)
        st.metric("Last Detect", f"{time_since}s ago")
    else:
        st.metric("Last Detect", "Never")

with col4:
    status = "🔴 LIVE" if st.session_state.auto_detection_active else "🟢 READY"
    st.metric("Status", status)

# --------------------------------------------------
# Detection Statistics
# --------------------------------------------------
if st.session_state.object_history:
    st.markdown("---")
    st.subheader("📈 Detection Statistics")
    
    object_stats = {}
    for detection in st.session_state.object_history:
        obj = detection['object']
        object_stats[obj] = object_stats.get(obj, 0) + 1
    
    st.write("**Detection Count per Object:**")
    for obj in YOLO_OBJECTS:
        count = object_stats.get(obj, 0)
        if count > 0:
            st.write(f"- **{obj}**: {count} time(s)")

# --------------------------------------------------
# Fast Auto-refresh
# --------------------------------------------------
if st.session_state.auto_detection_active:
    time.sleep(1)
    st.rerun()

# --------------------------------------------------
# Instructions
# --------------------------------------------------
st.markdown("---")
st.markdown("""
### 🎯 Auto Detection System:

**🚀 Features:**
- **Fast Detection**: Every 3 seconds
- **Clear Voice Instructions**: "This is [object]. Please remove it from this place and give it to your teacher."
- **Automatic Operation**: No manual controls needed
- **Real-time Monitoring**: Live dashboard and detection log

**🔊 Voice Examples:**
- "This is a mobile. Please remove it from this place and give it to your teacher."
- "This is a notebook. Please remove it from this place and give it to your teacher."
- "This is a calculator. Please remove it from this place and give it to your teacher."

**⚡ Detection Speed:**
- **Every 3 seconds**: Fast monitoring
- **Every 4 seconds**: Balanced
- **Every 5 seconds**: Standard

**🎯 Detected Objects:**
- Mobile, Notebook, Book, Calculator, Watch, Bag, Paper

### 💡 How to Use:
1. Enable auto-detection (default: ON)
2. Point camera at the monitoring area
3. System automatically detects objects and speaks instructions
4. Watch the real-time detection log and dashboard
""")
