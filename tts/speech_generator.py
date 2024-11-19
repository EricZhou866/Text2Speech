# speech_generator.py
"""
Speech generation module with improved handling of mixed language and numbers.
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
        self.text_processor = TextProcessor()

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
        Handles mixed language content and preserves number context.
        
        Args:
            chunk: Text chunk to process
            voice_gender: Gender of voice to use
            session_id: Unique session identifier
            chunk_index: Index of current chunk
            
        Returns:
            List of generated audio file paths
        """
        try:
            # Split the chunk into separate lines, preserving empty lines
            lines = chunk.split('\n')
            chunk_files = []
            
            for i, line in enumerate(lines):
                stripped_line = line.strip()
                if not stripped_line:
                    continue

                # Keep original line position for file naming
                original_index = i

                # Handle standalone numbers (e.g., line numbers)
                if stripped_line.isdigit():
                    voice = VOICES[voice_gender]['en']
                    temp_file = self.work_dir / f'segment_{chunk_index}_{original_index}_0_{session_id}.mp3'
                    await self.generate_speech(stripped_line, voice, str(temp_file))
                    chunk_files.append(str(temp_file))
                    continue

                # Detect text type for the whole line
                text_type = self.text_processor.detect_text_type(stripped_line)

                if text_type == 'en':
                    # Process English text
                    sentences = self.text_processor.split_english_sentences(stripped_line)
                    voice = VOICES[voice_gender]['en']
                    
                    for j, sentence in enumerate(sentences):
                        if len(sentence.strip()) >= MIN_SEGMENT_LENGTH or sentence.strip().isdigit():
                            temp_file = self.work_dir / f'segment_{chunk_index}_{original_index}_{j}_{session_id}.mp3'
                            await self.generate_speech(sentence, voice, str(temp_file))
                            chunk_files.append(str(temp_file))

                elif text_type == 'zh':
                    # Process Chinese text, keeping numbers in context
                    sentences = self.text_processor.split_chinese_text(stripped_line)
                    voice = VOICES[voice_gender]['zh']
                    
                    for j, sentence in enumerate(sentences):
                        if len(sentence.strip()) >= 1:
                            temp_file = self.work_dir / f'segment_{chunk_index}_{original_index}_{j}_{session_id}.mp3'
                            await self.generate_speech(sentence, voice, str(temp_file))
                            chunk_files.append(str(temp_file))

                else:  # mixed text
                    # Process mixed text with context-aware number handling
                    segments = self.text_processor.split_mixed_text(stripped_line)
                    
                    for j, (segment, lang) in enumerate(segments):
                        voice = VOICES[voice_gender][lang]
                        # Use appropriate minimum length based on language
                        min_len = 1 if lang == 'zh' else MIN_SEGMENT_LENGTH
                        
                        if len(segment.strip()) >= min_len or segment.strip().isdigit():
                            temp_file = self.work_dir / f'segment_{chunk_index}_{original_index}_{j}_{session_id}.mp3'
                            await self.generate_speech(segment, voice, str(temp_file))
                            chunk_files.append(str(temp_file))

            return chunk_files

        except Exception as e:
            logger.error(f"Error processing chunk: {str(e)}")
            raise

    async def process_single_line(self,
                                line: str,
                                voice_gender: str,
                                session_id: str,
                                line_index: int) -> List[str]:
        """
        Process a single line of text.
        Handles standalone numbers and mixed content.
        
        Args:
            line: Single line of text to process
            voice_gender: Gender of voice to use
            session_id: Unique session identifier
            line_index: Index of the line
            
        Returns:
            List of generated audio file paths
        """
        try:
            # Handle empty lines
            if not line.strip():
                return []

            # Handle standalone numbers
            if line.strip().isdigit():
                voice = VOICES[voice_gender]['en']
                temp_file = self.work_dir / f'segment_0_{line_index}_0_{session_id}.mp3'
                await self.generate_speech(line.strip(), voice, str(temp_file))
                return [str(temp_file)]

            # Process regular text
            return await self.process_text_chunk(line, voice_gender, session_id, line_index)

        except Exception as e:
            logger.error(f"Error processing line: {str(e)}")
            raise

    def cleanup_files(self, files: List[str]) -> None:
        """
        Clean up temporary audio files.
        
        Args:
            files: List of file paths to clean up
        """
        for file in files:
            try:
                path = Path(file)
                if path.exists():
                    path.unlink()
            except Exception as e:
                logger.error(f"Error cleaning up file {file}: {str(e)}")
