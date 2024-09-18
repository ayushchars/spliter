import os
import shutil
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS  # Import CORS
from moviepy.editor import VideoFileClip
import tempfile  # For creating temporary directories

app = Flask(__name__)
CORS(app)  # Enable CORS for the entire app

# Endpoint to process the video and zip the output
@app.route('/process-video', methods=['POST'])
def process_video():
    if 'video' not in request.files:
        return jsonify({'error': 'No video file provided.'}), 400
    
    video = request.files['video']
    
    # Create a temporary directory for the output
    with tempfile.TemporaryDirectory() as output_dir:
        video_path = os.path.join(output_dir, video.filename)
        video.save(video_path)
        
        # Load the video and process
        original_video = VideoFileClip(video_path)
        segment_duration = 60
        total_duration = original_video.duration
        segment_count = int(total_duration // segment_duration) + (1 if total_duration % segment_duration > 0 else 0)
        
        # Generate segments and save them in the temporary directory
        for i in range(segment_count):
            start_time = i * segment_duration
            end_time = min((i + 1) * segment_duration, total_duration)
            segment = original_video.subclip(start_time, end_time)
            segment_filename = f"segment_{i+1}.mp4"
            output_path = os.path.join(output_dir, segment_filename)
            segment.write_videofile(output_path, codec="libx264", audio_codec="aac")

        original_video.close()

        # Create a ZIP archive of the output folder
        zip_output = shutil.make_archive(os.path.join(output_dir, 'output'), 'zip', output_dir)

        # Send the ZIP file as the response
        return send_file(zip_output, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
