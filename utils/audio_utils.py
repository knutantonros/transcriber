### Ljudhjälpfunktioner

import os
import streamlit as st
from pydub import AudioSegment

# Konverterar och komprimerar ljud- eller videofil till mp3 och en mer hanterbar storlek
def convert_to_mono_and_compress(uploaded_file, file_name, target_size_MB=22):
    """
    Konvertera uppladdad ljud/videofil till mono MP3 och komprimera den till en målstorlek
    
    Parametrar:
    uploaded_file (UploadedFile): Det uppladdade filobjektet från Streamlit
    file_name (str): Filens namn
    target_size_MB (int): Målstorlek i MB för den komprimerade filen
    
    Returnerar:
    str: Sökväg till den konverterade filen
    """
    
    # Se till att ljudkatalogen finns
    os.makedirs("audio", exist_ok=True)
    
    # Ladda ljudfilen
    audio = AudioSegment.from_file(uploaded_file)
    
    # Konvertera till mono
    audio = audio.set_channels(1)
    
    # Beräkna målbitrate för att uppnå önskad filstorlek (i bitar per sekund)
    duration_seconds = len(audio) / 1000.0  # pydub arbetar i millisekunder
    target_bitrate = int((target_size_MB * 1024 * 1024 * 8) / duration_seconds)
    
    # Sätt en minsta bitrate för att behålla viss kvalitet
    min_bitrate = 16000  # 16kbps
    target_bitrate = max(target_bitrate, min_bitrate)
    
    # Komprimera ljudfilen
    file_path = f"audio/{file_name}.mp3"
    try:
        audio.export(file_path, format="mp3", bitrate=f"{target_bitrate}")
        return file_path
    except Exception as e:
        st.error(f"Fel vid ljudexport: {e}")
        return None
