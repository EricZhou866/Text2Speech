from flask import Flask, request, send_file, render_template
from flask_cors import CORS
import asyncio
import edge_tts
import os
import re
import uuid
import subprocess
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

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


def merge_audio_files(input_files, output_file):
    """
    Merge audio files using FFmpeg
    """
    try:
        if not input_files:
            raise ValueError("No input files provided")

        # Create a file list for FFmpeg
        list_file = 'files.txt'
        with open(list_file, 'w') as f:
            for file in input_files:
                f.write(f"file '{file}'\n")

        # Merge files using FFmpeg
        cmd = [
            'ffmpeg',
            '-f', 'concat',
            '-safe', '0',
            '-i', list_file,
            '-c', 'copy',
            output_file
        ]

        subprocess.run(cmd, check=True, capture_output=True, text=True)
        logger.info(f"Successfully merged {len(input_files)} audio files")

        # Clean up the list file
        os.remove(list_file)

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


def cleanup_files(temp_dir, output_file):
    """
    Clean up temporary files and directories
    """
    try:
        if os.path.exists(output_file):
            os.remove(output_file)
            logger.debug(f"Removed output file: {output_file}")

        if os.path.exists(temp_dir):
            for file in os.listdir(temp_dir):
                try:
                    file_path = os.path.join(temp_dir, file)
                    os.remove(file_path)
                    logger.debug(f"Removed temp file: {file_path}")
                except Exception as e:
                    logger.error(f"Error removing temp file {file}: {str(e)}")
            os.rmdir(temp_dir)
            logger.debug(f"Removed temp directory: {temp_dir}")
    except Exception as e:
        logger.error(f"Error in cleanup: {str(e)}")


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/tts', methods=['POST'])
def text_to_speech():
    temp_dir = 'temp_audio'
    output_file = None

    try:
        # Validate input
        data = request.get_json()
        if not data or 'text' not in data:
            return {'error': 'No text provided'}, 400

        text = data.get('text', '')
        voice_gender = data.get('voice', 'male')

        if voice_gender not in VOICES:
            return {'error': 'Invalid voice type'}, 400

        logger.info(f'Converting text with {voice_gender} voice')

        # Create temporary directory
        os.makedirs(temp_dir, exist_ok=True)

        # Generate unique session ID
        session_id = str(uuid.uuid4())
        output_file = f'speech_{session_id}.mp3'

        # Split text into segments
        segments = split_text(text)
        if not segments:
            return {'error': 'No valid text segments'}, 400

        # Store temporary file paths
        temp_files = []

        # Convert each segment
        for i, (segment, is_chinese) in enumerate(segments):
            temp_file = f'{temp_dir}/segment_{i}_{session_id}.mp3'

            # Select appropriate voice
            lang = 'zh' if is_chinese else 'en'
            voice = VOICES[voice_gender][lang]

            # Generate speech for segment
            asyncio.run(generate_speech(segment, voice, temp_file))
            temp_files.append(temp_file)

        # Merge audio files
        if temp_files:
            merge_audio_files(temp_files, output_file)
            return send_file(output_file, as_attachment=True)

        return {'error': 'No audio generated'}, 500

    except Exception as e:
        logger.error(f"Error in text_to_speech: {str(e)}", exc_info=True)
        return {'error': str(e)}, 500

    finally:
        cleanup_files(temp_dir, output_file)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)