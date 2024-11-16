from flask import Flask, request, send_file, render_template
from flask_cors import CORS
import asyncio
import edge_tts
import os
import re
import uuid
import subprocess
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Define base temp directory
BASE_TEMP_DIR = Path("/home/rslsync/vps/pd/Text2Speech/tts/temp")

# Voice configurations
VOICES = {
    'male': {
        'en': 'en-US-ChristopherNeural',
        'zh': 'zh-CN-YunxiNeural'
    },
    'female': {
        'en': 'en-US-JennyNeural',
        'zh': 'zh-CN-XiaoxiaoNeural'
    }
}

def split_text(text):
    """
    Split mixed text into Chinese and English segments
    Returns a list of tuples (text, is_chinese)
    """
    pattern = r'([\u4e00-\u9fff]+|[a-zA-Z0-9\s]+)'
    segments = re.findall(pattern, text)
    
    result = []
    for segment in segments:
        segment = segment.strip()
        if not segment:
            continue
        is_chinese = bool(re.search(r'[\u4e00-\u9fff]', segment))
        result.append((segment, is_chinese))
        logger.debug(f"Split segment: '{segment}' (Chinese: {is_chinese})")
    
    return result

def get_temp_dir():
    """Create a unique temporary directory"""
    temp_dir = BASE_TEMP_DIR / str(uuid.uuid4())
    temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir

def merge_audio_files(input_files, output_file):
    """
    Merge audio files using pure Python
    """
    try:
        if not input_files:
            raise ValueError("No input files provided")

        with open(output_file, 'wb') as outfile:
            for file in input_files:
                with open(file, 'rb') as infile:
                    outfile.write(infile.read())
                    
        logger.info(f"Successfully merged {len(input_files)} audio files")
        
    except Exception as e:
        logger.error(f"Error merging audio files: {str(e)}")
        raise

async def generate_speech(text, voice, output_file):
    """
    Generate speech using edge-tts
    """
    try:
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_file)
        logger.info(f"Generated speech for text: '{text[:50]}...' using voice: {voice}")
    except Exception as e:
        logger.error(f"Error generating speech: {str(e)}")
        raise

def cleanup_directory(directory):
    """Clean up a directory and its contents"""
    try:
        if directory.exists():
            for file in directory.glob('*'):
                try:
                    file.unlink()
                except Exception as e:
                    logger.error(f"Error removing file {file}: {str(e)}")
            directory.rmdir()
            logger.debug(f"Cleaned up directory: {directory}")
    except Exception as e:
        logger.error(f"Error in cleanup: {str(e)}")

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/tts', methods=['POST'])
def text_to_speech():
    work_dir = None
    output_file = None
    
    try:
        # Create working directory
        work_dir = get_temp_dir()
        
        # Validate input
        data = request.get_json()
        if not data or 'text' not in data:
            return {'error': 'No text provided'}, 400

        text = data.get('text', '')
        voice_gender = data.get('voice', 'male')
        
        if voice_gender not in VOICES:
            return {'error': 'Invalid voice type'}, 400

        logger.info(f'Converting text with {voice_gender} voice')

        # Generate unique session ID
        session_id = str(uuid.uuid4())
        output_file = work_dir / f'speech_{session_id}.mp3'

        # Split text into segments
        segments = split_text(text)
        if not segments:
            return {'error': 'No valid text segments'}, 400

        # Store temporary file paths
        temp_files = []

        # Convert each segment
        for i, (segment, is_chinese) in enumerate(segments):
            temp_file = work_dir / f'segment_{i}_{session_id}.mp3'
            
            # Select appropriate voice
            lang = 'zh' if is_chinese else 'en'
            voice = VOICES[voice_gender][lang]
            
            # Generate speech for segment
            asyncio.run(generate_speech(segment, voice, str(temp_file)))
            temp_files.append(str(temp_file))

        # Merge audio files
        if temp_files:
            merge_audio_files(temp_files, str(output_file))
            return send_file(str(output_file), as_attachment=True)
        
        return {'error': 'No audio generated'}, 500

    except Exception as e:
        logger.error(f"Error in text_to_speech: {str(e)}", exc_info=True)
        return {'error': str(e)}, 500

    finally:
        if work_dir:
            cleanup_directory(work_dir)

if __name__ == '__main__':
    # Ensure base temp directory exists
    BASE_TEMP_DIR.mkdir(parents=True, exist_ok=True)
    app.run(host='0.0.0.0', port=5001, debug=True)
