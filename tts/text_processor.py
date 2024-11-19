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
        Preprocess text by splitting into lines while preserving empty lines and numbers.
        
        Args:
            text: Input text with potential multiple lines
            
        Returns:
            List of lines, including empty ones and numbers
        """
        if not text:
            return []
            
        lines = text.split('\n')
        return [line.strip() for line in lines]

    @staticmethod
    def detect_text_type(text: str) -> str:
        """
        Detect text type including standalone numbers.
        Numbers are treated based on context.
        
        Args:
            text: Input text to analyze
            
        Returns:
            str: 'zh', 'en', or 'mixed'
        """
        if not text.strip():
            return 'en'
            
        # Handle standalone numbers
        if text.strip().isdigit():
            return 'en'

        # Check for Chinese characters and punctuation
        has_chinese = bool(re.search(r'[\u4e00-\u9fff，。！？；：""''（）、]', text))
        # Check for English characters (excluding numbers initially)
        has_english = bool(re.search(r'[a-zA-Z]', text))
        
        if has_chinese and has_english:
            return 'mixed'
        elif has_chinese:
            return 'zh'
        return 'en'

    @staticmethod
    def split_english_sentences(text: str) -> List[str]:
        """
        Split English text into natural speech segments.
        Preserves numbers and their context.
        
        Args:
            text: English text to split
            
        Returns:
            List of sentence segments
        """
        if not text.strip():
            return []

        # Handle standalone numbers
        if text.strip().isdigit():
            return [text.strip()]

        sentences = []
        current_sentence = []
        words = text.split()

        for word in words:
            current_sentence.append(word)
            
            if (word.endswith(('.', '!', '?')) or 
                word.endswith((',', ';', ':')) or 
                len(' '.join(current_sentence)) >= MAX_SEGMENT_LENGTH):
                
                # Handle abbreviations and numbers with periods
                if (word.endswith('.') and 
                    not word[:-1].isdigit() and
                    (all(c.isupper() for c in word[:-1]) or 
                     len(word) <= 3)):
                    continue
                
                sentence = ' '.join(current_sentence).strip()
                if len(sentence) >= MIN_SEGMENT_LENGTH or sentence.strip().isdigit():
                    sentences.append(sentence)
                current_sentence = []

        # Handle remaining text
        if current_sentence:
            sentence = ' '.join(current_sentence).strip()
            if len(sentence) >= MIN_SEGMENT_LENGTH or sentence.strip().isdigit():
                sentences.append(sentence)

        return sentences

    @staticmethod
    def split_chinese_text(text: str) -> List[str]:
        """
        Split Chinese text into natural segments while keeping numbers in context.
        
        Args:
            text: Chinese text to split
            
        Returns:
            List of text segments
        """
        if not text.strip():
            return []

        # For short text, keep it as one segment
        if len(text) <= MAX_SEGMENT_LENGTH:
            return [text.strip()]

        # Split by major punctuation while preserving it
        segments = re.split(r'([。！？；])', text)
        result = []
        
        i = 0
        while i < len(segments):
            current = segments[i].strip()
            
            if i + 1 < len(segments) and segments[i + 1] in '。！？；':
                current += segments[i + 1]
                i += 2
            else:
                i += 1
            
            if current:
                result.append(current)

        # Only split long segments if necessary
        final_result = []
        for segment in result:
            if len(segment) > MAX_SEGMENT_LENGTH:
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
        Process mixed Chinese-English text with context-aware number handling.
        
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

        def is_chinese_context(text: str, pos: int) -> bool:
            """Helper function to determine if a position is in Chinese context."""
            # Look at surrounding context (up to 5 chars before and after)
            pre_text = text[max(0, pos-5):pos]
            post_text = text[pos:min(len(text), pos+5)]
            
            return bool(re.search(r'[\u4e00-\u9fff]', pre_text + post_text))

        def flush_buffer():
            """Helper function to add buffered text to segments."""
            nonlocal buffer, current_type
            if buffer.strip():
                segments.append((buffer, current_type))
            buffer = ""

        while i < len(text):
            char = text[i]
            
            if re.match(r'[\u4e00-\u9fff，。！？；：""''（）、]', char):
                if current_type != 'zh':
                    flush_buffer()
                    current_type = 'zh'
                buffer += char
                
            elif char.isdigit():
                # Look ahead for complete number with symbols
                num_start = i
                while i < len(text) and (text[i].isdigit() or text[i] in '.%'):
                    i += 1
                number_with_symbols = text[num_start:i]
                i -= 1  # Adjust for main loop increment
                
                # Determine if number is in Chinese context
                if is_chinese_context(text, num_start):
                    if current_type != 'zh':
                        flush_buffer()
                        current_type = 'zh'
                else:
                    if current_type != 'en':
                        flush_buffer()
                        current_type = 'en'
                
                buffer += number_with_symbols
                
            elif re.match(r'[a-zA-Z]', char):
                if current_type != 'en':
                    flush_buffer()
                    current_type = 'en'
                buffer += char
                
            else:  # Punctuation and spaces
                if buffer:
                    buffer += char
            
            i += 1

        # Handle remaining buffer
        if buffer:
            flush_buffer()

        # Post-process segments
        return [(text.strip(), lang) for text, lang in segments 
                if text.strip() and (
                    lang == 'zh' or 
                    len(text.strip()) >= MIN_SEGMENT_LENGTH or 
                    text.strip().isdigit()
                )]
