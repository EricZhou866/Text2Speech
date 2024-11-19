# text_processor.py
"""
Text processing module for multilingual TTS system.
Handles text segmentation, language detection, and context-aware number processing.
"""
import re
from typing import List, Tuple
from config import MAX_SEGMENT_LENGTH, MIN_SEGMENT_LENGTH

class TextProcessor:
    @staticmethod
    def preprocess_text(text: str) -> List[str]:
        """
        Preprocess text by splitting into lines, preserving all content including numbers.
        
        Args:
            text: Input text with potential multiple lines
            
        Returns:
            List of lines, including empty ones and numbers
        """
        if not text:
            return []
            
        # Split text into lines but keep empty lines
        lines = text.split('\n')
        return [line.strip() for line in lines]

    @staticmethod
    def detect_text_type(text: str) -> str:
        """
        Detect text type including pure numbers.
        
        Args:
            text: Input text to analyze
            
        Returns:
            str: 'zh', 'en', or 'mixed'
        """
        # Special case for pure numbers
        if text.strip().isdigit():
            return 'en'

        # Chinese character detection (including punctuation)
        has_chinese = bool(re.search(r'[\u4e00-\u9fff，。！？；：""''（）、]', text))
        # English character detection (including letters and common punctuation)
        has_english = bool(re.search(r'[a-zA-Z]', text))

        if has_chinese and has_english:
            return 'mixed'
        elif has_chinese:
            return 'zh'
        return 'en'

    @staticmethod
    def split_english_sentences(text: str) -> List[str]:
        """
        Split English text into natural speech segments, preserving numbers.
        
        Args:
            text: English text to split
            
        Returns:
            List of sentence segments
        """
        if not text.strip():
            return []

        # Handle standalone numbers and very short text
        if text.strip().isdigit():
            return [text.strip()]

        # Normal sentence processing
        sentences = []
        current_sentence = []
        words = text.split()

        for word in words:
            current_sentence.append(word)
            
            if (word.endswith(('.', '!', '?')) or 
                word.endswith((',', ';', ':')) or 
                len(' '.join(current_sentence)) >= MAX_SEGMENT_LENGTH):
                
                # Handle abbreviations
                if (word.endswith('.') and 
                    not word[:-1].isdigit() and
                    (all(c.isupper() for c in word[:-1]) or 
                     len(word) <= 3)):
                    continue
                
                sentence = ' '.join(current_sentence).strip()
                if len(sentence) >= MIN_SEGMENT_LENGTH or any(c.isdigit() for c in sentence):
                    sentences.append(sentence)
                current_sentence = []

        # Handle remaining text
        if current_sentence:
            sentence = ' '.join(current_sentence).strip()
            if len(sentence) >= MIN_SEGMENT_LENGTH or any(c.isdigit() for c in sentence):
                sentences.append(sentence)

        return sentences

    @staticmethod
    def split_chinese_text(text: str) -> List[str]:
        """
        Split Chinese text into natural segments.
        
        Args:
            text: Chinese text to split
            
        Returns:
            List of text segments
        """
        if not text.strip():
            return []

        # Split by major punctuation while preserving the punctuation
        segments = re.split(r'([。！？；])', text)
        result = []
        
        i = 0
        while i < len(segments):
            current = segments[i].strip()
            
            # Add punctuation if available
            if i + 1 < len(segments) and segments[i + 1] in '。！？；':
                current += segments[i + 1]
                i += 2
            else:
                i += 1
            
            if current:
                result.append(current)
        
        final_result = []
        for segment in result:
            if len(segment) > MAX_SEGMENT_LENGTH:
                # Split by minor punctuation for long segments
                subsegments = re.split(r'([，、：])', segment)
                current = ''
                
                for j in range(0, len(subsegments), 2):
                    part = subsegments[j]
                    if j + 1 < len(subsegments):
                        part += subsegments[j + 1]
                    
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

    @staticmethod
    def split_mixed_text(text: str) -> List[Tuple[str, str]]:
        """
        Process mixed Chinese-English text with context-aware handling.
        
        Args:
            text: Mixed language text to split
            
        Returns:
            List of tuples (text_segment, language_code)
        """
        if not text.strip():
            return []

        # Handle standalone numbers
        if text.strip().isdigit():
            return [(text.strip(), 'en')]

        segments = []
        current_type = None
        buffer = ""
        i = 0

        def flush_buffer():
            nonlocal buffer, current_type
            if buffer.strip():
                segments.append((buffer, current_type))
            buffer = ""

        while i < len(text):
            char = text[i]
            
            # Chinese character detection
            if re.match(r'[\u4e00-\u9fff，。！？；：""''（）、]', char):
                if current_type != 'zh':
                    flush_buffer()
                    current_type = 'zh'
                buffer += char
                
            # English character detection
            elif char.isdigit() or re.match(r'[a-zA-Z]', char):
                if current_type != 'en':
                    flush_buffer()
                    current_type = 'en'
                buffer += char
                
            # Punctuation and spaces
            else:
                if buffer:
                    buffer += char
            
            i += 1

        # Handle remaining buffer
        if buffer:
            flush_buffer()

        # Post-process segments
        processed_segments = []
        for text, lang in segments:
            text = text.strip()
            if text:
                # Include segment if it meets length requirements or contains numbers
                if (lang == 'zh' and len(text) >= 1) or \
                   (lang == 'en' and (len(text) >= MIN_SEGMENT_LENGTH or text.isdigit())):
                    processed_segments.append((text, lang))

        return processed_segments
