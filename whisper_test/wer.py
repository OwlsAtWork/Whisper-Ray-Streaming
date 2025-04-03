import jiwer
import re

def calculate_wer(reference, hypothesis):
    """
    Calculate Word Error Rate between reference and hypothesis transcriptions
    using custom text normalization
    """
    if not hypothesis:
        return 1.0  # 100% error if no hypothesis
    
    try:
        # Apply custom text normalization
        reference_normalized = normalize_text(reference)
        hypothesis_normalized = normalize_text(hypothesis)
        
        # Calculate WER using jiwer with normalized text
        wer = jiwer.wer(reference_normalized, hypothesis_normalized)
        
        return wer
    except Exception as e:
        print(e)
        return 1.0

def normalize_text(text):
    """
    Normalize text using custom rules:
    - Convert to lowercase
    - Remove punctuation
    - Remove extra whitespace
    """
    text = str(text).lower()
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text