# app.py
"""
Main application module.
Handles HTTP routes and request processing.
"""
from quart import Quart, request, send_file, render_template
from quart_cors import cors
import asyncio
import logging
import uuid
import io
from hypercorn.config import Config
from hypercorn.asyncio import serve
from config import (
    MAX_CONCURRENT_TASKS, 
    VOICES,
    BASE_TEMP_DIR  # Added this import
)
from speech_generator import SpeechGenerator
from utils import FileManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Quart(__name__)
app = cors(app, allow_origin="*")

@app.route('/')
async def home():
    """Render the home page."""
    return await render_template('index.html')

@app.route('/tts', methods=['POST'])
async def text_to_speech():
    """
    Convert text to speech.
    Expects JSON with 'text' and optional 'voice' fields.
    """
    work_dir = None
    output_file = None
    all_temp_files = []

    try:
        work_dir = FileManager.get_temp_dir()

        data = await request.get_json()
        if not data or 'text' not in data:
            return {'error': 'No text provided'}, 400

        text = data.get('text', '').strip()
        if not text:
            return {'error': 'Empty text provided'}, 400

        voice_gender = data.get('voice', 'male')
        if voice_gender not in VOICES:
            return {'error': 'Invalid voice type'}, 400

        logger.info(f'Processing text with {voice_gender} voice')

        session_id = str(uuid.uuid4())
        output_file = work_dir / f'speech_{session_id}.mp3'

        speech_generator = SpeechGenerator(work_dir)
        sem = asyncio.Semaphore(MAX_CONCURRENT_TASKS)

        async def process_with_semaphore(text_chunk, index):
            async with sem:
                return await speech_generator.process_text_chunk(text_chunk, voice_gender, session_id, index)

        tasks = [process_with_semaphore(text, 0)]
        chunk_results = await asyncio.gather(*tasks)

        for chunk_files in chunk_results:
            all_temp_files.extend(chunk_files)

        if not all_temp_files:
            return {'error': 'No audio generated'}, 500

        FileManager.merge_audio_files(all_temp_files, str(output_file))

        # Read the final file
        with open(output_file, 'rb') as f:
            data = f.read()

        return await send_file(
            io.BytesIO(data),
            mimetype='audio/mpeg'
        )

    except Exception as e:
        logger.error(f"Error in text_to_speech: {str(e)}", exc_info=True)
        return {'error': str(e)}, 500

    finally:
        # Clean up
        try:
            if all_temp_files:
                FileManager.cleanup_files(all_temp_files)
            if output_file and output_file.exists():
                output_file.unlink()
            if work_dir and work_dir.exists():
                work_dir.rmdir()
        except Exception as e:
            logger.error(f"Error in cleanup: {str(e)}")

async def run_app():
    """Run the application with Hypercorn server."""
    config = Config()
    config.bind = ["0.0.0.0:5001"]
    await serve(app, config)

def initialize_app():
    """Initialize application directories and settings."""
    FileManager.ensure_directory_exists(BASE_TEMP_DIR)

if __name__ == '__main__':
    initialize_app()
    asyncio.run(run_app())
