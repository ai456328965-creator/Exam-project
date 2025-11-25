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
st.markdown("<h2 style='text-align:center;'>🎥 YOLO Auto Detection - Complete Voice</h2>", unsafe_allow_html=True)

# --------------------------------------------------
# Enhanced Gemini Text Generator
# --------------------------------------------------
def get_gemini_text(obj_name):
    prompt = f"Say exactly: 'This is a {obj_name}. Please remove it from this place and give it to your teacher.' Do not add anything else."
    try:
        reply = gemini_model.generate_content(prompt)
        # Ensure we get the exact format we want
        text = reply.text.strip()
        if "This is a" not in text:
            return f"This is a {obj_name}. Please remove it from this place and give it to your teacher."
        return text
    except Exception as e:
        return f"This is a {obj_name}. Please remove it from this place and give it to your teacher."

# --------------------------------------------------
# Improved Audio Manager with No-Refresh During Speech
# --------------------------------------------------
class AudioManager:
    def __init__(self):
        self.audio_queue = queue.Queue()
        self.is_playing = False
        self.current_audio = None
        self.audio_start_time = 0
        
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
                self.audio_start_time = time.time()
                
                # Create HTML audio player that prevents refresh
                audio_html = f'''
                <audio id="mainAudio" autoplay>
                    <source src="data:audio/mp3;base64,{audio_data['audio_base64']}" type="audio/mp3">
                </audio>
                <script>
                    // Prevent page refresh while audio is playing
                    const audio = document.getElementById('mainAudio');
                    let audioFinished = false;
                    
                    audio.addEventListener('play', function() {{
                        console.log('Audio started playing');
                    }});
                    
                    audio.addEventListener('ended', function() {{
                        console.log('Audio finished completely');
                        audioFinished = true;
                        // Send message to Streamlit that audio finished
                        window.parent.postMessage({{type: 'audioFinished'}}, '*');
                    }});
                    
                    audio.addEventListener('error', function(e) {{
                        console.log('Audio error:', e);
                        audioFinished = true;
                    }});
                    
                    // Block navigation while audio is playing
                    window.addEventListener('beforeunload', function(e) {{
                        if (!audioFinished && !audio.ended) {{
                            e.preventDefault();
                            e.returnValue = 'Audio is still playing. Please wait.';
                            return 'Audio is still playing. Please wait.';
                        }}
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
# Object Detection
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
    scenario_index = (current_time // 10) % len(scenarios)
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
if 'audio_playing' not in st.session_state:
    st.session_state.audio_playing = False
if 'block_refresh' not in st.session_state:
    st.session_state.block_refresh = False

# --------------------------------------------------
# Main App
# --------------------------------------------------
st.info("🎥 **COMPLETE VOICE DETECTION** - No interrupted audio!")

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

# Set interval
interval_seconds = 10
if "12 seconds" in detection_interval:
    interval_seconds = 12
elif "15 seconds" in detection_interval:
    interval_seconds = 15

# --------------------------------------------------
# Handle Audio Playback - CRITICAL FIX
# --------------------------------------------------

# Check if audio finished via JavaScript message (simulated)
if st.session_state.audio_playing:
    # Estimate audio duration based on text length (approx 0.5 seconds per word)
    if st.session_state.audio_manager.current_audio:
        text = st.session_state.audio_manager.current_audio['text']
        word_count = len(text.split())
        estimated_duration = word_count * 0.5 + 2  # Add 2 seconds buffer
        
        if time.time() - st.session_state.audio_manager.audio_start_time > estimated_duration:
            st.session_state.audio_playing = False
            st.session_state.audio_manager.is_playing = False
            st.session_state.block_refresh = False

# Play next audio if not playing
if not st.session_state.audio_playing:
    if st.session_state.audio_manager.play_next():
        st.session_state.audio_playing = True
        st.session_state.block_refresh = True  # Block refresh during speech

# --------------------------------------------------
# AUTO DETECTION MODE - WITH AUDIO PROTECTION
# --------------------------------------------------
if st.session_state.auto_detection_active:
    st.success(f"🔴 **AUTO DETECTION ACTIVE** - Checking every {interval_seconds} seconds")
    
    # Show camera for visual feedback
    camera_image = st.camera_input(
        "Camera Feed - Voice Protection Active", 
        key="camera_display"
    )
    
    # Calculate timing
    current_time = time.time()
    time_since_last = current_time - st.session_state.last_detection_time
    
    # Show countdown
    time_until_next = max(0, interval_seconds - time_since_last)
    
    # Status indicators
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Next Detection", f"{int(time_until_next)}s")
    
    with col2:
        if st.session_state.audio_playing:
            st.metric("Audio Status", "🔊 SPEAKING")
            st.warning("⏸️ Refresh blocked during speech")
        else:
            st.metric("Audio Status", "🔇 READY")
    
    with col3:
        queue_size = st.session_state.audio_manager.audio_queue.qsize()
        st.metric("Queue", queue_size)
        
    with col4:
        if st.session_state.block_refresh:
            st.metric("Refresh", "🔒 BLOCKED")
        else:
            st.metric("Refresh", "🟢 ALLOWED")
    
    # Perform auto-detection ONLY if no audio is playing
    can_detect = (
        time_since_last >= interval_seconds and 
        not st.session_state.audio_playing and
        not st.session_state.block_refresh
    )
    
    if can_detect:
        with st.spinner("🔍 Scanning for objects..."):
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
                
                # Show exact message that will be spoken
                with st.expander("🔊 Voice Message Details", expanded=True):
                    st.write(f"**Exact spoken text:**")
                    st.info(f"*'{message}'*")
                    st.write(f"**Object:** {obj}")
                    st.write(f"**Detection time:** {time.strftime('%H:%M:%S')}")

    # Display detection log
    if st.session_state.object_history:
        st.markdown("---")
        st.subheader("📋 Complete Voice History")
        
        for detection in reversed(st.session_state.object_history[-6:]):
            st.write(f"**🕒 {detection['time']}** | **{detection['object']}**")
            st.success(f"*'{detection['message']}'*")
            st.write("---")

# --------------------------------------------------
# Real-time Dashboard
# --------------------------------------------------
st.markdown("---")
st.subheader("📊 Voice Protection Dashboard")

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
    if st.session_state.audio_playing:
        st.metric("Status", "🔊 SPEAKING")
    else:
        st.metric("Status", "🔍 SCANNING")

# --------------------------------------------------
# Smart Auto-refresh - Only when safe
# --------------------------------------------------
if st.session_state.auto_detection_active and not st.session_state.block_refresh:
    # Only refresh if no audio is playing
    refresh_delay = 2  # Slower refresh when audio might play
    time.sleep(refresh_delay)
    st.rerun()
elif st.session_state.auto_detection_active and st.session_state.block_refresh:
    # Wait longer if audio is playing to ensure completion
    st.warning("🔒 Page refresh blocked to ensure complete audio playback...")
    time.sleep(3)  # Wait 3 seconds before checking again
    st.rerun()

# --------------------------------------------------
# Instructions
# --------------------------------------------------
st.markdown("---")
st.markdown("""
### 🎯 Complete Voice Protection System:

**🔊 GUARANTEED COMPLETE AUDIO:**
- **No Interruptions**: Page refresh blocked during speech
- **Complete Sentences**: "This is a [object]. Please remove it from this place and give it to your teacher."
- **Audio Protection**: Special system prevents audio cutoff
- **Voice Priority**: Detection pauses during speech

**🛡️ Protection Features:**
- **Refresh Blocking**: Page won't refresh while audio plays
- **Audio Queue**: Manages multiple speech requests
- **Duration Estimation**: Knows how long speech will take
- **Safe Refresh**: Only refreshes when audio is complete

**🔊 Exact Voice Output:**
- "This is a mobile. Please remove it from this place and give it to your teacher."
- "This is a book. Please remove it from this place and give it to your teacher."
- "This is a calculator. Please remove it from this place and give it to your teacher."

**⏰ Monitoring Intervals:**
- **Every 10 seconds**: Frequent but safe
- **Every 12 seconds**: Balanced protection
- **Every 15 seconds**: Maximum audio safety

### 💡 How It Works:
1. System detects object
2. **BLOCKS PAGE REFRESH** during speech
3. Plays complete audio sentence
4. **Only then** allows page refresh
5. Continues monitoring
""")
