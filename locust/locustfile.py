import os
import time
import json
import logging
import librosa
import numpy as np
import soundfile as sf
from gevent.pool import Pool
from locust import User, task
from locust.exception import StopUser
from websockets.sync.client import connect
from websockets.exceptions import InvalidMessage

# Audio Configuration
SAMPLE_RATE = 16000  # Required sample rate
CHUNK_DURATION_MS = 100  # 100ms chunks
SAMPLES_PER_CHUNK = int(SAMPLE_RATE * CHUNK_DURATION_MS / 1000)

logging.basicConfig(level=logging.INFO)


def load_and_chunk_audio(file_path):
    """Load an audio file and split it into chunks of 100ms."""
    audio, sr = librosa.load(file_path, sr=SAMPLE_RATE, mono=True)
    audio = (audio * 32767).astype(np.int16)  # Convert to int16 PCM format
    
    # Pad with silence if necessary to ensure full chunks
    num_chunks = int(np.ceil(len(audio) / SAMPLES_PER_CHUNK))
    padded_length = num_chunks * SAMPLES_PER_CHUNK
    audio = np.pad(audio, (0, padded_length - len(audio)), mode="constant")
    
    chunks = np.split(audio, num_chunks)
    return chunks


class WebSocketUser(User):
    abstract = True

    def __init__(self, environment):
        super().__init__(environment)
        self.pool = Pool(1)
        with self.environment.events.request.measure("[Connect]", "Websocket"):
            self.client = connect(self.host)

    def on_start(self):
        def _receive():
            while True:
                try:
                    transcription_str = self.client.recv()
                except InvalidMessage as e:
                    logging.error("Invalid message:", e)
                except Exception as e:
                    logging.error("Error:", e)
                    break
                else:
                    with self.environment.events.request.measure("[Receive]", "Response"):
                        transcription_json = json.loads(transcription_str)
                        logging.info(f"Received: {transcription_json['text']}")

        self.pool.spawn(_receive)

    def on_stop(self):
        super().on_stop()
        logging.info("Closing websocket connection")
        self.pool.kill()
        self.client.close()

    @task
    def send_streaming_audio(self):
        self.start_time = time.time()
        
        for filename in os.listdir(self.audio_file_path):
            if filename.endswith(".wav"):
                audio_file = os.path.join(self.audio_file_path, filename)
                logging.info(f"Loading audio file: {audio_file}")
                
                try:
                    audio_chunks = load_and_chunk_audio(audio_file)
                    logging.info("Start sending audio")
                    
                    for chunk in audio_chunks:
                        with self.environment.events.request.measure("[Send]", "Audio chunks"):
                            self.client.send(chunk.tobytes())
                            # time.sleep(0.01)
                            time.sleep(CHUNK_DURATION_MS / 1000.0)
                            
                    
                    # Send one chunk of silence at the end
                    silence_chunk = np.zeros(20*SAMPLES_PER_CHUNK, dtype=np.int16)
                    self.client.send(silence_chunk.tobytes())
                    logging.info("Sent silence chunk")
                    
                except Exception as e:
                    logging.error(f"Error processing audio file: {e}")
                    
        raise StopUser()


class EnglishStreamWhisperWebSocketUser(WebSocketUser):
    host = "ws://localhost:8000"
    audio_file_path = "./data/en_raw"




# import pathlib
# from gevent.pool import Pool
# from locust import User, task
# from locust.exception import StopUser
# # from pydub import AudioSegment
# from websockets.sync.client import connect
# from websockets.exceptions import InvalidMessage

# import os
# import time
# import logging
# import json
# import librosa


# from utils import load_and_prepare_audio


# logging.basicConfig(level=logging.INFO)


# class WebSocketUser(User):
#     abstract = True

#     def __init__(self, environment):
#         super().__init__(environment)
#         self.pool = Pool(1)
#         with self.environment.events.request.measure("[Connect]", "Websocket"):
#             self.client = connect(self.host)

#     def on_start(self):

#         def _receive():
#             while True:
#                 try:
#                     transcription_str = self.client.recv()
#                 except InvalidMessage as e:
#                     logging.error("Invalid message:", e)
#                 except Exception as e:
#                     logging.error("Error:", e)
#                     break
#                 else:
#                     with self.environment.events.request.measure(
#                         "[Receive]", "Response"
#                     ):
#                         client_id = self.client.id
#                         transcription_end = time.time()
#                         time_elapse = round(transcription_end - self.start_time, 2)
#                         transcription_json = json.loads(transcription_str)
#                         logging.debug(transcription_json)
#                         logging.info(
#                             f"[{client_id}] Time elapse: {time_elapse}s, Received: {transcription_json['text']}"
#                         )

#         self.pool.spawn(_receive)

#     def on_stop(self):
#         super().on_stop()
#         logging.info("Closing websocket connection")
#         self.pool.kill()
#         self.client.close()

#     @task
#     def send_streaming_audio(self):

#         self.start_time = time.time()
#         for filename in os.listdir(self.audio_file_path):
#             if filename.endswith(".wav"):
#                 audio_file = os.path.join(self.audio_file_path, filename)
#                 logging.info(f"Loading audio file: {audio_file}")

#                 with open(audio_file, "rb") as file:
#                     file_format = pathlib.Path(audio_file).suffix[1:]
#                     logging.debug(f"File format: {file_format}")
#                     try:
#                         audio = AudioSegment.from_file(file, format=file_format)
#                     except Exception as e:
#                         logging.error("File loading error:", e)

#                     logging.info("Start sending audio")
#                     for i in range(0, len(audio), 250):
#                         chunk = audio[i : i + 250]
#                         with self.environment.events.request.measure(
#                             "[Send]", "Audio trunks"
#                         ):
#                             logging.debug(f"Sending trunk {i}...")
#                             self.client.send(chunk.raw_data)
#                             time.sleep(0.25)
#                     silence = AudioSegment.silent(duration=10000)
#                     self.client.send(silence.raw_data)
#                     logging.info("Sent silence")
#         raise StopUser()
    
    
#     # @task
#     # def send_streaming_audio(self):
#     #     self.start_time = time.time()
#     #     for filename in os.listdir(self.audio_file_path):
#     #         if filename.endswith(".wav"):
#     #             audio_file = os.path.join(self.audio_file_path, filename)
#     #             logging.info(f"using {audio_file} for testing")
#     #             logging.info(f"Loading audio file: {audio_file}")
                
#     #             try:
#     #                 # Use the load_and_prepare_audio function to get chunks
#     #                 audio_chunks = load_and_prepare_audio(audio_file)
                    
#     #                 logging.info("Start sending audio")
#     #                 for chunk in audio_chunks:
#     #                     with self.environment.events.request.measure("[Send]", "Audio chunks"):
#     #                         logging.debug(f"Sending chunk {len(chunk)}...")
#     #                         self.client.send(chunk)
#     #                         time.sleep(0.1)
                    
#     #                 logging.info("Audio chunks sent, silence automatically included")
                    
#     #             except Exception as e:
#     #                 logging.error(f"Error processing audio file: {e}")
                    
#     #     raise StopUser()


# class EnglisthStreamWhisperWebSocketUser(WebSocketUser):
#     host = "ws://localhost:8000"
#     audio_file_path = "./data/en_raw"
#     start_time: float = 0.0


# # class ChineseStreamWhisperWebSocketUser(WebSocketUser):
# #     host = "ws://localhost:8000"
# #     audio_file_path = "./data/en"
# #     start_time: float = 0.0
