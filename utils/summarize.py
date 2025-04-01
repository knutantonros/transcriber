### Sammanfattningsfunktioner

import os
import nltk
import streamlit as st
import openai
from nltk.tokenize import sent_tokenize

# Ladda ner NLTK-resurser (om de inte redan är nedladdade)
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)

# Se till att språkspecifika data är tillgängliga
for lang in ['english', 'swedish']:
    try:
        nltk.data.find(f'tokenizers/punkt/{lang}.pickle')
    except LookupError:
        nltk.download('punkt', quiet=True)

def summarize_text_openai(text, summary_length="Medium", api_key=None):
    """
    Sammanfatta text med OpenAI
    
    Parametrar:
    text (str): Texten som ska sammanfattas
    summary_length (str): Mycket kort, Kort, Medium, Lång, eller Mycket lång
    api_key (str): OpenAI API-nyckel
    
    Returnerar:
    str: Sammanfattad text
    """
    if not text:
        return ""
    
    # Kontrollera om API-nyckel finns
    api_key = api_key or st.session_state.get("openai_api_key")
    
    if not api_key:
        return "**Ingen OpenAI API-nyckel tillhandahållen.** Ange din API-nyckel i sidofältet för att aktivera sammanfattningsfunktionen."
    
    # Definiera längdinställningar baserat på summary_length
    length_mappings = {
        "Mycket kort": "mycket kort (1-2 meningar)",
        "Kort": "kort (2-3 meningar)",
        "Medium": "medellång (3-5 meningar)",
        "Lång": "lång (5-7 meningar)",
        "Mycket lång": "mycket lång (7-10 meningar)"
    }
    
    length_description = length_mappings[summary_length]
    
    # För mycket korta indata, returnera bara texten
    if len(text.split()) < 20:
        return text
    
    try:
        client = openai.OpenAI(api_key=api_key)
        
        prompt = f"""
        Nedan finns en text på svenska som ska sammanfattas. 
        Skapa en {length_description} sammanfattning av texten på svenska.
        Sammanfattningen ska fånga den viktigaste informationen och behålla textens ursprungliga ton.
        
        Text att sammanfatta:
        {text}
        """
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Du är en assistent som skapar högkvalitativa sammanfattningar på svenska."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=500
        )
        
        return response.choices[0].message.content.strip()
    
    except Exception as e:
        # Visa ett mer användarvänligt felmeddelande
        error_message = str(e)
        if "auth" in error_message.lower() or "api key" in error_message.lower():
            return "**Det uppstod ett fel med din API-nyckel.** Kontrollera att nyckeln är korrekt och har tillräcklig kredit för att använda OpenAI:s API."
        else:
            # Fallback till extraktiv sammanfattning om API-anropet misslyckas
            st.warning(f"Fel vid sammanfattning med OpenAI: {e}. Använder enkel sammanfattning istället.")
            try:
                return extractive_summarize(text, summary_length)
            except Exception as ex:
                # Om även den enkla sammanfattningen misslyckas
                st.error(f"Kunde inte skapa en sammanfattning: {ex}")
                return "**Kunde inte skapa en sammanfattning.** Vänligen kontrollera texten eller försök igen senare."


def extractive_summarize(text, summary_length="Medium"):
    """
    Utför extraktiv sammanfattning på text som en reservmetod
    
    Parametrar:
    text (str): Texten som ska sammanfattas
    summary_length (str): Mycket kort, Kort, Medium, Lång, eller Mycket lång
    
    Returnerar:
    str: Sammanfattad text
    """
    if not text:
        return ""
        
    # Mappa summary_length till antal meningar
    length_map = {
        "Mycket kort": 1,
        "Kort": 2,
        "Medium": 3,
        "Lång": 5,
        "Mycket lång": 7
    }
    
    num_sentences = length_map[summary_length]
    
    # Försök att dela upp texten i meningar med flera metoder
    try:
        # Försök först med NLTK's sent_tokenize för svenska
        sentences = sent_tokenize(text, language='swedish')
    except (LookupError, ImportError, ValueError) as e:
        try:
            # Fallback till engelsk tokenisering
            sentences = sent_tokenize(text, language='english')
        except (LookupError, ImportError, ValueError) as e:
            # Enkel manuell tokenisering som sista utväg
            sentences = [s.strip() for s in text.replace('!', '.').replace('?', '.').split('.') if s.strip()]
            
    # Om vi fortfarande inte har meningar, returnera texten som den är
    if not sentences:
        return text
        
    # För korta texter, returnera originalet
    if len(sentences) <= num_sentences:
        return text
    
    # Enkel poängsättning: de första meningarna och den sista meningen innehåller ofta viktig information
    important_indices = list(range(min(3, len(sentences))))
    
    # Lägg till den sista meningen om vi har tillräckligt med meningar
    if len(sentences) > 3 and -1 not in important_indices:
        important_indices.append(len(sentences) - 1)
    
    # Om vi behöver fler meningar, lägg till några från mitten
    remaining_needed = num_sentences - len(important_indices)
    if remaining_needed > 0:
        middle_indices = list(range(3, len(sentences) - 1))
        step_size = max(1, len(middle_indices) // remaining_needed)
        additional_indices = middle_indices[::step_size][:remaining_needed]
        important_indices.extend(additional_indices)
    
    # Sortera indexen för att behålla den ursprungliga ordningen
    important_indices.sort()
    
    # Extrahera de viktiga meningarna
    summary_sentences = [sentences[i] for i in important_indices[:num_sentences]]
    
    return " ".join(summary_sentences)
