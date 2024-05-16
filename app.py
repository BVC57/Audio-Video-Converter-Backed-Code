from flask import Flask, jsonify, request
import os
import mysql.connector
from mysql.connector import Error
from datetime import datetime
import json
from pydub import AudioSegment
from googletrans import Translator
# from moviepy import VideoFileClip

app = Flask(__name__)

# MySQL Configuration
mysql_config = {
    'host': 'localhost',
    'database': 'convarter-db',
    'user': 'root',
    'password': ''
}


def convert_audio_to_language(file_path, language):
    # Check if the file exists
    if not os.path.exists(file_path):
        print("File not found.")
        return None

    # Load audio file
    audio = AudioSegment.from_file(file_path)

    # Initialize translator
    translator = Translator()

    # Extract text from the audio using speech recognition
    recognizer = sr.Recognizer()
    with sr.AudioFile(file_path) as source:
        audio_data = recognizer.record(source)
        audio_text = recognizer.recognize_google(audio_data)

    # Translate the text to the selected language
    translated_text = translator.translate(audio_text, dest=language)

    # Convert the translated text to audio
    translated_audio = AudioSegment.from_file(translated_text.pronunciation)

    # Save the translated audio
    translated_file_path = 'translated_audio.wav'
    translated_audio.export(translated_file_path, format='wav')

    return translated_file_path



@app.route('/')
def home():
    return "Hello, your API is ready!"

@app.route('/languageslist', methods=['GET'])
def get_languages():
    try:
        with open('languages.json', 'r', encoding='utf-8') as f:
            languages = json.load(f)
        print("JSON file opened successfully.")
        return jsonify(languages)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/upload', methods=['POST'])
def upload_file():
    lan = request.args.get('lan')
    print("selected language", lan)
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']

    try:
        # Connect to MySQL
        connection = mysql.connector.connect(**mysql_config)
        if connection.is_connected():
            print("Connected to MySQL database")
            cursor = connection.cursor()

            # Insert data into MySQL
            current_datetime = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            insert_query = "INSERT INTO uploaddetail (filename, filetype, dateandtime, status, convertlanguage) VALUES (%s, %s, %s, %s, %s)"
            file_data = (file.filename, file.content_type, current_datetime, 'processing', lan)  # Assuming 'filetype' is the content type of the file
            cursor.execute(insert_query, file_data)
            connection.commit()

            # Save the file to a specific location
            upload_folder = 'comingfiles/'
            if file.content_type.startswith('audio'):
                upload_folder += 'audio/'
            elif file.content_type.startswith('video'):
                upload_folder += 'video/'
            else:
                return jsonify({'error': 'Unsupported file type'}), 400

            # Create directory if it doesn't exist
            os.makedirs(upload_folder, exist_ok=True)

            file_path = os.path.join(upload_folder, file.filename)
            file.save(file_path)

            # Check file type and perform conversion accordingly
            if file.content_type.startswith('audio'):
                translated_file_path = convert_audio_to_language(file_path, lan)
            # elif file.content_type.startswith('video'):
            #     translated_file_path = convert_video_to_language(file_path, lan)
            else:
                return jsonify({'error': 'Unsupported file type'}), 400

            return jsonify({'message': 'File uploaded successfully', 'Converted Language': lan, 'statuscode': 200})

    except Error as e:
        print("Error while connecting to MySQL:", e)
        return jsonify({'error': 'Database error'}), 500

    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()


@app.route('/get_data', methods=['GET'])
def get_data():
    try:
        # Connect to MySQL
        connection = mysql.connector.connect(**mysql_config)
        if connection.is_connected():
            cursor = connection.cursor()

            # Query to fetch all details from the table
            select_query = "SELECT * FROM uploaddetail"
            cursor.execute(select_query)
            data = cursor.fetchall()

            # Convert the fetched data to a list of dictionaries
            result = []
            for row in data:
                result.append({
                    'filename': row[0],
                    'filetype': row[1],
                    'dateandtime': row[2].strftime('%Y-%m-%d %H:%M:%S'),  # Format the datetime
                    'status': row[3],
                    'convertlanguage': row[4]
                })

            return jsonify(result)

    except Error as e:
        print("Error while connecting to MySQL:", e)
        return jsonify({'error': 'Database error'}), 500

    finally:
        if 'connection' in locals() and connection.is_connected():
            cursor.close()
            connection.close()
            
            
if __name__ == '__main__':
    app.run(debug=True)
