### Ljudhjälpfunktioner

import os
import streamlit as st
import tempfile
import hashlib
from pydub import AudioSegment

# Konverterar och komprimerar ljud- eller videofil till mp3 och en mer hanterbar storlek
def convert_to_mono_and_compress(uploaded_file, file_name, audio_dir="audio", target_size_MB=22):
    """
    Konvertera uppladdad ljud/videofil till mono MP3 och komprimera den till en målstorlek
    
    Parametrar:
    uploaded_file (UploadedFile): Det uppladdade filobjektet från Streamlit
    file_name (str): Filens namn
    audio_dir (str): Katalog för ljudfiler
    target_size_MB (int): Målstorlek i MB för den komprimerade filen
    
    Returnerar:
    str: Sökväg till den konverterade filen
    """
    
    # Se till att ljudkatalogen finns
    os.makedirs(audio_dir, exist_ok=True)
    
    try:
        # Beräkna en hash för filen för cachning
        file_content = uploaded_file.getvalue()
        file_hash = hashlib.md5(file_content).hexdigest()
        cache_key = f"converted_audio_{file_hash}"
        
        # Kontrollera om filen redan har bearbetats
        if cache_key in st.session_state:
            # Återanvänd tidigare konverterad fil om den fortfarande existerar
            cached_path = st.session_state[cache_key]
            if os.path.exists(cached_path):
                return cached_path
        
        # Spara den uppladdade filen temporärt för att säkerställa att ffmpeg kan komma åt den
        with tempfile.NamedTemporaryFile(delete=False, suffix='.' + uploaded_file.name.split('.')[-1]) as tmp_file:
            tmp_file.write(file_content)
            tmp_path = tmp_file.name
        
        # Ladda ljudfilen från den temporära filen
        try:
            audio = AudioSegment.from_file(tmp_path)
        except Exception as e:
            st.error(f"Kunde inte läsa ljudfilen: {e}")
            st.info("Kontrollera att ffmpeg är installerat korrekt.")
            os.unlink(tmp_path)  # Ta bort temporär fil
            return None
        
        # Ta bort temporär fil
        os.unlink(tmp_path)
        
        # Konvertera till mono
        audio = audio.set_channels(1)
        
        # Beräkna målbitrate för att uppnå önskad filstorlek (i bitar per sekund)
        duration_seconds = len(audio) / 1000.0  # pydub arbetar i millisekunder
        target_bitrate = int((target_size_MB * 1024 * 1024 * 8) / duration_seconds)
        
        # Sätt en minsta bitrate för att behålla viss kvalitet
        min_bitrate = 16000  # 16kbps
        target_bitrate = max(target_bitrate, min_bitrate)
        
        # Komprimera ljudfilen
        file_path = os.path.join(audio_dir, f"{file_name}.mp3")
        try:
            audio.export(file_path, format="mp3", bitrate=f"{target_bitrate}")
            
            # Spara i session state för framtida användning
            st.session_state[cache_key] = file_path
            
            return file_path
        except Exception as e:
            st.error(f"Fel vid ljudexport: {e}")
            return None
            
    except Exception as e:
        st.error(f"Ett oväntat fel uppstod: {e}")
        return None
