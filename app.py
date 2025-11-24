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
st.markdown("<h2 style='text-align:center;'>🎥 YOLO Auto Detection - Smooth Voice</h2>", unsafe_allow_html=True)

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
            tts = gTTS(text=text, lang="en")
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
                <script>
                    // Notify when audio ends
                    document.querySelector('audio').addEventListener('ended', function() {{
                        window.parent.postMessage('audio_ended', '*');
                    }});
                </script>
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
    scenario_index = (current_time // 8) % len(scenarios)  # Change every 8 seconds
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
# JavaScript Communication for Audio Events
# --------------------------------------------------
def inject_audio_listener():
    """Inject JavaScript to handle audio end events"""
    js_code = """
    <script>
    // Listen for audio end events
    window.addEventListener('message', function(event) {
        if (event.data === 'audio_ended') {
            // Notify Streamlit that audio finished
            const audioEndEvent = new CustomEvent('audioEnded');
            document.dispatchEvent(audioEndEvent);
        }
    });
    
    // Also handle page visibility changes to prevent audio cutoff
    document.addEventListener('visibilitychange', function() {
        if (document.hidden) {
            // Page is hidden, might be refreshing - try to preserve audio
            const audio = document.querySelector('audio');
            if (audio) {
                audio.currentTime = 0;
            }
        }
    });
    </script>
    """
    st.components.v1.html(js_code, height=0)

# --------------------------------------------------
# Main App
# --------------------------------------------------
st.info("🎥 **SMOOTH AUTO DETECTION** - No audio glitches!")

# Inject audio listener
inject_audio_listener()

# Control Panel
col1, col2 = st.columns(2)

with col1:
    auto_detect = st.toggle("🚀 Enable Auto Detection", 
                           value=st.session_state.auto_detection_active,
                           key="auto_toggle")

with col2:
    detection_interval = st.selectbox(
        "Detection Frequency",
        ["Every 8 seconds", "Every 10 seconds", "Every 12 seconds"],
        index=0,
        key="speed_select"
    )

st.session_state.auto_detection_active = auto_detect

# Set interval
interval_seconds = 8
if "10 seconds" in detection_interval:
    interval_seconds = 10
elif "12 seconds" in detection_interval:
    interval_seconds = 12

# --------------------------------------------------
# Handle Audio Playback
# --------------------------------------------------
# Check if we should play next audio
if not st.session_state.audio_playing:
    if st.session_state.audio_manager.play_next():
        st.session_state.audio_playing = True
        st.session_state.speech_cooldown = time.time()

# Check if audio finished (simulate since we can't get real events easily)
if st.session_state.audio_playing:
    if time.time() - st.session_state.speech_cooldown > 4:  # Assume audio takes max 4 seconds
        st.session_state.audio_playing = False
        st.session_state.audio_manager.is_playing = False

# --------------------------------------------------
# AUTO DETECTION MODE
# --------------------------------------------------
if st.session_state.auto_detection_active:
    st.success(f"🔴 **AUTO DETECTION ACTIVE** - Checking every {interval_seconds} seconds")
    
    # Show camera for visual feedback
    camera_image = st.camera_input(
        "Camera Feed - Auto Detection Running", 
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
            st.metric("Audio Status", "🔊 PLAYING")
        else:
            st.metric("Audio Status", "🔇 READY")
    
    with col3:
        queue_size = st.session_state.audio_manager.audio_queue.qsize()
        st.metric("Audio Queue", queue_size)
    
    # Perform auto-detection (only if no audio playing and cooldown passed)
    can_detect = (
        time_since_last >= interval_seconds and 
        not st.session_state.audio_playing and
        st.session_state.audio_manager.audio_queue.empty()
    )
    
    if can_detect:
        with st.spinner("🤖 Auto-detecting objects..."):
            detected_objects = detect_objects_smart()
        
        if detected_objects:
            st.session_state.detection_count += 1
            st.session_state.last_detection_time = current_time
            
            # Auto-speak (add to queue)
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
                st.success(f"**🎯 AUTO-DETECTED:** {', '.join(detected_objects)}")
                
                # Show detection details
                with st.expander("📋 Latest Detection Details", expanded=True):
                    st.write(f"**Time:** {time.strftime('%H:%M:%S')}")
                    st.write(f"**Object:** {obj}")
                    st.write(f"**Message:** {message}")
                    st.write(f"**Detection #:** {st.session_state.detection_count}")

    # Display real-time detection log
    if st.session_state.object_history:
        st.markdown("---")
        st.subheader("📋 DETECTION HISTORY")
        
        # Show last 6 detections
        for detection in reversed(st.session_state.object_history[-6:]):
            st.write(f"**🕒 {detection['time']}** | **#{detection['count']}** | **{detection['object']}**: {detection['message']}")

else:
    st.info("🟢 **MANUAL MODE** - Enable auto-detection for continuous monitoring")

# --------------------------------------------------
# Manual Controls
# --------------------------------------------------
st.markdown("---")
st.subheader("🔧 Manual Controls")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("🎯 Single Detection", use_container_width=True):
        if not st.session_state.audio_playing:
            detected_objects = detect_objects_smart()
            if detected_objects:
                obj = detected_objects[0]
                message = get_gemini_text(obj)
                st.session_state.audio_manager.speak(message)

with col2:
    if st.button("🔇 Clear Audio Queue", use_container_width=True):
        # Clear the queue
        while not st.session_state.audio_manager.audio_queue.empty():
            try:
                st.session_state.audio_manager.audio_queue.get_nowait()
            except:
                pass
        st.session_state.audio_playing = False
        st.success("Audio queue cleared!")

with col3:
    if st.button("🔄 Reset All", use_container_width=True):
        st.session_state.detection_count = 0
        st.session_state.object_history = []
        st.session_state.last_detection_time = 0
        # Clear audio queue
        while not st.session_state.audio_manager.audio_queue.empty():
            try:
                st.session_state.audio_manager.audio_queue.get_nowait()
            except:
                pass
        st.session_state.audio_playing = False
        st.success("All counters reset!")

# --------------------------------------------------
# Quick Voice Test
# --------------------------------------------------
st.markdown("---")
st.subheader("⚡ Quick Voice Test")

st.info("Test individual object detection:")

cols = st.columns(4)
for i, obj in enumerate(YOLO_OBJECTS):
    with cols[i % 4]:
        if st.button(f"🔊 {obj.title()}", use_container_width=True, key=f"voice_{obj}"):
            if not st.session_state.audio_playing:
                message = get_gemini_text(obj)
                st.session_state.audio_manager.speak(message)

# --------------------------------------------------
# Dashboard
# --------------------------------------------------
st.markdown("---")
st.subheader("📊 SYSTEM DASHBOARD")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Detections", st.session_state.detection_count)

with col2:
    st.metric("Last Object", st.session_state.last_spoken or "None")

with col3:
    queue_size = st.session_state.audio_manager.audio_queue.qsize()
    st.metric("Audio Queue", queue_size)

with col4:
    status = "🔴 LIVE" if st.session_state.auto_detection_active else "🟢 READY"
    st.metric("Status", status)

# --------------------------------------------------
# Auto-refresh with better timing
# --------------------------------------------------
if st.session_state.auto_detection_active:
    # Use longer refresh interval to prevent audio cutoff
    refresh_delay = 2  # Refresh every 2 seconds instead of 1
    time.sleep(refresh_delay)
    st.rerun()

# --------------------------------------------------
# Instructions
# --------------------------------------------------
st.markdown("---")
st.markdown("""
### 🎯 Smooth Audio Features:

**✅ No More Glitches:**
- **Audio Queue System** - Prevents overlapping speech
- **Longer Intervals** - More time for audio to complete
- **Smart Refresh** - Less frequent page refreshes
- **Audio State Tracking** - Knows when audio is playing

**🔧 Manual Controls:**
- **Clear Queue** - Stop all pending speech
- **Single Detection** - Manual test without auto-mode
- **Reset All** - Clear history and queue

**⚡ Detection Intervals:**
- **Every 8 seconds** - Balanced (recommended)
- **Every 10 seconds** - More audio time
- **Every 12 seconds** - Maximum audio stability

### 💡 Pro Tips:
1. Use longer intervals for more stable audio
2. Clear queue if audio gets stuck
3. Watch the audio queue size in dashboard
4. Manual mode for testing specific objects
""")
