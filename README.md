# Text-to-Speech Web Application

A web-based Text-to-Speech (TTS) application that converts text to natural-sounding speech. The application supports both English and Chinese text input, and provides immediate playback and MP3 download options.

Live demo: [http://text2speech.help/](http://text2speech.help/)

https://github.com/EricZhou866/Text2Speech/blob/main/tts/static/tts-ui.png

## Features

- Support for both English and Chinese text
- Real-time text-to-speech conversion
- Auto language detection
- Built-in audio player
- MP3 download option
- Clean and user-friendly interface
- Mobile responsive design

## Tech Stack

- **Frontend**: HTML5, CSS3, JavaScript
- **Backend**: Python Flask
- **TTS Engine**: Google Text-to-Speech (gTTS)
- **Web Server**: Nginx
- **WSGI Server**: Gunicorn

## Installation

### Prerequisites

- Python 3.8+
- Nginx
- pip (Python package manager)

### Server Setup

1. Install required packages:
```bash
pip install flask flask-cors gtts gunicorn

2. Clone the repository:
git clone https://github.com/EricZhou866/Text2Speech
cd text-to-speech-app

3. Install Nginx:
# For CentOS/RHEL
sudo yum install nginx

# For Ubuntu/Debian
sudo apt-get install nginx

Usage

Open your web browser and navigate to your domain or IP address
Enter text in the text area (supports both English and Chinese)
Click "Convert to Speech" button
The audio will automatically play when ready
Use the download button to save the MP3 file

API Endpoints
POST /tts
Converts text to speech
Request Body:
