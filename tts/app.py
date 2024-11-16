from flask import Flask, request, send_file, render_template
from flask_cors import CORS
from gtts import gTTS
import os
import re
import uuid
import subprocess

app = Flask(__name__)
CORS(app)


def split_text(text):
    """
    Split mixed text into Chinese and English segments
    Returns a list of tuples (text, is_chinese)
    """
    # Use regex to split text
    pattern = r'([\u4e00-\u9fff]+|[a-zA-Z0-9\s]+)'
    segments = re.findall(pattern, text)

    # Clean and mark each segment
    result = []
    for segment in segments:
        segment = segment.strip()
        if not segment:
            continue
        # Check if segment is Chinese
        is_chinese = bool(re.search(r'[\u4e00-\u9fff]', segment))
        result.append((segment, is_chinese))

    return result


def merge_audio_files(input_files, output_file):
    """
    Merge audio files using sox command line tool
    """
    cmd = ['sox'] + input_files + [output_file]
    subprocess.run(cmd, check=True)


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/tts', methods=['POST'])
def text_to_speech():
    try:
        # Validate input
        data = request.get_json()
        if not data or 'text' not in data:
            return {'error': 'No text provided'}, 400

        text = data.get('text', '')
        print(f'Converting text: {text}')

        # Create temporary directory
        temp_dir = 'temp_audio'
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)

        # Generate unique session ID
        session_id = str(uuid.uuid4())
        output_file = f'speech_{session_id}.mp3'

        # Split text into segments
        segments = split_text(text)

        # Store temporary file paths
        temp_files = []

        # Convert each segment
        for i, (segment, is_chinese) in enumerate(segments):
            temp_file = f'{temp_dir}/segment_{i}_{session_id}.mp3'

            # Generate speech for each segment
            if is_chinese:
                # Chinese text
                tts = gTTS(text=segment, lang='zh-cn')
            else:
                # English text (US accent)
                tts = gTTS(text=segment, lang='en', tld='com')

            tts.save(temp_file)
            temp_files.append(temp_file)

        # Process audio files
        if temp_files:
            # Merge all segments into final output
            merge_audio_files(temp_files, output_file)

            # Clean up temporary segment files
            for temp_file in temp_files:
                try:
                    os.remove(temp_file)
                except Exception as e:
                    print(f'Error removing temporary file {temp_file}: {str(e)}')

            return send_file(output_file, as_attachment=True)
        else:
            return {'error': 'No valid text segments'}, 400

    except Exception as e:
        print(f'Error: {str(e)}')
        return {'error': str(e)}, 500

    finally:
        # Clean up all temporary files
        try:
            # Remove output file
            if os.path.exists(output_file):
                os.remove(output_file)

            # Clean up temporary directory
            if os.path.exists(temp_dir):
                for file in os.listdir(temp_dir):
                    try:
                        os.remove(os.path.join(temp_dir, file))
                    except Exception as e:
                        print(f'Error cleaning up temp file: {str(e)}')
                os.rmdir(temp_dir)
        except Exception as e:
            print(f'Error in cleanup: {str(e)}')


if __name__ == '__main__':
    # Run the server
    app.run(host='0.0.0.0', port=5001, debug=True)