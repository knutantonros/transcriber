# Python imports
import os
import streamlit as st
import hashlib
import tempfile
from PIL import Image

# External imports
from docx import Document
from pydub import AudioSegment

# Local imports
from utils.audio_utils import convert_to_mono_and_compress
from utils.transcribe import transcribe_with_kb_whisper
from utils.summarize import summarize_text_openai
import config as c

### INITIAL VARIABLES

# Create directories if they don't exist
# Use absolute paths to avoid issues in different environments
base_dir = os.path.dirname(os.path.abspath(__file__))
audio_dir = os.path.join(base_dir, "audio")
text_dir = os.path.join(base_dir, "text")

os.makedirs(audio_dir, exist_ok=True)  # Where audio files are stored for transcription
os.makedirs(text_dir, exist_ok=True)   # Where transcribed documents are stored

# Check and set default values if they don't exist in session_state
if "transcribed" not in st.session_state:  # Transcription result
    st.session_state["transcribed"] = None
if "summarized" not in st.session_state:  # Summarization result
    st.session_state["summarized"] = None
if "transcribe_model" not in st.session_state:  # Which Whisper model to use
    st.session_state["transcribe_model"] = "KB Whisper Tiny"
if "file_name_converted" not in st.session_state:  # Audio file name
    st.session_state["file_name_converted"] = None

# Check if uploaded audio file has been transcribed
def compute_file_hash(uploaded_file):
    """Calculate MD5 hash for a file to check if it has changed"""
    hasher = hashlib.md5()
    
    for chunk in iter(lambda: uploaded_file.read(4096), b""):
        hasher.update(chunk)
    uploaded_file.seek(0)  # Reset file pointer to beginning
    
    return hasher.hexdigest()

### MAIN APP ###########################

# Page configuration
st.set_page_config(
    page_title="Audio Transcription & Summarization",
    page_icon="🎙️",
    layout="centered",
    initial_sidebar_state="auto"
)

# Disable the PyTorch file watcher which is causing problems
os.environ["STREAMLIT_GLOBAL_WATCHER_MAX_FILE_SIZE"] = "0"

def main():
    ### SIDEBAR
    
    st.sidebar.header("Settings")
    st.sidebar.markdown("")
    
    # Text input for OpenAI API key
    api_key = st.sidebar.text_input(
        "Enter your OpenAI API key for summarization",
        type="password",
        help="Required for the summarization function. Your API key is only stored in your active session and is not sent to any server except OpenAI."
    )
    
    # Save API key in session
    if api_key:
        st.session_state["openai_api_key"] = api_key
    
    # Dropdown menu - select Whisper model
    transcribe_model = st.sidebar.selectbox(
        "Select transcription model", 
        [
            "KB Whisper Tiny",
            "KB Whisper Base",
            "KB Whisper Small",
            "KB Whisper Medium", 
            "KB Whisper Large"
        ],
        index=[
            "KB Whisper Tiny",
            "KB Whisper Base",
            "KB Whisper Small",
            "KB Whisper Medium", 
            "KB Whisper Large"
        ].index(st.session_state["transcribe_model"]),
        help="Smaller models (Tiny, Base) are faster but less accurate. Larger models (Medium, Large) are slower but more accurate."
    )
    
    model_map_transcribe_model = {
        "KB Whisper Large": "kb-whisper-large",
        "KB Whisper Medium": "kb-whisper-medium",
        "KB Whisper Small": "kb-whisper-small",
        "KB Whisper Base": "kb-whisper-base",
        "KB Whisper Tiny": "kb-whisper-tiny"
    }
    
    # Options for summary length
    summary_length = st.sidebar.select_slider(
        "Summary length",
        options=["Very short", "Short", "Medium", "Long", "Very long"],
        value="Medium"
    )
    
    # Update session_state
    st.session_state["transcribe_model"] = transcribe_model
    
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"Version: {c.app_version}")
    
    ### MAIN PAGE
    
    # Title
    st.title("Audio Transcription & Summarization")
    st.markdown("### Upload audio files and get transcription + summary")
    
    st.markdown(f"""**Selected model:** {st.session_state["transcribe_model"]}""")
    
    # Show API key information
    if not st.session_state.get("openai_api_key"):
        st.info("📝 **No OpenAI API key provided.** Transcription will work, but to get a summary you need to enter an API key in the sidebar.")
    else:
        st.success("✅ **OpenAI API key is configured.** Summarization function is enabled.")
    
    
    # CREATE TWO TABS FOR FILE UPLOAD AND RECORDING    
    tab1, tab2 = st.tabs(["Upload file", "Record audio"])
    
    # FILE UPLOADER
    with tab1:
        uploaded_file = st.file_uploader(
            "Upload your audio or video file",
            type=["mp3", "wav", "flac", "mp4", "m4a", "aifc"],
            help="Max 2GB file size",
        )
        
        if uploaded_file:
            # Check if uploaded file has already been transcribed
            current_file_hash = compute_file_hash(uploaded_file)
            
            # If uploaded file hash is different than the one in session state, reset state
            if "file_hash" not in st.session_state or st.session_state.file_hash != current_file_hash:
                st.session_state.file_hash = current_file_hash
                
                if "transcribed" in st.session_state:
                    st.session_state.transcribed = None
                if "summarized" in st.session_state:
                    st.session_state.summarized = None
            
            # If audio has not been transcribed
            if st.session_state.transcribed is None:
                # Button to start processing
                if st.button("Transcribe and summarize"):
                    # Send audio for conversion to mp3 and compression
                    with st.spinner('Compressing audio file...'):
                        st.session_state.file_name_converted = convert_to_mono_and_compress(uploaded_file, uploaded_file.name, audio_dir)
                        if not st.session_state.file_name_converted:
                            st.error("Could not process the audio file. Check the file format and that ffmpeg is installed.")
                            return
                        st.success('Audio compressed. Starting transcription.')
                    
                    # Transcribe audio with KB Whisper
                    with st.spinner('Transcribing... This may take a while depending on the length of the recording...'):
                        # Create progress bar
                        progress_bar = st.progress(0)
                        
                        # Create callback function to update progress bar
                        def update_progress(progress_value):
                            progress_bar.progress(progress_value)
                        
                        # Call the transcription function with progress_callback
                        st.session_state.transcribed = transcribe_with_kb_whisper(
                            st.session_state.file_name_converted, 
                            uploaded_file.name, 
                            model_map_transcribe_model[st.session_state["transcribe_model"]],
                            "sv",
                            text_dir,
                            update_progress
                        )
                        
                        # Set progress bar to 100% when done
                        progress_bar.progress(1.0)
                        
                        st.success('Transcription complete.')
                    
                    # Summarize the transcribed text with OpenAI
                    with st.spinner('Summarizing the transcription...'):
                        st.session_state.summarized = summarize_text_openai(
                            st.session_state.transcribed, 
                            summary_length,
                            st.session_state.get("openai_api_key")
                        )
                        st.success('Summarization complete.')
                        
                    st.balloons()
            
            # If we have transcribed and summarized text
            if st.session_state.transcribed is not None:
                # Create a Word document with the transcribed text
                document = Document()
                clean_text = st.session_state.transcribed.encode('utf-8', errors='replace').decode('utf-8')
                document.add_paragraph(clean_text)
                
                if st.session_state.summarized:
                    document.add_paragraph("\n\nSUMMARY:\n" + st.session_state.summarized)
                
                document.save(os.path.join(text_dir, uploaded_file.name + '.docx'))
                
                # Save text file
                with open(os.path.join(text_dir, uploaded_file.name + '.txt'), 'w', encoding='utf-8') as txt_file:
                    txt_file.write(clean_text)
                    if st.session_state.summarized:
                        txt_file.write("\n\nSUMMARY:\n" + st.session_state.summarized)
                
                with open(os.path.join(text_dir, uploaded_file.name + ".docx"), "rb") as docx_file:
                    docx_bytes = docx_file.read()
                
                # Create columns for download buttons
                col1, col2 = st.columns(2)
                
                # Text download
                with col1:
                    with open(os.path.join(text_dir, uploaded_file.name + '.txt'), "rb") as file_txt:
                        st.download_button(
                            label = "Download as Text",
                            data = file_txt,
                            file_name = uploaded_file.name + '.txt',
                            mime = 'text/plain',
                        )
                
                # Word download
                with col2:
                    st.download_button(
                        label = "Download as Word",
                        data = docx_bytes,
                        file_name = uploaded_file.name + '.docx',
                        mime = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                    )
                
                # Show audio
                st.markdown("### Audio File")
                if st.session_state.file_name_converted is not None:
                    st.audio(st.session_state.file_name_converted, format='audio/wav')
                
                # Show transcription
                st.markdown("### Transcription")
                st.write(st.session_state.transcribed)
                
                # Show summary
                if st.session_state.summarized:
                    st.markdown("### Summary")
                    st.write(st.session_state.summarized)
    
    # AUDIO RECORDER
    with tab2:
        audio = st.audio_input("Record audio")
        
        if audio:
            # Open the saved audio file and calculate its hash
            current_file_hash = compute_file_hash(audio)
            
            # If uploaded file hash is different than the one in session state, reset state
            if "file_hash" not in st.session_state or st.session_state.file_hash != current_file_hash:
                st.session_state.file_hash = current_file_hash
                
                if "transcribed" in st.session_state:
                    st.session_state.transcribed = None
                if "summarized" in st.session_state:
                    st.session_state.summarized = None
            
            # If audio has not been transcribed
            if st.session_state.transcribed is None:
                # Button to start processing
                if st.button("Process recording"):
                    # Create a temporary file to save the recording
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.webm') as tmp_file:
                        tmp_file.write(audio.getvalue())
                        tmp_path = tmp_file.name
                    
                    try:
                        audio_file = AudioSegment.from_file(tmp_path)
                        output_path = os.path.join(audio_dir, "recording.mp3")
                        audio_file.export(output_path, format="mp3", bitrate="16k")
                        os.unlink(tmp_path)  # Remove temporary file
                    except Exception as e:
                        st.error(f"Could not process the recording: {e}")
                        if os.path.exists(tmp_path):
                            os.unlink(tmp_path)
                        return
                    
                    # Transcribe
                    with st.spinner('Transcribing... This may take a while depending on the length of the recording...'):
                        # Create progress bar
                        progress_bar = st.progress(0)
                        
                        # Create callback function to update progress bar
                        def update_progress(progress_value):
                            progress_bar.progress(progress_value)
                        
                        # Call the transcription function with progress_callback
                        st.session_state.transcribed = transcribe_with_kb_whisper(
                            output_path, 
                            "recording.mp3", 
                            model_map_transcribe_model[st.session_state["transcribe_model"]],
                            "sv",
                            text_dir,
                            update_progress
                        )
                        
                        # Set progress bar to 100% when done
                        progress_bar.progress(1.0)
                        
                        st.success('Transcription complete.')
                    
                    # Summarize
                    with st.spinner('Summarizing the transcription...'):
                        st.session_state.summarized = summarize_text_openai(
                            st.session_state.transcribed, 
                            summary_length,
                            st.session_state.get("openai_api_key")
                        )
                        st.success('Summarization complete.')
                    
                    st.balloons()
            
            # If we have transcribed and summarized text
            if st.session_state.transcribed is not None:
                recording_name = "recording.mp3"
                document = Document()
                clean_text = st.session_state.transcribed.encode('utf-8', errors='replace').decode('utf-8')
                document.add_paragraph(clean_text)
                
                if st.session_state.summarized:
                    document.add_paragraph("\n\nSUMMARY:\n" + st.session_state.summarized)
                
                document.save(os.path.join(text_dir, recording_name + '.docx'))
                
                # Save text file
                with open(os.path.join(text_dir, recording_name + '.txt'), 'w', encoding='utf-8') as txt_file:
                    txt_file.write(clean_text)
                    if st.session_state.summarized:
                        txt_file.write("\n\nSUMMARY:\n" + st.session_state.summarized)
                
                with open(os.path.join(text_dir, recording_name + '.docx'), "rb") as docx_file:
                    docx_bytes = docx_file.read()
                
                # Create columns for download buttons
                col1, col2 = st.columns(2)
                
                # Text download
                with col1:
                    with open(os.path.join(text_dir, recording_name + '.txt'), "rb") as file_txt:
                        st.download_button(
                            label = "Download as Text",
                            data = file_txt,
                            file_name = recording_name + '.txt',
                            mime = 'text/plain',
                        )
                
                # Word download
                with col2:
                    st.download_button(
                        label = "Download as Word",
                        data = docx_bytes,
                        file_name = recording_name + '.docx',
                        mime = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                    )
                
                # Show transcription
                st.markdown("### Transcription")
                st.write(st.session_state.transcribed)
                
                # Show summary
                if st.session_state.summarized:
                    st.markdown("### Summary")
                    st.write(st.session_state.summarized)

if __name__ == "__main__":
    main()
