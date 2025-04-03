import os
import pandas as pd
import numpy as np
import asyncio
import websockets
import json
import soundfile as sf
import librosa
import argparse
import mlflow
from datetime import datetime
import logging
import jiwer  


from config import *
from streaming_transcription import whisper_transcription
from wer import calculate_wer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('transcription_analysis.log')
    ]
)
logger = logging.getLogger(__name__)

def setup_mlflow():
    """Configure MLflow tracking"""
    experiment_name = f"transcription_wer_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    experiment_name="transcription_wer_analysis"
    try:
        experiment_id = mlflow.create_experiment(experiment_name)
        logger.info(f"Created new MLflow experiment: {experiment_name}")
    except Exception as e:
        experiment_id = mlflow.get_experiment_by_name(experiment_name).experiment_id
        logger.info(f"Using existing MLflow experiment: {experiment_name}")
    
    return experiment_id

def get_user_parameters():
    """Prompt user for parameters or use environment variables/defaults"""
    # Define parameters with environment fallbacks and defaults
    server_url = SERVER_URL
    
    silence_threshold = SILENCE_THRESHOLD
    
    min_speech_duration = MIN_SPEECH_DURATION
    
    max_buffer_duration = MAX_BUFFER_DURATION

    buffer_context = BUFFER_CONTEXT
    
    model= MODEL

    
    logger.info(f"Using parameters - Server URL: {server_url}, Silence threshold: {silence_threshold}dB, "
                f"Min speech: {min_speech_duration}ms, Max buffer: {max_buffer_duration}ms, "
                f"Buffer context: {buffer_context}ms")
    
    return {
        "server_url": server_url,
        "silence_threshold": silence_threshold,
        "min_speech_duration": min_speech_duration,
        "max_buffer_duration": max_buffer_duration,
        "buffer_context": buffer_context,
        "model": model,
    }





async def process_samples(csv_path,n_samples,params):
    """
    Process the first n_samples from the CSV file
    """
    try:
        # Load the CSV file
        df = pd.read_csv(csv_path)
        logger.info(f"Loaded dataset with {len(df)} total entries")
        
        # Select first n samples
        sample_df = df.head(n_samples)
        
        if 'wav_path' not in sample_df.columns or 'transcription' not in sample_df.columns:
            logger.error("CSV must contain 'wav_path' and 'transcription' columns")
            return None
        
        # Process each sample
        results = []
        for idx, row in sample_df.iterrows():
            logger.info(f"Processing sample {idx+1}/{n_samples}: {row['wav_path']}")
            
            # Check if file exists
            if not os.path.exists(row['wav_path']):
                # Try relative path
                base_dir = os.path.dirname(csv_path)
                alt_path = os.path.join(base_dir, row['wav_path'])
                if not os.path.exists(alt_path):
                    logger.warning(f"Audio file not found: {row['wav_path']}")
                    continue
                wav_path = alt_path
            else:
                wav_path = row['wav_path']
            
            # Get reference transcription
            reference_transcription = row['transcription']
            
            # Get real-time transcription from WebSocket server
            transcription,latency = await whisper_transcription(wav_path)
            
            # Calculate WER
            wer = calculate_wer(reference_transcription, transcription)
            
            # Basic audio stats for context
            # try:
            #     audio_data, sample_rate = sf.read(wav_path, dtype='float32')
            #     if len(audio_data.shape) > 1:
            #         audio_data = np.mean(audio_data, axis=1)
            #     duration = len(audio_data) / sample_rate
            # except Exception as e:
            #     logger.error(f"Error getting audio stats: {e}")
            #     duration = 0
            
            # Store results
            sample_result = {
                "sample_id": idx,
                "wav_path": wav_path,
                "reference_transcription": reference_transcription,
                "asr_transcription": transcription,
                "wer": wer,
                "latency": latency
            }
            
            results.append(sample_result)
            
            # Log individual sample metrics to MLflow
            mlflow.log_metric(f"sample_{idx}_wer", wer)
            mlflow.log_metric(f"sample_{idx}_latency",latency )
            
            # Create text artifact with transcriptions
            transcription_file = f"transcriptions/sample_{idx}.txt"
            os.makedirs(os.path.dirname(transcription_file), exist_ok=True)
            with open(transcription_file, 'w') as f:
                f.write(f"Reference: {reference_transcription}\n")
                f.write(f"ASR Output: {transcription}\n")
                f.write(f"WER: {wer:.4f}\n")
            mlflow.log_artifact(transcription_file)
            
        return results
    except Exception as e:
        logger.error(f"Error processing samples: {e}")
        return None

async def main_async():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Real-time Transcription and WER Analysis')
    parser.add_argument('--csv_path', default='speech_dataset/speech_data.csv', 
                        help='Path to the CSV file containing speech dataset')
    parser.add_argument('--n_samples', type=int, default=10,
                        help='Number of samples to analyze')
    args = parser.parse_args()
    
    # Get user parameters
    params = get_user_parameters()
    
    # Setup MLflow
    experiment_id = setup_mlflow()
    
    # Start MLflow run
    with mlflow.start_run(experiment_id=experiment_id):
        # Log parameters
        for param_name, param_value in params.items():
            mlflow.log_param(param_name, param_value)
        
        # Process samples and calculate WER
        results = await process_samples(args.csv_path, args.n_samples, params)
        
        if results:
            # Calculate aggregate statistics
            wers = [r['wer'] for r in results]
            latency = [r['latency'] for r in results]
            
            # Log aggregate metrics
            mlflow.log_metric("avg_wer", np.mean(wers))
            mlflow.log_metric("median_wer", np.median(wers))
            mlflow.log_metric("min_wer", np.min(wers))
            mlflow.log_metric("max_wer", np.max(wers))
            mlflow.log_metric("sample_count", len(results))
            mlflow.log_metric("avg_duration", np.mean(latency))
            
            # Create summary DataFrame
            summary_df = pd.DataFrame(results)
            
            # Save summary to CSV
            output_path = f"wer_analysis_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            summary_df.to_csv(output_path, index=False)
            mlflow.log_artifact(output_path)
            
            # Print summary
            print("\n===== Transcription Analysis Summary =====")
            print(f"Analyzed {len(results)} of {args.n_samples} requested samples")
            print(f"Average WER: {np.mean(wers):.4f}")
            print(f"Median WER: {np.median(wers):.4f}")
            print(f"Min WER: {np.min(wers):.4f}")
            print(f"Max WER: {np.max(wers):.4f}")
            print(f"Results saved to {output_path} and logged to MLflow")
            print("==========================================\n")
        else:
            logger.error("No results were produced. Check logs for errors.")

def main():
    # Run the async main function
    asyncio.run(main_async())

if __name__ == "__main__":
    main()