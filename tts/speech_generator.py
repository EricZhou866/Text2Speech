# speech_generator.py
"""
Speech generation module.
Handles TTS conversion using Edge TTS.
"""
import asyncio
import edge_tts
import logging
from typing import List
from pathlib import Path
from config import DEFAULT_TIMEOUT, VOICES, MIN_SEGMENT_LENGTH
from text_processor import TextProcessor

logger = logging.getLogger(__name__)

class SpeechGenerator:
    def __init__(self, work_dir: Path):
        """
        Initialize SpeechGenerator with working directory.
        
        Args:
            work_dir: Directory for temporary files
        """
        self.work_dir = work_dir

    async def generate_speech(self, 
                            text: str, 
                            voice: str, 
                            output_file: str, 
                            timeout: int = DEFAULT_TIMEOUT) -> bool:
        """
        Generate speech for a given text segment.
        
        Args:
            text: Text to convert to speech
            voice: Voice ID to use
            output_file: Output file path
            timeout: Maximum time to wait for generation
            
        Returns:
            bool: Success status
            
        Raises:
            ValueError: If text is empty or generation fails
        """
        try:
            text = text.strip()
            if not text:
                raise ValueError("Empty text segment")
            
            communicate = edge_tts.Communicate(text, voice)
            await asyncio.wait_for(communicate.save(output_file), timeout=timeout)
            
            if not Path(output_file).exists() or Path(output_file).stat().st_size == 0:
                raise ValueError(f"Failed to generate audio for text: {text[:50]}...")
                
            logger.info(f"Generated speech for text: '{text}'")
            return True
            
        except Exception as e:
            logger.error(f"Error generating speech: {str(e)}")
            raise

    async def process_text_chunk(self, 
                               chunk: str, 
                               voice_gender: str, 
                               session_id: str, 
                               chunk_index: int) -> List[str]:
        """
        Process a text chunk and generate speech segments.
        Handles each line separately.
        
        Args:
            chunk: Text chunk to process
            voice_gender: Gender of voice to use
            session_id: Unique session identifier
            chunk_index: Index of current chunk
            
        Returns:
            List of generated audio file paths
        """
        try:
            text_processor = TextProcessor()
            # Split the chunk into separate lines
            lines = text_processor.preprocess_text(chunk)
            chunk_files = []
            
            for i, line in enumerate(lines):
                if not line.strip():
                    continue
                    
                text_type = text_processor.detect_text_type(line)
                
                if text_type == 'en':
                    sentences = text_processor.split_english_sentences(line)
                    voice = VOICES[voice_gender]['en']
                    for j, sentence in enumerate(sentences):
                        if len(sentence.strip()) >= MIN_SEGMENT_LENGTH or sentence.strip().isdigit():
                            temp_file = self.work_dir / f'segment_{chunk_index}_{i}_{j}_{session_id}.mp3'
                            await self.generate_speech(sentence, voice, str(temp_file))
                            chunk_files.append(str(temp_file))
                            
                elif text_type == 'zh':
                    sentences = text_processor.split_chinese_text(line)
                    voice = VOICES[voice_gender]['zh']
                    for j, sentence in enumerate(sentences):
                        if len(sentence.strip()) >= 1:
                            temp_file = self.work_dir / f'segment_{chunk_index}_{i}_{j}_{session_id}.mp3'
                            await self.generate_speech(sentence, voice, str(temp_file))
                            chunk_files.append(str(temp_file))
                            
                else:  # mixed
                    segments = text_processor.split_mixed_text(line)
                    for j, (segment, lang) in enumerate(segments):
                        min_len = 1 if lang == 'zh' else MIN_SEGMENT_LENGTH
                        if len(segment.strip()) >= min_len or segment.strip().isdigit():
                            voice = VOICES[voice_gender][lang]
                            temp_file = self.work_dir / f'segment_{chunk_index}_{i}_{j}_{session_id}.mp3'
                            await self.generate_speech(segment, voice, str(temp_file))
                            chunk_files.append(str(temp_file))
            
            return chunk_files
            
        except Exception as e:
            logger.error(f"Error processing chunk: {str(e)}")
            raise
