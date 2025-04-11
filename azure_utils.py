import os
import streamlit as st

def get_openai_api_key():
    """Get OpenAI API key from environment variable or session state"""
    # First check environment variable
    api_key = os.getenv("OPENAI_API_KEY")
    
    # Then check session state (from sidebar input)
    if not api_key and "openai_api_key" in st.session_state:
        api_key = st.session_state["openai_api_key"]
        
    return api_key
