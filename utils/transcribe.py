### Transkriberingsfunktioner

import os
import torch
from datasets import load_dataset
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline

def transcribe_with_kb_whisper(file_name_converted, file_name, whisper_model, spoken_language="sv", text_dir="text"):
    """
    Transkribera ljud med KB-Whisper modeller
    
    Parametrar:
    file_name_converted (str): Sökväg till ljudfilen
    file_name (str): Basnamn för utdatafilen
    whisper_model (str): Namn på KB Whisper-modellen som ska användas
    spoken_language (str): Språkkod (standardvärde 'sv' för svenska)
    
    Returnerar:
    str: Transkriberad text
    """
    
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
    
    transcribed_content = res["text"]
    
    # Se till att textkatalogen finns
    os.makedirs("text", exist_ok=True)
    
    with open(f'text/{file_name}.txt', 'w', encoding='utf-8', errors='replace') as file:
        file.write(transcribed_content)
    
    return transcribed_content
