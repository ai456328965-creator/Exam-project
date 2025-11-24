import streamlit as st
import google.generativeai as genai
from gtts import gTTS
import tempfile
import os
import time
import base64
from PIL import Image
import io
from datetime import datetime

# --------------------------------------------------
# 🔐 Configuration & Security
# --------------------------------------------------
# IMPORTANT: Move API key to Streamlit secrets or environment variables
# For production: st.secrets["GEMINI_API_KEY"] or os.getenv("GEMINI_API_KEY")
API_KEY = st.secrets.get("GEMINI_API_KEY", "AIzaSyDrGWv-nruXtcfcph-XhT7kCkpxsqBHYps")

@st.cache_resource
def initialize_gemini():
    """Initialize Gemini model with caching"""
    genai.configure(api_key=API_KEY)
    return genai.GenerativeModel("gemini-1.5-flash")

gemini_model = initialize_gemini()

# --------------------------------------------------
# Streamlit Page Configuration
# --------------------------------------------------
st.set_page_config(
    page_title="AI Live Detection with Voice",
    page_icon="📷",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for better UI
st.markdown("""
    <style>
    .main-header {
        text-align: center;
        color: #1f77b4;
        padding: 1rem 0;
    }
    .stButton>button {
        width: 100%;
    }
    .detection-box {
        padding: 1rem;
        border-radius: 10px;
        background-color: #f0f2f6;
        margin: 1rem 0;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("<h2 class='main-header'>📷 AI Real-Time Detection with Voice Assistant</h2>", unsafe_allow_html=True)

# --------------------------------------------------
# Helper Functions
# --------------------------------------------------
@st.cache_data(ttl=3600)
def get_gemini_text(obj_name: str) -> str:
    """Generate polite removal message using Gemini with caching"""
    prompt = f"Create one short, polite sentence asking the user to remove the {obj_name}. Be friendly and concise."
    try:
        reply = gemini_model.generate_content(prompt)
        return reply.text.strip()
    except Exception as e:
        st.error(f"Text generation error: {e}")
        return f"Please kindly remove the {obj_name}."

def detect_objects_with_gemini(image: Image.Image) -> list:
    """Detect objects using Gemini Vision API"""
    try:
        prompt = """Analyze this image and identify all visible objects.
        Return ONLY a comma-separated list of objects (maximum 5 main objects).
        Format: object1, object2, object3
        Be specific and accurate. Do not include explanations."""
        
        response = gemini_model.generate_content([prompt, image])
        objects_text = response.text.strip()
        
        # Clean and parse response
        detected_objects = [
            obj.strip().lower() 
            for obj in objects_text.split(',') 
            if obj.strip()
        ]
        
        return detected_objects[:5]  # Limit to 5 objects
        
    except Exception as e:
        st.error(f"❌ Detection error: {str(e)}")
        return []

def speak(text: str) -> None:
    """Generate and play text-to-speech audio"""
    try:
        tts = gTTS(text=text, lang="en", slow=False)
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
            tts.save(tmp_file.name)
            
            with open(tmp_file.name, "rb") as audio_file:
                audio_bytes = audio_file.read()
                audio_base64 = base64.b64encode(audio_bytes).decode()
            
            # Auto-play audio
            st.markdown(
                f'<audio autoplay><source src="data:audio/mp3;base64,{audio_base64}" type="audio/mp3"></audio>',
                unsafe_allow_html=True
            )
            
            # Clean up temp file
            os.unlink(tmp_file.name)
        
        st.success(f"🔊 **Voice:** {text}")
        
    except Exception as e:
        st.warning(f"⚠️ Audio error: {str(e)}")

def should_speak(obj: str, cooldown_seconds: int = 10) -> bool:
    """Check if enough time has passed to speak about this object"""
    current_time = time.time()
    last_obj = st.session_state.get('last_spoken', '')
    last_time = st.session_state.get('last_speak_time', 0)
    
    return (obj != last_obj or current_time - last_time > cooldown_seconds)

# --------------------------------------------------
# Session State Initialization
# --------------------------------------------------
if 'last_spoken' not in st.session_state:
    st.session_state.last_spoken = ""
if 'last_speak_time' not in st.session_state:
    st.session_state.last_speak_time = 0
if 'processing' not in st.session_state:
    st.session_state.processing = False
if 'detection_history' not in st.session_state:
    st.session_state.detection_history = []

# --------------------------------------------------
# Main Interface - Tabs
# --------------------------------------------------
tab1, tab2, tab3 = st.tabs(["📷 Live Camera", "📸 Upload Image", "🛠️ Manual Mode"])

# --------------------------------------------------
# TAB 1: Live Camera Detection
# --------------------------------------------------
with tab1:
    st.info("🎥 **Real-time detection:** Take a picture to detect objects and hear voice alerts")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        camera_image = st.camera_input("Capture Image", key="live_camera")
    
    with col2:
        cooldown = st.slider("Voice cooldown (seconds)", 5, 30, 10)
        auto_detect = st.checkbox("Auto-detect on capture", value=True)
    
    if camera_image and auto_detect:
        if not st.session_state.processing:
            st.session_state.processing = True
            
            try:
                image = Image.open(camera_image)
                
                # Display captured image
                st.image(image, caption="📸 Captured Image", use_column_width=True)
                
                # Detect objects
                with st.spinner("🔍 Analyzing image with AI..."):
                    detected_objects = detect_objects_with_gemini(image)
                
                if detected_objects:
                    st.success(f"✅ **Detected:** {', '.join(detected_objects)}")
                    
                    # Record detection
                    st.session_state.detection_history.append({
                        'time': datetime.now().strftime("%H:%M:%S"),
                        'objects': detected_objects
                    })
                    
                    # Auto-speak for first object
                    obj = detected_objects[0]
                    
                    if should_speak(obj, cooldown):
                        with st.spinner("🎙️ Generating voice message..."):
                            message = get_gemini_text(obj)
                            speak(message)
                        
                        st.session_state.last_spoken = obj
                        st.session_state.last_speak_time = time.time()
                    else:
                        st.info(f"⏱️ Cooldown active for '{obj}'. Wait {cooldown} seconds.")
                else:
                    st.warning("⚠️ No objects detected. Try adjusting lighting or camera angle.")
                    
            except Exception as e:
                st.error(f"❌ Processing error: {str(e)}")
            finally:
                st.session_state.processing = False

# --------------------------------------------------
# TAB 2: Image Upload
# --------------------------------------------------
with tab2:
    st.info("📤 Upload an image file for object detection")
    
    uploaded_file = st.file_uploader("Choose an image", type=['jpg', 'jpeg', 'png', 'webp'])
    
    if uploaded_file:
        image = Image.open(uploaded_file)
        st.image(image, caption="Uploaded Image", use_column_width=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔍 Detect Objects", use_container_width=True):
                with st.spinner("Analyzing..."):
                    detected_objects = detect_objects_with_gemini(image)
                
                if detected_objects:
                    st.session_state.upload_objects = detected_objects
                    st.success(f"✅ Found: {', '.join(detected_objects)}")
                else:
                    st.warning("No objects detected")
        
        # Voice generation for detected objects
        if 'upload_objects' in st.session_state and st.session_state.upload_objects:
            selected_obj = st.selectbox(
                "Select object for voice message:",
                st.session_state.upload_objects
            )
            
            with col2:
                if st.button("🔊 Generate Voice", use_container_width=True):
                    message = get_gemini_text(selected_obj)
                    speak(message)

# --------------------------------------------------
# TAB 3: Manual Mode
# --------------------------------------------------
with tab3:
    st.info("🎯 Manually select objects if automatic detection isn't working")
    
    predefined_objects = [
        "phone", "laptop", "bottle", "cup", "book", 
        "person", "bag", "chair", "table", "glasses",
        "pen", "notebook", "headphones", "mouse", "keyboard"
    ]
    
    manual_objects = st.multiselect(
        "Select objects:",
        predefined_objects,
        help="Choose one or more objects"
    )
    
    if manual_objects:
        selected_manual = st.radio("Choose object for voice message:", manual_objects)
        
        if st.button("🔊 Generate Voice Message", use_container_width=True):
            message = get_gemini_text(selected_manual)
            speak(message)

# --------------------------------------------------
# Sidebar: Detection History & Settings
# --------------------------------------------------
with st.sidebar:
    st.header("⚙️ Settings")
    
    st.markdown("### 📊 Detection History")
    if st.session_state.detection_history:
        for entry in st.session_state.detection_history[-5:]:
            st.text(f"{entry['time']}: {', '.join(entry['objects'])}")
    else:
        st.text("No detections yet")
    
    if st.button("🗑️ Clear History"):
        st.session_state.detection_history = []
        st.rerun()
    
    st.markdown("---")
    st.markdown("### 📖 Instructions")
    st.markdown("""
    **Live Camera:**
    - Allow camera access
    - Point at objects
    - Auto-detection on capture
    
    **Upload Image:**
    - Choose image file
    - Click detect
    - Select object for voice
    
    **Manual Mode:**
    - Select from list
    - Generate voice message
    """)

# --------------------------------------------------
# Footer
# --------------------------------------------------
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
    <p>Powered by Gemini Vision AI & Google Text-to-Speech</p>
    <p style='font-size: 0.8rem;'>⚠️ Remember to secure your API key in production!</p>
</div>
""", unsafe_allow_html=True)
