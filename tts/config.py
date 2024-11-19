# config.py
"""
Configuration module for TTS application.
Contains all constants and configuration parameters.
"""
import os
from pathlib import Path

# Application root and temporary directories
APP_ROOT = Path(os.path.dirname(os.path.abspath(__file__)))
BASE_TEMP_DIR = APP_ROOT / 'temp'

# Text processing configurations
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

