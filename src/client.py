import faulthandler
faulthandler.enable()

import logging
import uuid

from .buffering_strategy.buffering_strategy_factory import BufferingStrategyFactory
from fastapi import WebSocket

logger = logging.getLogger("ray.serve")
logger.setLevel(logging.DEBUG)

class Client:
    """
    Represents a client connected to the VoiceStreamAI server.

    Attributes:
        client_id (str): A unique identifier for the client.
        buffer (bytearray): A buffer to store incoming audio data.
        config (dict): Configuration settings for the client, like chunk length and offset.
        file_counter (int): Counter for the number of audio files processed.
        total_samples (int): Total number of audio samples received from this client.
        sampling_rate (int): The sampling rate of the audio data in Hz.
        samples_width (int): The width of each audio sample in bits.
    """
    def __init__(self, client_id, sampling_rate, samples_width):
        self.client_id = client_id
        self.buffer = bytearray()
        self.scratch_buffer = bytearray()
        self.config = {
            "language": None,
            "processing_strategy": "silence_at_end_of_chunk",
            "processing_args": {
                "chunk_length_seconds": 0.01,
                "chunk_offset_seconds": 0.1
            }
        }
        self.file_counter = 0
        self.total_samples = 0
        self.sampling_rate = sampling_rate
        self.samples_width = samples_width
        self.buffering_strategy = BufferingStrategyFactory.create_buffering_strategy(
            self.config['processing_strategy'],
            self, **self.config['processing_args']
        )

    def update_config(self, config_data):
        self.config.update(config_data)
        self.buffering_strategy = BufferingStrategyFactory.create_buffering_strategy(
            self.config['processing_strategy'],
            self, **self.config['processing_args']
        )

    def append_audio_data(self, audio_data):
        self.buffer.extend(audio_data)
        if self.samples_width and self.samples_width != 0:
            self.total_samples += len(audio_data) / self.samples_width
        else:
            logger.error("failed to append audio data: samples_width is either None or zero", self.samples_width)

    def clear_buffer(self):
        self.buffer.clear()

    def increment_file_counter(self):
        self.file_counter += 1

    def get_file_name(self):
        # Generate an UUID string
        new_uuid = uuid.uuid4()

        return f"{self.client_id}_{self.file_counter}.wav"

    def process_audio(self, websocket: WebSocket, vad_handle, asr_handle, debug_output):
        self.buffering_strategy.process_audio(websocket, vad_handle, asr_handle, debug_output)
