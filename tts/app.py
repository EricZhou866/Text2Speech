from quart import Quart, request, send_file, render_template
from quart_cors import cors
import asyncio
import edge_tts
import os
import re
import uuid
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
MIN_SEGMENT_LENGTH = 2
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

def detect_text_type(text):
    """
    Detect text type: pure Chinese, pure English, or mixed
    Returns: 'zh', 'en', or 'mixed'
    """
    has_chinese = bool(re.search(r'[\u4e00-\u9fff]', text))
    has_english = bool(re.search(r'[a-zA-Z]', text))
    
    if has_chinese and has_english:
        return 'mixed'
    elif has_chinese:
        return 'zh'
    else:
        return 'en'

def split_english_sentences(text):
    """
    Intelligently split English text into natural speech segments
    """
    if not text.strip():
        return []

    sentences = []
    current_sentence = []
    words = text.split()

    for word in words:
        current_sentence.append(word)
        
        # Check if this is end of a sentence or clause
        if (word.endswith(('.', '!', '?')) or 
            word.endswith((',', ';', ':')) or 
            len(' '.join(current_sentence)) >= MAX_SEGMENT_LENGTH):
            
            # Don't split on periods in numbers or abbreviations
            if (word.endswith('.') and 
                (word[:-1].isdigit() or 
                 all(c.isupper() for c in word[:-1]) or 
                 len(word) <= 3)):
                continue
            
            sentence = ' '.join(current_sentence).strip()
            if len(sentence) >= MIN_SEGMENT_LENGTH:
                sentences.append(sentence)
            current_sentence = []

    # Add any remaining words
    if current_sentence:
        sentence = ' '.join(current_sentence).strip()
        if len(sentence) >= MIN_SEGMENT_LENGTH:
            sentences.append(sentence)

    return sentences

def split_chinese_text(text):
    """
    Split Chinese text into natural segments
    """
    if not text.strip():
        return []

    # First split by major punctuation
    segments = re.split(r'([。！？；])', text)
    result = []
    
    # Combine segments with their punctuation
    i = 0
    while i < len(segments):
        current = segments[i].strip()
        
        # Add punctuation if available
        if i + 1 < len(segments) and segments[i + 1] in '。！？；':
            current += segments[i + 1]
            i += 2
        else:
            i += 1
        
        # Only add non-empty segments
        if current:
            result.append(current)
    
    # Further split long segments if needed
    final_result = []
    for segment in result:
        if len(segment) > MAX_SEGMENT_LENGTH:
            # Split by commas
            subsegments = re.split(r'([，,])', segment)
            current = ''
            
            for j in range(0, len(subsegments), 2):
                part = subsegments[j]
                if j + 1 < len(subsegments):
                    part += subsegments[j + 1]  # Add back the punctuation
                
                if len(current + part) <= MAX_SEGMENT_LENGTH:
                    current += part
                else:
                    if current:
                        final_result.append(current)
                    current = part
            
            if current:
                final_result.append(current)
        else:
            final_result.append(segment)
    
    return [s for s in final_result if len(s.strip()) >= 1]

def split_mixed_text(text):
    """
    Process mixed Chinese-English text with improved handling
    """
    if not text.strip():
        return []

    segments = []
    current_segment = []
    current_type = None
    buffer = []
    
    def flush_buffer():
        nonlocal buffer
        if buffer:
            text = ''.join(buffer).strip()
            if text:
                if current_type == 'en' and len(text) >= MIN_SEGMENT_LENGTH:
                    segments.append((text, 'en'))
                elif current_type == 'zh' and len(text) >= 1:
                    segments.append((text, 'zh'))
            buffer = []

    for char in text:
        # Detect character type
        if re.match(r'[\u4e00-\u9fff]', char):
            char_type = 'zh'
        elif re.match(r'[a-zA-Z0-9]', char):
            char_type = 'en'
        else:
            # Keep punctuation and spaces with current segment
            if buffer:
                buffer.append(char)
            continue

        # If type changes, flush buffer
        if current_type and char_type != current_type:
            flush_buffer()
            
        buffer.append(char)
        current_type = char_type

    # Flush any remaining content
    flush_buffer()

    return segments

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

def get_temp_dir():
    """Create a unique temporary directory"""
    try:
        temp_dir = Path(tempfile.mkdtemp(prefix='tts_'))
    except Exception as e:
        logger.warning(f"Could not create temp dir in system temp: {e}")
        temp_dir = BASE_TEMP_DIR / str(uuid.uuid4())
        temp_dir.mkdir(parents=True, exist_ok=True)
    return temp_dir

def merge_audio_files(input_files, output_file):
    """Merge audio files using buffered reading/writing"""
    try:
        if not input_files:
            raise ValueError("No input files provided")

        with open(output_file, 'wb') as outfile:
            for file in input_files:
                try:
                    with open(file, 'rb') as infile:
                        outfile.write(infile.read())
                except Exception as e:
                    logger.error(f"Error reading file {file}: {str(e)}")
                    raise

    except Exception as e:
        logger.error(f"Error merging audio files: {str(e)}")
        raise

async def generate_speech(text, voice, output_file, timeout=DEFAULT_TIMEOUT):
    """Generate speech with improved error handling"""
    try:
        text = text.strip()
        if not text:
            raise ValueError("Empty text segment")
        
        communicate = edge_tts.Communicate(text, voice)
        await asyncio.wait_for(communicate.save(output_file), timeout=timeout)
        
        # Verify file was created successfully
        if not os.path.exists(output_file) or os.path.getsize(output_file) == 0:
            raise ValueError(f"Failed to generate audio for text: {text[:50]}...")
            
        logger.info(f"Generated speech for text: '{text[:50]}...'")
        return True
        
    except Exception as e:
        logger.error(f"Error generating speech: {str(e)}")
        raise

async def process_text_chunk(chunk, voice_gender, work_dir, session_id, chunk_index):
    """Process a text chunk with improved error handling"""
    try:
        chunk = chunk.strip()
        if not chunk:
            return []

        text_type = detect_text_type(chunk)
        chunk_files = []
        
        if text_type == 'en':
            sentences = split_english_sentences(chunk)
            voice = VOICES[voice_gender]['en']
            for i, sentence in enumerate(sentences):
                if len(sentence.strip()) >= MIN_SEGMENT_LENGTH:
                    temp_file = work_dir / f'segment_{chunk_index}_{i}_{session_id}.mp3'
                    await generate_speech(sentence, voice, str(temp_file))
                    chunk_files.append(str(temp_file))
                    
        elif text_type == 'zh':
            sentences = split_chinese_text(chunk)
            voice = VOICES[voice_gender]['zh']
            for i, sentence in enumerate(sentences):
                if len(sentence.strip()) >= 1:
                    temp_file = work_dir / f'segment_{chunk_index}_{i}_{session_id}.mp3'
                    await generate_speech(sentence, voice, str(temp_file))
                    chunk_files.append(str(temp_file))
                    
        else:  # mixed
            segments = split_mixed_text(chunk)
            for i, (segment, lang) in enumerate(segments):
                min_len = 1 if lang == 'zh' else MIN_SEGMENT_LENGTH
                if len(segment.strip()) >= min_len:
                    voice = VOICES[voice_gender][lang]
                    temp_file = work_dir / f'segment_{chunk_index}_{i}_{session_id}.mp3'
                    await generate_speech(segment, voice, str(temp_file))
                    chunk_files.append(str(temp_file))
        
        return chunk_files
        
    except Exception as e:
        logger.error(f"Error processing chunk: {str(e)}")
        raise

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

        text = data.get('text', '').strip()
        if not text:
            return {'error': 'Empty text provided'}, 400

        voice_gender = data.get('voice', 'male')
        if voice_gender not in VOICES:
            return {'error': 'Invalid voice type'}, 400

        logger.info(f'Processing text with {voice_gender} voice')

        session_id = str(uuid.uuid4())
        output_file = work_dir / f'speech_{session_id}.mp3'

        # Process text
        sem = asyncio.Semaphore(MAX_CONCURRENT_TASKS)

        async def process_with_semaphore(text_chunk, index):
            async with sem:
                return await process_text_chunk(text_chunk, voice_gender, work_dir, session_id, index)

        # Initial chunk processing
        tasks = [process_with_semaphore(text, 0)]
        chunk_results = await asyncio.gather(*tasks)

        for chunk_files in chunk_results:
            all_temp_files.extend(chunk_files)

        if not all_temp_files:
            return {'error': 'No audio generated'}, 500

        # Merge audio files
        merge_audio_files(all_temp_files, str(output_file))

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
                cleanup_files(all_temp_files)
            if output_file and os.path.exists(output_file):
                os.remove(output_file)
            if work_dir and os.path.exists(work_dir):
                if os.path.isdir(work_dir):
                    os.rmdir(work_dir)
        except Exception as e:
            logger.error(f"Error in cleanup: {str(e)}")

def initialize_app():
    """Initialize application"""
    ensure_directory_exists(BASE_TEMP_DIR)

async def run_app():
    """Run the application"""
    config = Config()
    config.bind = ["0.0.0.0:5001"]
    await serve(app, config)

if __name__ == '__main__':
    initialize_app()
    asyncio.run(run_app())
