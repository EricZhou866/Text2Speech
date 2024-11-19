from quart import Quart, request, send_file, render_template
from quart_cors import cors
import asyncio
import edge_tts
import os
import re
import uuid
import subprocess
import logging
from pathlib import Path
import tempfile
from hypercorn.config import Config
from hypercorn.asyncio import serve
import io

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Quart(__name__)
app = cors(app, allow_origin="*")

# Get application root directory
APP_ROOT = Path(os.path.dirname(os.path.abspath(__file__)))
# Define base temp directory
BASE_TEMP_DIR = APP_ROOT / 'temp'

# Configuration
MAX_SEGMENT_LENGTH = 1000
MAX_CONCURRENT_TASKS = 4
DEFAULT_TIMEOUT = 30
BUFFER_SIZE = 10485760

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


def ensure_directory_exists(directory):
    """Ensure directory exists and has correct permissions"""
    try:
        directory.mkdir(parents=True, exist_ok=True)
        try:
            directory.chmod(0o755)
        except Exception as e:
            logger.warning(f"Could not set permissions for {directory}: {e}")
    except Exception as e:
        logger.error(f"Error creating directory {directory}: {e}")
        raise


def cleanup_files(files):
    """Clean up a list of files"""
    for file in files:
        try:
            if os.path.exists(file):
                os.remove(file)
        except Exception as e:
            logger.error(f"Error removing file {file}: {str(e)}")


def cleanup_directory(directory):
    """Clean up a directory and its contents"""
    try:
        if directory and os.path.exists(directory):
            for file in os.listdir(directory):
                try:
                    os.remove(os.path.join(directory, file))
                except Exception as e:
                    logger.error(f"Error removing file {file}: {str(e)}")
            try:
                os.rmdir(directory)
                logger.debug(f"Cleaned up directory: {directory}")
            except Exception as e:
                logger.error(f"Error removing directory {directory}: {str(e)}")
    except Exception as e:
        logger.error(f"Error in cleanup: {str(e)}")


def split_text(text):
    """Split mixed text into Chinese and English segments"""
    # Pattern to handle contractions and possessives
    pattern = r"([\u4e00-\u9fff]+|[a-zA-Z0-9][a-zA-Z0-9']*[a-zA-Z0-9]+(?:\s+[a-zA-Z0-9][a-zA-Z0-9']*[a-zA-Z0-9]+)*)"
    segments = re.findall(pattern, text)

    result = []
    for segment in segments:
        segment = segment.strip()
        if not segment:
            continue
        # Check if segment contains Chinese characters
        is_chinese = bool(re.search(r'[\u4e00-\u9fff]', segment))
        # For English segments, preserve contractions and possessives
        if not is_chinese:
            # Combine with any following possessive or contraction
            if "'" in segment:
                segment = segment.strip("'")  # Remove any standalone apostrophes
        
        result.append((segment, is_chinese))
        logger.debug(f"Split segment: '{segment}' (Chinese: {is_chinese})")

    return result

def split_long_text(text, max_length=MAX_SEGMENT_LENGTH):
    """Split text into smaller chunks"""
    if len(text) <= max_length:
        return [text]

    delimiters = '.!?。！？'
    chunks = []
    current_chunk = []
    current_length = 0

    sentences = re.split(f'([{delimiters}])', text)
    for i in range(0, len(sentences), 2):
        sentence = sentences[i]
        if i + 1 < len(sentences):
            sentence += sentences[i + 1]

        if current_length + len(sentence) <= max_length:
            current_chunk.append(sentence)
            current_length += len(sentence)
        else:
            if current_chunk:
                chunks.append(''.join(current_chunk))
            current_chunk = [sentence]
            current_length = len(sentence)

    if current_chunk:
        chunks.append(''.join(current_chunk))

    return chunks


def get_temp_dir():
    """Create a unique temporary directory"""
    try:
        temp_dir = Path(tempfile.mkdtemp(prefix='tts_'))
    except Exception as e:
        logger.warning(f"Could not create temp dir in system temp: {e}")
        temp_dir = BASE_TEMP_DIR / str(uuid.uuid4())
        temp_dir.mkdir(parents=True, exist_ok=True)

    logger.debug(f"Created temporary directory: {temp_dir}")
    return temp_dir


def merge_audio_files(input_files, output_file, buffer_size=BUFFER_SIZE):
    """Merge audio files using buffered reading/writing"""
    try:
        if not input_files:
            raise ValueError("No input files provided")

        with open(output_file, 'wb') as outfile:
            for file in input_files:
                with open(file, 'rb') as infile:
                    while True:
                        buffer = infile.read(buffer_size)
                        if not buffer:
                            break
                        outfile.write(buffer)

        logger.info(f"Successfully merged {len(input_files)} audio files")

    except Exception as e:
        logger.error(f"Error merging audio files: {str(e)}")
        raise


async def generate_speech(text, voice, output_file, timeout=DEFAULT_TIMEOUT):
    """Generate speech with timeout control"""
    try:
        communicate = edge_tts.Communicate(text, voice)
        await asyncio.wait_for(communicate.save(output_file), timeout=timeout)
        logger.info(f"Generated speech for text: '{text[:50]}...' using voice: {voice}")
    except asyncio.TimeoutError:
        logger.error(f"Speech generation timed out for text: '{text[:50]}...'")
        raise
    except Exception as e:
        logger.error(f"Error generating speech: {str(e)}")
        raise


async def process_text_chunk(chunk, voice_gender, work_dir, session_id, chunk_index):
    """Process a single chunk of text"""
    segments = split_text(chunk)
    chunk_files = []

    for i, (segment, is_chinese) in enumerate(segments):
        temp_file = work_dir / f'segment_{chunk_index}_{i}_{session_id}.mp3'
        lang = 'zh' if is_chinese else 'en'
        voice = VOICES[voice_gender][lang]

        await generate_speech(segment, voice, str(temp_file))
        chunk_files.append(str(temp_file))

    return chunk_files


@app.route('/')
async def home():
    return await render_template('index.html')


@app.route('/tts', methods=['POST'])
async def text_to_speech():
    work_dir = None
    output_file = None
    all_temp_files = []

    try:
        work_dir = get_temp_dir()

        data = await request.get_json()
        if not data or 'text' not in data:
            return {'error': 'No text provided'}, 400

        text = data.get('text', '')
        voice_gender = data.get('voice', 'male')

        if voice_gender not in VOICES:
            return {'error': 'Invalid voice type'}, 400

        logger.info(f'Converting text with {voice_gender} voice')

        session_id = str(uuid.uuid4())
        output_file = work_dir / f'speech_{session_id}.mp3'

        text_chunks = split_long_text(text)

        # Process chunks with bounded concurrency
        sem = asyncio.Semaphore(MAX_CONCURRENT_TASKS)

        async def process_with_semaphore(chunk, index):
            async with sem:
                return await process_text_chunk(chunk, voice_gender, work_dir, session_id, index)

        tasks = [process_with_semaphore(chunk, i) for i, chunk in enumerate(text_chunks)]
        chunk_results = await asyncio.gather(*tasks)

        for chunk_files in chunk_results:
            all_temp_files.extend(chunk_files)

        if not all_temp_files:
            return {'error': 'No audio generated'}, 500

        # Merge audio files
        merge_audio_files(all_temp_files, str(output_file))

        # Clean up temporary segment files
        cleanup_files(all_temp_files)

        # Read the final file
        if not os.path.exists(output_file):
            raise FileNotFoundError(f"Output file not found: {output_file}")

        with open(output_file, 'rb') as f:
            data = f.read()

        # Create response
        return await send_file(
            io.BytesIO(data),
            mimetype='audio/mpeg'
        )

    except Exception as e:
        logger.error(f"Error in text_to_speech: {str(e)}", exc_info=True)
        return {'error': str(e)}, 500

    finally:
        # Clean up remaining files
        try:
            if output_file and os.path.exists(output_file):
                os.remove(output_file)
            if work_dir and os.path.exists(work_dir):
                os.rmdir(work_dir)
        except Exception as e:
            logger.error(f"Error in final cleanup: {str(e)}")


def initialize_app():
    """Initialize application directories and settings"""
    try:
        ensure_directory_exists(BASE_TEMP_DIR)
        logger.info(f"Initialized application with temp directory: {BASE_TEMP_DIR}")
    except Exception as e:
        logger.error(f"Failed to initialize application: {e}")
        raise


async def run_app():
    config = Config()
    config.bind = ["0.0.0.0:5001"]
    await serve(app, config)


if __name__ == '__main__':
    initialize_app()
    asyncio.run(run_app())
