### Transkriberingsfunktioner

import os
import torch
import time
import threading
from pydub import AudioSegment
from datasets import load_dataset
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline

def get_audio_duration(file_path):
    """
    Hämta längden på en ljudfil i sekunder
    
    Parametrar:
    file_path (str): Sökväg till ljudfilen
    
    Returnerar:
    float: Ljudfilens längd i sekunder
    """
    try:
        audio = AudioSegment.from_file(file_path)
        return len(audio) / 1000.0  # Konvertera från millisekunder till sekunder
    except Exception as e:
        print(f"Kunde inte hämta ljudfilens längd: {e}")
        return 0

def transcribe_with_kb_whisper(file_name_converted, file_name, whisper_model, spoken_language="sv", text_dir="text", progress_callback=None):
    """
    Transkribera ljud med KB-Whisper modeller
    
    Parametrar:
    file_name_converted (str): Sökväg till ljudfilen
    file_name (str): Basnamn för utdatafilen
    whisper_model (str): Namn på KB Whisper-modellen som ska användas
    spoken_language (str): Språkkod (standardvärde 'sv' för svenska)
    text_dir (str): Katalog för utmatning av textfiler
    progress_callback (function): Funktion att anropa för att rapportera förloppet
    
    Returnerar:
    str: Transkriberad text
    """
    
    # Uppskatta ljudfilens längd
    audio_duration = get_audio_duration(file_name_converted)
    
    # Definiera en funktion som uppdaterar förloppet
    def update_progress():
        if progress_callback:
            # Beräkna uppskattad transkriptionstid baserat på modell och ljudlängd
            # Olika modeller har olika bearbetningstider
            model_speed_factors = {
                "kb-whisper-large": 0.3,  # Långsammare
                "kb-whisper-medium": 0.5,
                "kb-whisper-small": 0.7,
                "kb-whisper-base": 0.8,
                "kb-whisper-tiny": 1.0    # Snabbare
            }
            
            speed_factor = model_speed_factors.get(whisper_model, 0.5)
            
            # Beräkna hur lång tid transkriberingen bör ta
            # Detta är en grov uppskattning som kan justeras
            estimated_time = audio_duration * (1.0 / speed_factor)
            
            # Lägsta tid för korta filer
            estimated_time = max(estimated_time, 5)
            
            # Uppdatera förloppet med jämna intervall
            steps = 100
            sleep_time = estimated_time / steps
            
            for i in range(steps):
                # Uppskatta förloppet (0.0 till 1.0)
                progress = min(i / steps, 0.95)  # Max 95% för att visa att vi fortfarande arbetar
                progress_callback(progress)
                time.sleep(sleep_time)
    
    # Starta uppdatering av förloppet i en separat tråd
    if progress_callback:
        progress_thread = threading.Thread(target=update_progress)
        progress_thread.daemon = True
        progress_thread.start()
    
    try:
        device = "cuda:0" if torch.cuda.is_available() else "cpu"
        torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32
        model_id = f"KBLab/{whisper_model}"
        
        # Skapa cache-katalog om den inte finns
        os.makedirs("cache", exist_ok=True)
        
        model = AutoModelForSpeechSeq2Seq.from_pretrained(
            model_id, torch_dtype=torch_dtype, use_safetensors=True, cache_dir="cache"
        )
        model.to(device)
        processor = AutoProcessor.from_pretrained(model_id)
        
        pipe = pipeline(
            "automatic-speech-recognition",
            model=model,
            tokenizer=processor.tokenizer,
            feature_extractor=processor.feature_extractor,
            torch_dtype=torch_dtype,
            device=device,
        )
        
        generate_kwargs = {"task": "transcribe", "language": spoken_language}
        
        res = pipe(
            file_name_converted, 
            chunk_length_s=30,
            generate_kwargs=generate_kwargs
        )
        
        # Meddela att processen är klar
        if progress_callback:
            progress_callback(1.0)
        
        transcribed_content = res["text"]
        
        # Se till att textkatalogen finns
        os.makedirs(text_dir, exist_ok=True)
        
        with open(os.path.join(text_dir, f'{file_name}.txt'), 'w', encoding='utf-8', errors='replace') as file:
            file.write(transcribed_content)
        
        return transcribed_content
        
    except Exception as e:
        if progress_callback:
            progress_callback(1.0)  # Avsluta förloppet även vid fel
        raise e
