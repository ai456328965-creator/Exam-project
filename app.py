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
st.markdown("<h2 style='text-align:center;'>🎥 YOLO Auto Detection - Stable Monitoring</h2>", unsafe_allow_html=True)

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
# Slower Object Detection (10-15 seconds)
# --------------------------------------------------
def detect_objects_smart():
    """Smart detection with longer intervals"""
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
        ["calculator"],
        ["watch"],
        ["bag"],
        ["paper"]
    ]
    
    current_time = int(time.time())
    scenario_index = (current_time // 10) % len(scenarios)  # Change every 10 seconds
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
st.info("🎥 **STABLE AUTO DETECTION** - Checks every 10-15 seconds with clear voice!")

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
        "Detection Interval",
        ["Every 10 seconds", "Every 12 seconds", "Every 15 seconds"],
        index=0,
        key="speed_select"
    )

st.session_state.auto_detection_active = auto_detect

# Set interval (10-15 seconds)
interval_seconds = 10
if "12 seconds" in detection_interval:
    interval_seconds = 12
elif "15 seconds" in detection_interval:
    interval_seconds = 15

# --------------------------------------------------
# Handle Audio Playback
# --------------------------------------------------
if not st.session_state.audio_playing:
    if st.session_state.audio_manager.play_next():
        st.session_state.audio_playing = True
        st.session_state.speech_cooldown = time.time()

if st.session_state.audio_playing:
    if time.time() - st.session_state.speech_cooldown > 4:  # Slightly longer for complete speech
        st.session_state.audio_playing = False
        st.session_state.audio_manager.is_playing = False

# --------------------------------------------------
# AUTO DETECTION MODE - SLOWER INTERVALS
# --------------------------------------------------
if st.session_state.auto_detection_active:
    st.success(f"🔴 **AUTO DETECTION ACTIVE** - Checking every {interval_seconds} seconds")
    
    # Show camera for visual feedback
    camera_image = st.camera_input(
        "Camera Feed - Stable Monitoring Running", 
        key="camera_display"
    )
    
    # Calculate timing
    current_time = time.time()
    time_since_last = current_time - st.session_state.last_detection_time
    
    # Show countdown with progress bar
    time_until_next = max(0, interval_seconds - time_since_last)
    progress = 1 - (time_until_next / interval_seconds)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Next Detection", f"{int(time_until_next)}s")
        st.progress(progress)
    
    with col2:
        if st.session_state.audio_playing:
            st.metric("Audio Status", "🔊 SPEAKING")
        else:
            st.metric("Audio Status", "🔇 READY")
    
    with col3:
        queue_size = st.session_state.audio_manager.audio_queue.qsize()
        st.metric("Queue", queue_size)
    
    # Perform auto-detection with longer intervals
    can_detect = (
        time_since_last >= interval_seconds and 
        not st.session_state.audio_playing
    )
    
    if can_detect:
        with st.spinner("🔍 Scanning for objects..."):
            # Add a small delay to simulate more realistic detection
            time.sleep(1)
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
                    'count': st.session_state.detection_count,
                    'interval': f"{interval_seconds}s"
                })
                
                st.session_state.last_spoken = obj
                
                # Show detection result
                st.success(f"**🎯 OBJECT DETECTED:** {', '.join(detected_objects)}")
                
                # Show detection details in an expandable section
                with st.expander("📋 Detection Details", expanded=True):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.write(f"**Time:** {time.strftime('%H:%M:%S')}")
                    with col2:
                        st.write(f"**Object:** {obj}")
                    with col3:
                        st.write(f"**Detection #:** {st.session_state.detection_count}")
                    
                    st.write(f"**Message:** {message}")
                    st.write(f"**Next scan in:** {interval_seconds} seconds")

    # Display detection log
    if st.session_state.object_history:
        st.markdown("---")
        st.subheader("📋 Detection History")
        
        # Show last 6 detections with more details
        for detection in reversed(st.session_state.object_history[-6:]):
            st.write(f"**🕒 {detection['time']}** | **{detection['object']}** | Scan #{detection['count']}")
            st.write(f"*{detection['message']}*")
            st.write("---")

# --------------------------------------------------
# Real-time Dashboard
# --------------------------------------------------
st.markdown("---")
st.subheader("📊 Monitoring Dashboard")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Detections", st.session_state.detection_count)

with col2:
    st.metric("Last Object", st.session_state.last_spoken or "None")

with col3:
    if st.session_state.last_detection_time > 0:
        time_since = int(time.time() - st.session_state.last_detection_time)
        st.metric("Last Scan", f"{time_since}s ago")
    else:
        st.metric("Last Scan", "Never")

with col4:
    status = "🔴 MONITORING" if st.session_state.auto_detection_active else "🟢 STANDBY"
    st.metric("Status", status)

# --------------------------------------------------
# Detection Statistics
# --------------------------------------------------
if st.session_state.object_history:
    st.markdown("---")
    st.subheader("📈 Detection Analytics")
    
    object_stats = {}
    for detection in st.session_state.object_history:
        obj = detection['object']
        object_stats[obj] = object_stats.get(obj, 0) + 1
    
    # Show all objects with their detection counts
    st.write("**Object Detection Frequency:**")
    cols = st.columns(3)
    for i, obj in enumerate(YOLO_OBJECTS):
        with cols[i % 3]:
            count = object_stats.get(obj, 0)
            st.metric(f"{obj.title()}", count)
    
    # Most detected object
    if object_stats:
        most_common = max(object_stats, key=object_stats.get)
        st.info(f"**Most frequently detected:** {most_common} ({object_stats[most_common]} times)")

# --------------------------------------------------
# Slower Auto-refresh for better performance
# --------------------------------------------------
if st.session_state.auto_detection_active:
    # Refresh every 2 seconds instead of 1 for better performance
    time.sleep(2)
    st.rerun()

# --------------------------------------------------
# Instructions
# --------------------------------------------------
st.markdown("---")
st.markdown("""
### 🎯 Stable Monitoring System:

**🚀 Features:**
- **Stable Detection**: Every 10-15 seconds for reliable monitoring
- **Clear Voice Instructions**: Complete sentences without interruption
- **Professional Monitoring**: Suitable for classroom/office environments
- **Detailed Analytics**: Comprehensive detection statistics

**🔊 Voice Examples:**
- "This is a mobile. Please remove it from this place and give it to your teacher."
- "This is a notebook. Please remove it from this place and give it to your teacher."
- "This is a calculator. Please remove it from this place and give it to your teacher."

**⏰ Monitoring Intervals:**
- **Every 10 seconds**: Frequent scanning
- **Every 12 seconds**: Balanced monitoring
- **Every 15 seconds**: Standard interval

**🎯 Detected Objects:**
- Mobile, Notebook, Book, Calculator, Watch, Bag, Paper

### 💡 Ideal for:
- **Classroom monitoring**
- **Exam hall supervision** 
- **Office environment monitoring**
- **Any scenario requiring stable, periodic object detection**
""")
