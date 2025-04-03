import asyncio
import websockets
import numpy as np
import time
import json
import soundfile as sf
import librosa
from collections import deque
from typing import List, Dict
import os
import wave

from config import *

class TranscriptionManager:
    def __init__(self):
        self.transcription_queue = asyncio.Queue()
        self.chunks_sent = 0
        self.total_chunks = 0
        self.is_sending_complete = False
        self.transcription_segments: List[Dict] = []
        self.start_time = time.time()
        self.send_complete_time = None
        self.latency_stats = {
            'send_time': 0,
            'first_response_time': None,
            'last_response_time': None,
            'processing_time': 0,
            'total_time': 0
        }
        
    def get_progress(self):
        return f"{self.chunks_sent}/{self.total_chunks}" if self.total_chunks else "0/0"
    
    def record_send_complete(self):
        self.send_complete_time = time.time()
        self.latency_stats['send_time'] = self.send_complete_time - self.start_time

async def send_audio_chunks(websocket, audio_chunks: List[bytes], manager: TranscriptionManager):
    """Task responsible for sending audio chunks"""
    try:
        manager.total_chunks = len(audio_chunks)
        chunk_send_times = []
        
        # Create directory if it doesn't exist
        debug_dir = "sent_audio"
        os.makedirs(debug_dir, exist_ok=True)
        
        for i, chunk in enumerate(audio_chunks):
            chunk_start = time.time()
            
            # Convert bytes back to numpy array
            chunk_array = np.frombuffer(chunk, dtype=np.int16)
            
            # Save chunk as WAV file
            chunk_filename = os.path.join(debug_dir, f"chunk_{i:04d}.wav")
            with wave.open(chunk_filename, 'wb') as wav_file:
                wav_file.setnchannels(1)  # mono
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(SAMPLE_RATE)
                wav_file.writeframes(chunk_array.tobytes())
            
            await websocket.send(chunk)
            chunk_send_times.append(time.time() - chunk_start)
            manager.chunks_sent += 1
            
            if manager.chunks_sent % 10 == 0:
                print(f"[INFO] Progress: {manager.get_progress()} chunks sent")
            
            await asyncio.sleep(CHUNK_SLEEP)
        
        manager.is_sending_complete = True
        manager.record_send_complete()
        avg_chunk_latency = sum(chunk_send_times) / len(chunk_send_times)
        print(f"[INFO] All audio chunks sent successfully. Average chunk send time: {avg_chunk_latency:.3f}s")
        
    except Exception as e:
        print(f"[ERROR] Error in send_audio_chunks: {e}")
        manager.is_sending_complete = True
        raise

async def receive_transcriptions(websocket, manager: TranscriptionManager):
    """Task responsible for receiving and processing transcriptions"""
    try:
        last_response_time = time.time()
        while True:
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=REQUEST_TIMEOUT)
                current_time = time.time()
                
                try:
                    response_data = json.loads(response)
                    if "text" in response_data and response_data["text"].strip():
                        # Record first response time
                        if not manager.latency_stats['first_response_time']:
                            manager.latency_stats['first_response_time'] = current_time - manager.start_time
                        
                        # Update last response time
                        manager.latency_stats['last_response_time'] = current_time - manager.start_time
                        
                        segment = {
                            "text": response_data["text"].strip(),
                            "timestamp": current_time,
                            "latency": current_time - manager.start_time
                        }
                        manager.transcription_segments.append(segment)
                        print(f"[INFO] New transcription: {segment['text']} (Latency: {segment['latency']:.3f}s)")
                        
                except json.JSONDecodeError:
                    print(f"[WARNING] Received non-JSON response: {response[:100]}...")
            
            except asyncio.TimeoutError:
                if manager.is_sending_complete and (time.time() - last_response_time > AFTER_SENT_TIMEOUT):
                    print("[INFO] No new responses received for 10 seconds after sending completion. Finishing...")
                    break
                continue
            except websockets.exceptions.ConnectionClosed:
                print("[INFO] WebSocket connection closed")
                break
            
    except Exception as e:
        print(f"[ERROR] Error in receive_transcriptions: {e}")
        raise
    
    
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
        silence_duration = SILENCE_PADDING  # seconds
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
                print(len(chunk))
            chunks.append(chunk.tobytes())
        
        return chunks
        
    except Exception as e:
        print(f"[ERROR] Error processing audio file: {e}")
        raise



async def whisper_transcription(audio_file=AUDIO_FILE):
    try:
        audio_chunks = load_and_prepare_audio(audio_file)
        manager = TranscriptionManager()
        
        print(f"[INFO] Starting transcription of {len(audio_chunks)} chunks")
        
        async with websockets.connect(SERVER_URL) as websocket:
            send_task = asyncio.create_task(send_audio_chunks(websocket, audio_chunks, manager))
            receive_task = asyncio.create_task(receive_transcriptions(websocket, manager))
            
            await asyncio.gather(send_task, receive_task)
            
        # Calculate final latency statistics
        end_time = time.time()
        manager.latency_stats['total_time'] = end_time - manager.start_time
        manager.latency_stats['processing_time'] = manager.latency_stats['last_response_time'] - manager.latency_stats['send_time']
        
        # Process results
        full_transcription = " ".join(segment["text"] for segment in manager.transcription_segments)
        
        # Print detailed latency information
        print("\n=== Latency Statistics ===")
        print(f"Total time: {manager.latency_stats['total_time']:.3f}s")
        print(f"Audio send time: {manager.latency_stats['send_time']:.3f}s")
        print(f"Time to first response: {manager.latency_stats['first_response_time']:.3f}s")
        print(f"Time to Last response: {manager.latency_stats['last_response_time']:.3f}s")
        print(f"Processing time: {manager.latency_stats['processing_time']:.3f}s")
        print(f"Number of transcription segments: {len(manager.transcription_segments)}")
        print(f"\n[INFO] Final transcription: {full_transcription}")
        
        return full_transcription, manager.latency_stats.get("last_response_time",{})
        
    except Exception as e:
        print(f"[ERROR] An error occurred: {e}")
        return None, None, None

if __name__ == "__main__":
    
#    transcription,latency= asyncio.run(whisper_transcription())
    asyncio.run(whisper_transcription())
   
    # print("////////////////////",f"Transcription:{transcription}",f"Latency:{latency}")