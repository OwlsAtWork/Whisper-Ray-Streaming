import librosa
import numpy as np
import soundfile as sf  


SAMPLE_RATE = 16000
CHUNK_DURATION_MS = 100
SAMPLES_PER_CHUNK = int(SAMPLE_RATE * CHUNK_DURATION_MS / 1000)



def load_and_prepare_audio(file_path):
    """
    Loads a WAV file, converts it to the correct format if needed, and splits it into chunks.
    Returns list of chunks in bytes format.
    """
    try:
        # Read audio file using soundfile which supports multiple formats
        audio_data, sample_rate = sf.read(file_path, dtype='float32')
        
        # Convert stereo to mono if needed
        if len(audio_data.shape) > 1:
            audio_data = np.mean(audio_data, axis=1)
        
        # Resample if needed
        if sample_rate != SAMPLE_RATE:
            audio_data = librosa.resample(audio_data, orig_sr=sample_rate, target_sr=SAMPLE_RATE)
        
        # Convert to 16-bit PCM
        audio_array = (audio_data * 32767).astype(np.int16)
        
        # Generate 2 seconds of silence
        silence_duration = 2  # seconds
        silence_samples = int(SAMPLE_RATE * silence_duration)
        silence = np.zeros(silence_samples, dtype=np.int16)
        
        # Append silence to the audio data
        audio_array = np.concatenate((audio_array, silence))
        
        # Split into chunks
        chunks = []
        for i in range(0, len(audio_array), SAMPLES_PER_CHUNK):
            chunk = audio_array[i:i + SAMPLES_PER_CHUNK]
            # Pad last chunk with zeros if necessary
            if len(chunk) < SAMPLES_PER_CHUNK:
                chunk = np.pad(chunk, (0, SAMPLES_PER_CHUNK - len(chunk)), 'constant', constant_values=0)
            chunks.append(chunk.tobytes())
        
        return chunks
        
    except Exception as e:
        print(f"[ERROR] Error processing audio file: {e}")
        raise