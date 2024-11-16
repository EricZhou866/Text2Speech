from flask import Flask, request, send_file, render_template
from flask_cors import CORS
from gtts import gTTS
import os

app = Flask(__name__)
CORS(app)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/tts', methods=['POST'])
def text_to_speech():
    try:
        data = request.get_json()
        if not data or 'text' not in data:
            return {'error': 'No text provided'}, 400
            
        text = data.get('text', '')
        print(f'Converting text: {text}')
        
        # 检测语言
        is_chinese = any('\u4e00' <= char <= '\u9fff' for char in text)
        
        # 生成音频文件
        output_file = 'speech.mp3'
        
        if is_chinese:
            # 中文
            tts = gTTS(text=text, lang='zh-cn')
        else:
            # 英文（美式发音）
            tts = gTTS(text=text, lang='en', tld='com')
        
        # 保存音频文件
        tts.save(output_file)
        
        return send_file(output_file, as_attachment=True)
        
    except Exception as e:
        print(f'Error: {str(e)}')
        return {'error': str(e)}, 500
    
    finally:
        # 清理临时文件
        try:
            if os.path.exists(output_file):
                os.remove(output_file)
        except:
            pass

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
