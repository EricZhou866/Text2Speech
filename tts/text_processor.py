# text_processor.py
"""
Text processing module.
Handles text segmentation and language detection.
"""
import re
from typing import List, Tuple
from config import MAX_SEGMENT_LENGTH, MIN_SEGMENT_LENGTH  # Changed from relative import

class TextProcessor:
    @staticmethod
    def detect_text_type(text: str) -> str:
        """
        Detect text type: pure Chinese, pure English, or mixed.
        
        Args:
            text: Input text to analyze
            
        Returns:
            str: 'zh', 'en', or 'mixed'
        """
        has_chinese = bool(re.search(r'[\u4e00-\u9fff]', text))
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
        
        Args:
            text: English text to split
            
        Returns:
            List of sentence segments
        """
        if not text.strip():
            return []

        sentences = []
        current_sentence = []
        words = text.split()

        for word in words:
            current_sentence.append(word)
            
            if (word.endswith(('.', '!', '?')) or 
                word.endswith((',', ';', ':')) or 
                len(' '.join(current_sentence)) >= MAX_SEGMENT_LENGTH):
                
                if (word.endswith('.') and 
                    (word[:-1].isdigit() or 
                     all(c.isupper() for c in word[:-1]) or 
                     len(word) <= 3)):
                    continue
                
                sentence = ' '.join(current_sentence).strip()
                if len(sentence) >= MIN_SEGMENT_LENGTH:
                    sentences.append(sentence)
                current_sentence = []

        if current_sentence:
            sentence = ' '.join(current_sentence).strip()
            if len(sentence) >= MIN_SEGMENT_LENGTH:
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
        
        final_result = []
        for segment in result:
            if len(segment) > MAX_SEGMENT_LENGTH:
                subsegments = re.split(r'([，,])', segment)
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
        Process mixed Chinese-English text.
        
        Args:
            text: Mixed language text to split
            
        Returns:
            List of tuples (text_segment, language_code)
        """
        if not text.strip():
            return []

        segments = []
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
            if re.match(r'[\u4e00-\u9fff]', char):
                char_type = 'zh'
            elif re.match(r'[a-zA-Z0-9]', char):
                char_type = 'en'
            else:
                if buffer:
                    buffer.append(char)
                continue

            if current_type and char_type != current_type:
                flush_buffer()
                
            buffer.append(char)
            current_type = char_type

        flush_buffer()
        return segments

