import faulthandler
faulthandler.enable()

import io
import logging
from math import trunc
import time
import traceback

import numpy as np
from faster_whisper import WhisperModel, BatchedInferencePipeline
from ray import serve

from .asr_interface import ASRInterface
from ..datetime_utils import get_current_time_string_with_milliseconds

logger = logging.getLogger("ray.serve")
logger.setLevel(logging.INFO)

language_codes = {
    "afrikaans": "af",
    "amharic": "am",
    "arabic": "ar",
    "assamese": "as",
    "azerbaijani": "az",
    "bashkir": "ba",
    "belarusian": "be",
    "bulgarian": "bg",
    "bengali": "bn",
    "tibetan": "bo",
    "breton": "br",
    "bosnian": "bs",
    "catalan": "ca",
    "czech": "cs",
    "welsh": "cy",
    "danish": "da",
    "german": "de",
    "greek": "el",
    "english": "en",
    "spanish": "es",
    "estonian": "et",
    "basque": "eu",
    "persian": "fa",
    "finnish": "fi",
    "faroese": "fo",
    "french": "fr",
    "galician": "gl",
    "gujarati": "gu",
    "hausa": "ha",
    "hawaiian": "haw",
    "hebrew": "he",
    "hindi": "hi",
    "croatian": "hr",
    "haitian": "ht",
    "hungarian": "hu",
    "armenian": "hy",
    "indonesian": "id",
    "icelandic": "is",
    "italian": "it",
    "japanese": "ja",
    "javanese": "jw",
    "georgian": "ka",
    "kazakh": "kk",
    "khmer": "km",
    "kannada": "kn",
    "korean": "ko",
    "latin": "la",
    "luxembourgish": "lb",
    "lingala": "ln",
    "lao": "lo",
    "lithuanian": "lt",
    "latvian": "lv",
    "malagasy": "mg",
    "maori": "mi",
    "macedonian": "mk",
    "malayalam": "ml",
    "mongolian": "mn",
    "marathi": "mr",
    "malay": "ms",
    "maltese": "mt",
    "burmese": "my",
    "nepali": "ne",
    "dutch": "nl",
    "norwegian nynorsk": "nn",
    "norwegian": "no",
    "occitan": "oc",
    "punjabi": "pa",
    "polish": "pl",
    "pashto": "ps",
    "portuguese": "pt",
    "romanian": "ro",
    "russian": "ru",
    "sanskrit": "sa",
    "sindhi": "sd",
    "sinhalese": "si",
    "slovak": "sk",
    "slovenian": "sl",
    "shona": "sn",
    "somali": "so",
    "albanian": "sq",
    "serbian": "sr",
    "sundanese": "su",
    "swedish": "sv",
    "swahili": "sw",
    "tamil": "ta",
    "telugu": "te",
    "tajik": "tg",
    "thai": "th",
    "turkmen": "tk",
    "tagalog": "tl",
    "turkish": "tr",
    "tatar": "tt",
    "ukrainian": "uk",
    "urdu": "ur",
    "uzbek": "uz",
    "vietnamese": "vi",
    "yiddish": "yi",
    "yoruba": "yo",
    "chinese": "zh",
    "cantonese": "yue",
}


@serve.deployment(
    ray_actor_options={"num_cpus": 1},
    autoscaling_config={"min_replicas": 1, "max_replicas": 3, "target_num_ongoing_requests_per_replica": 8, "initial_replicas": 1},
    max_ongoing_requests=10,
)
class FasterWhisperASR(ASRInterface):
    def __init__(self, **kwargs):
        model_size = kwargs.get('model_size', "deepdml/faster-whisper-large-v3-turbo-ct2")
        # Run on GPU with FP16
        logger.info(f"Using model {model_size} for transcription")
        self.asr_pipeline = WhisperModel(
            model_size, 
            device="cpu",
            compute_type="float32"
        )
        
    async def batch_transcribe(self, client):
        audio_stream = io.BytesIO(client.scratch_buffer)

        language = None if client.config['language'] is None else language_codes.get(
            client.config['language'].lower())
        
        self.batched_model = BatchedInferencePipeline(model=self.asr_pipeline)

        segments, info = self.batched_model.transcribe(
            audio_stream, word_timestamps=True, language="en", batch_size=16, beam_size=2)

        flattened_words = [
            word for segment in segments for word in segment.words]

        to_return = {
            "language": info.language,
            "language_probability": info.language_probability,
            "text": ' '.join([s.text.strip() for s in segments]),
            "words": [
                {"word": w.word, "start": w.start, "end": w.end, "probability": w.probability} for w in flattened_words
            ]
        }
        return to_return


    async def transcribe_raw(self, client, debug_output):
        """
        Transcribe raw audio bytes directly without saving to a WAV file.
        Expects 16-bit PCM audio data at 16kHz sample rate.
        """
        try:
            # Convert raw PCM bytes to numpy array
            audio_data = np.frombuffer(client.scratch_buffer, dtype=np.int16)
            logger.debug(f"Converted to numpy array with shape: {audio_data.shape}")
            
            # Normalize to float32 in range [-1, 1]
            audio_data = audio_data.astype(np.float32) / 32768.0
            logger.debug(f"Normalized audio data to float32")

            # Language detection
            language = None if client.config['language'] is None else language_codes.get(
                client.config['language'].lower())
            logger.debug(f"Using language: {language if language else 'auto-detect'}")
            
            # Transcription
            logger.info("Starting transcription")
            start_time = time.time()
            
            
            debug_output["transcriptions_timestamp"]={"start_time": get_current_time_string_with_milliseconds(), "end_time": None, "duration_in_seconds": None}
            segments, info = self.asr_pipeline.transcribe(
                audio_data, 
                word_timestamps=True, 
                language="en", 
                beam_size=5,
                vad_filter=True,
            )
            logger.info("Transcription completed")
            debug_output["transcriptions_timestamp"]["end_time"] = get_current_time_string_with_milliseconds()
            transcription_time = time.time() - start_time
            debug_output["transcriptions_timestamp"]["duration_in_seconds"] = f"{transcription_time:.4f}"
            
            logger.debug(f"Completed transcription in {transcription_time:.2f} seconds")

            segments = list(segments)  # Ensure segments is a list
            logger.debug(f"Generated {len(segments)} segments")
            
            debug_output["original_buffer_size"] = len(client.scratch_buffer)
            debug_output["audio_shape"] = audio_data.shape
            debug_output["audio_dtype"] = str(audio_data.dtype)
            debug_output["audio_duration"] = f"{len(audio_data) / 16000} seconds"  # Assuming 16kHz sample rate
            
            silence_detection_duration = debug_output["silence_detection_timestamp"]["duration_in_seconds"]
            silence_threshold_seconds = debug_output["silence_threshold_seconds"]
            total_processing_time = silence_detection_duration + silence_threshold_seconds + transcription_time
            debug_output["total_processing_time"] = total_processing_time
                
            flattened_words = [word for segment in segments for word in segment.words]
            to_return = {
                "language": info.language,
                "language_probability": info.language_probability,
                "text": ' '.join([s.text.strip() for s in segments]),
                "words": [
                    {
                        "word": w.word, 
                        "start": w.start, 
                        "end": w.end, 
                        "probability": w.probability
                    } for w in flattened_words
                ],
                "metrics": debug_output
            }
            return to_return

        except Exception as e:
            logger.error(f"Transcription error: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {
                "error": str(e),
                "buffer_details": {
                    "size": len(client.scratch_buffer),
                    "type": str(type(client.scratch_buffer))
                }
            }
