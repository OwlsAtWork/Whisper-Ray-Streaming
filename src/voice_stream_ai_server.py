from .vad.vad_factory import VADFactory
from .vad.silero_vad import SileroVAD
from .client import Client
from .asr.faster_whisper_asr import FasterWhisperASR
from .asr.asr_factory import ASRFactory
from ray.serve.handle import DeploymentHandle
from ray import serve
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import uuid
import logging
import json
import faulthandler
faulthandler.enable()


logger = logging.getLogger("ray.serve")
logger.setLevel(logging.INFO)

fastapi_app = FastAPI()


@serve.deployment
@serve.ingress(fastapi_app)
class TranscriptionServer:
    """
    Represents the WebSocket server for handling real-time audio transcription.
    """

    def __init__(self, asr_handle: DeploymentHandle, vad_handle=DeploymentHandle, sampling_rate=16000, samples_width=2):
        logger.info("Initializing TranscriptionServer")

        self.sampling_rate = sampling_rate
        self.samples_width = samples_width
        self.connected_clients = {}
        self.asr_handle = asr_handle
        self.vad_handle = vad_handle

        logger.info("Creating VAD and ASR pipelines")
        self.vad_pipeline = VADFactory.create_vad_pipeline("silero")
        self.asr_pipeline = ASRFactory.create_asr_pipeline("faster_whisper")
        logger.info("VAD and ASR pipelines created successfully")
        self.debug_output = {
            "transcriptions_timestamp": {},
            "silence_detection_timestamp": {},
            "silence_threshold_seconds": 0.6,
            "min_speech_seconds": 0.5,
            "max_buffer_seconds": 3000.0,
            "buffer_context_seconds_for_vad": 1.0,
            "client_id": None,
            "original_buffer_size": None,
            "audio_shape": None,
            "audio_dtype": None,
            "audio_duration": None,
            "total_processing_time": None,
        }

    async def handle_audio(self, client: Client, websocket: WebSocket):
        """
        Handles the audio stream from the client.
        """
        while True:
            message = await websocket.receive()

            if "bytes" in message.keys():
                client.append_audio_data(message['bytes'])
            elif "text" in message.keys():
                config = json.loads(message['text'])
                if config.get('type') == 'config':
                    logger.debug(
                        f"Received config update from client {client.client_id}")
                    client.update_config(config['data'])
                    continue
            elif message["type"] == "websocket.disconnect":
                logger.info(f"Client {client.client_id} disconnected")
                raise WebSocketDisconnect
            else:
                keys_list = list(message.keys())
                logger.error(
                    f"{type(message)} is not a valid message type. Type is {message['type']}; keys: {json.dumps(keys_list)}")

            client.process_audio(websocket, self.vad_handle,
                                 self.asr_handle, self.debug_output)

    @fastapi_app.websocket("/")
    async def handle_websocket(self, websocket: WebSocket):
        logger.info("New WebSocket connection initiated")
        await websocket.accept()

        client_id = str(uuid.uuid4())
        client = Client(client_id, self.sampling_rate, self.samples_width)
        self.connected_clients[client_id] = client

        logger.info(f"Client {client_id} connected")
        self.debug_output["client_id"] = client_id

        try:
            await self.handle_audio(client, websocket)
        except WebSocketDisconnect as e:
            logger.warning(f"Connection with {client_id} closed: {e}")
        finally:
            logger.info(f"Removing client {client_id} from connected clients")
            del self.connected_clients[client_id]


logger.info("Starting TranscriptionServer deployment")
entrypoint = TranscriptionServer.bind(
    FasterWhisperASR.bind(), SileroVAD.bind())
serve.run(entrypoint)
logger.info("TranscriptionServer is running")
