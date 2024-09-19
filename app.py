from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS  # Import Flask-CORS
import os
import re
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip
from werkzeug.utils import secure_filename
import zipfile
from io import BytesIO
from PIL import Image  # Add this

# Patch to replace the deprecated ANTIALIAS with LANCZOS
if hasattr(Image, 'ANTIALIAS'):
    Image.Resampling = Image  # Ensure Resampling is defined
    Image.ANTIALIAS = Image.Resampling.LANCZOS  # Patch ANTIALIAS

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = './uploads'
OUTPUT_FOLDER = './output'
ALLOWED_EXTENSIONS = {'mp4'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def parse_time(time_str):
    """Parses time strings like '1m60s' into seconds"""
    match = re.match(r'((?P<minutes>\d+)m)?((?P<seconds>\d+)s)?', time_str)
    minutes = int(match.group('minutes') or 0)
    seconds = int(match.group('seconds') or 0)
    return minutes * 60 + seconds

@app.route('/upload_video', methods=['POST'])
def upload_video():
    if 'video' not in request.files or 'text_two' not in request.form:
        return jsonify({'error': 'Missing video or text inputs'}), 400
    
    video = request.files['video']
    text_two = request.form['text_two']
    start_time_str = request.form.get('start_time', '0') 
    end_time_str = request.form.get('end_time') 
    output_duration = request.form.get('output_duration')  

    if video and allowed_file(video.filename):
        filename = secure_filename(video.filename)
        video_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        video.save(video_path)

        file_number = len(os.listdir(app.config['OUTPUT_FOLDER'])) + 1
        text_one = f"Text {file_number}"

        start_time = parse_time(start_time_str) if start_time_str else 0

        original_video = VideoFileClip(video_path)
        if end_time_str:
            end_time = parse_time(end_time_str)
        else:
            end_time = original_video.duration

        output_videos = process_video(video_path, text_one, text_two, start_time, end_time, output_duration)

        zip_buffer = BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w') as zf:
            for video_file in output_videos:
                video_file_path = os.path.join(app.config['OUTPUT_FOLDER'], video_file)
                zf.write(video_file_path, video_file)

        zip_buffer.seek(0)

        return send_file(zip_buffer, mimetype='application/zip', download_name='output_videos.zip', as_attachment=True)

    else:
        return jsonify({'error': 'Invalid file format'}), 400

@app.route('/output/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['OUTPUT_FOLDER'], filename)

def process_video(video_path, text_above, text_below, start_time, end_time, output_duration):
    original_video = VideoFileClip(video_path)

    start_time = max(0, start_time)  
    end_time = min(end_time, original_video.duration)  

    segment = original_video.subclip(start_time, end_time)

    if output_duration is None:
        output_duration = segment.duration
    else:
        output_duration = float(output_duration)

    output_videos = []
    num_segments = int(segment.duration // output_duration) + (1 if segment.duration % output_duration > 0 else 0)

    for i in range(num_segments):
        segment_start = i * output_duration
        segment_end = min(segment_start + output_duration, segment.duration)
        video_segment = segment.subclip(segment_start, segment_end)

        font_path = "./fonts/ProtestGuerrilla-Regular.ttf"
        text_size = (video_segment.w, int(video_segment.h * 0.15))
        text_color = 'white'
        bg_color = 'black'
        font_size = 70

        text_above_clip = TextClip(f"Part {i+1}", fontsize=font_size, color=text_color, font=font_path, size=text_size, bg_color=bg_color).set_duration(video_segment.duration)
        text_below_clip = TextClip(text_below, fontsize=font_size, color=text_color, font=font_path, size=text_size, bg_color=bg_color).set_duration(video_segment.duration)

        resized_segment = video_segment.resize(height=1080)
        final_video = CompositeVideoClip([
            text_above_clip.set_position(("center", "top")),
            resized_segment.set_position("center"),
            text_below_clip.set_position(("center", "bottom"))
        ], size=(resized_segment.w, resized_segment.h + text_size[1] * 2))

        output_filename = f"output_segment_{text_above}_part{i+1}.mp4"
        output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
        final_video.write_videofile(output_path, codec="libx264", audio_codec="aac")

        output_videos.append(output_filename)

    original_video.close()

    return output_videos

if __name__ == '__main__':
    app.run(debug=True)
