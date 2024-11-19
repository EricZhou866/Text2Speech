# utils.py
"""
Utility functions for file and directory operations.
"""
import os
import uuid
import tempfile
import logging
from pathlib import Path
from typing import List
from config import BASE_TEMP_DIR  # Changed from relative import

logger = logging.getLogger(__name__)

class FileManager:
    @staticmethod
    def ensure_directory_exists(directory: Path) -> None:
        """
        Ensure directory exists and has correct permissions.
        
        Args:
            directory: Directory path to check/create
        """
        try:
            directory.mkdir(parents=True, exist_ok=True)
            try:
                directory.chmod(0o755)
            except Exception as e:
                logger.warning(f"Could not set permissions for {directory}: {e}")
        except Exception as e:
            logger.error(f"Error creating directory {directory}: {e}")
            raise

    @staticmethod
    def cleanup_files(files: List[str]) -> None:
        """
        Clean up a list of temporary files.
        
        Args:
            files: List of file paths to remove
        """
        for file in files:
            try:
                if os.path.exists(file):
                    os.remove(file)
            except Exception as e:
                logger.error(f"Error removing file {file}: {str(e)}")

    @staticmethod
    def get_temp_dir() -> Path:
        """
        Create a unique temporary directory.
        
        Returns:
            Path to temporary directory
        """
        try:
            temp_dir = Path(tempfile.mkdtemp(prefix='tts_'))
        except Exception as e:
            logger.warning(f"Could not create temp dir in system temp: {e}")
            temp_dir = BASE_TEMP_DIR / str(uuid.uuid4())
            temp_dir.mkdir(parents=True, exist_ok=True)
        return temp_dir

    @staticmethod
    def merge_audio_files(input_files: List[str], output_file: str) -> None:
        """
        Merge multiple audio files into one.
        
        Args:
            input_files: List of input file paths
            output_file: Output file path
        """
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
