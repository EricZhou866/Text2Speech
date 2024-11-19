# Text-to-Speech Web Application

A web-based Text-to-Speech (TTS) application that converts text to natural-sounding speech. The application supports both English and Chinese text input, and provides immediate playback and MP3 download options.

Live demo: [http://text2speech.help/](http://text2speech.help/)

![Main Interface](https://github.com/EricZhou866/Text2Speech/blob/main/tts/static/tts-ui.png)


## Project Structure

```
tts-backend/
├── config.py           # Configuration settings and constants
├── text_processor.py   # Text processing and segmentation logic
├── speech_generator.py # TTS conversion using Edge TTS
├── utils.py           # File and directory management utilities
├── app.py             # Main application and API routes
├── requirements.txt   # Project dependencies
└── templates/         # HTML templates
    └── index.html     # Web interface template
```

## Key Features

- Multi-language support (English and Chinese)
- Mixed language processing
- Male and female voices
- Intelligent text segmentation
- Concurrent speech generation
- Automatic file cleanup
- Error handling and logging

## Components

### 1. Configuration (config.py)
- Application constants
- Voice configurations
- Path settings
- Processing parameters

### 2. Text Processor (text_processor.py)
- Language detection
- Text segmentation for different languages
- Mixed language handling
- Intelligent sentence splitting

### 3. Speech Generator (speech_generator.py)
- TTS conversion using Edge TTS
- Chunk processing
- Voice selection
- Audio file generation

### 4. Utilities (utils.py)
- File management
- Directory operations
- Audio file merging
- Cleanup routines

### 5. Main Application (app.py)
- HTTP routes
- Request handling
- Error management
- Application initialization

## API Endpoints

### POST /tts
Converts text to speech.

Request body:
```json
{
    "text": "Text to convert to speech",
    "voice": "male" // or "female"
}
```

Response: Audio file (MP3 format)

## Setup and Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Start the server:
```bash
python app.py
```

The server will start on port 5001.

## Error Handling

- Comprehensive error logging
- Proper cleanup of temporary files
- User-friendly error messages
- Request validation

## Notes on Usage

- Maximum segment length: 1000 characters
- Minimum English segment length: 2 characters
- Minimum Chinese segment length: 1 character
- Concurrent tasks limit: 4
- Default timeout: 30 seconds

## Maintenance

- Regular cleanup of temporary files
- Logging for debugging and monitoring
- Error tracking and reporting
