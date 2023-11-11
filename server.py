import os
import random
from datetime import datetime

import string
import logging
from base64 import b64decode
from flask import Flask, request, redirect, url_for, send_from_directory
from werkzeug.utils import secure_filename
from gun_detector import Detector

import logging
logging.basicConfig(filename='flask.log',level=logging.INFO)

UPLOAD_FOLDER = 'mydata/uploads'
ALLOWED_EXTENSIONS = set(['mp4', 'avi'])
RESULTS_FOLDER = 'mydata/results'

app = Flask(__name__)

if not os.path.exists(UPLOAD_FOLDER):
    os.mkdir(UPLOAD_FOLDER)

if not os.path.exists(RESULTS_FOLDER):
    os.mkdir(RESULTS_FOLDER)


arguments = {'weightsPath': "runs/train/exp12/weights/best.pt",
             'fps': 1}

detector = Detector(**arguments)

@app.route("/")
def main():
    filename = request.args.get('file', default=None)
    head = """<head>
    <title>Детекция вооруженных людей</title>
    <style>
        * {
            font-family: Cambria;
        }
        div#loading {
            width: 35px;
            height: 35px;
            display: none;
            background: url(/static/loading.gif) no-repeat;
            cursor: wait;
        }
    </style>
    <script type="text/javascript">
        function loading() {
            document.getElementById("loading").style.display = "block";
        }

        function main() {
            var button = document.getElementById('button');

            document.getElementById('file').addEventListener('change', function () {
                if (this.value.length > 0) {
                    button.disabled = false;
                } else {
                    button.disabled = true;
                }
            });
        }

        window.onload = main;
    </script>
    </head>"""
    html = ""
    if filename != None:
        filename = secure_filename(filename)
        url = url_for('uploaded_file', filename=filename)
        filename = os.path.join(UPLOAD_FOLDER, filename)
        if os.path.exists(filename):
            error = False
            try:
                results = detector.detect(filename)
            except Exception as exc:
                error = True
                results = []
                if str(exc) == "No face detected!":
                    html += "<h1> Лицо не найдено </h1>"
                else:
                    html += "<h1> Возникла неизвестная ошибка: " + str(exc) + "</h1>"
                    app.logger.info("Unknown error: %s", str(exc))
        else:
            results = []
        
        if results and not error:
            for i, path in enumerate(results):
                url = url_for('results_file', filename=path)
                html += "<img src='{}' height='600'></img><br>".format(url)
            app.logger.info("Found %d guns", len(results))
        elif results == [] and not error:
            html += "<h2> Признаков наличия оружия не найдено. </h2>"
            app.logger.info("Guns not found")
            
    return head + f"""
    <form method="post" enctype="multipart/form-data" action="{url_for('upload')}">
        <label for="file"> Загрузить видео </label> <br>
        <input type="file" id="file" name="file" accept="video/mp4, video/avi" required> <br><br>
        <input type="submit" id="button" value="Отправить" onclick="loading();" disabled="true">
    </form><div id="loading" style="display:none"></div>
    """ + html

def allowed_file(filename):
    filename = filename.lower()
    return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

def random_word(length):
   r = random.Random(datetime.now().timestamp())
   return ''.join(r.choices(string.ascii_lowercase, k=length))

@app.route("/api/upload", methods=['post'])
def upload():
    # check if the post request has the file part
    if 'file' not in request.files:
        raise(RuntimeError('No file part'))
    file = request.files['file']
    # if user does not select file, browser also
    # submit an empty part without filename
    if file.filename == '':
        raise(RuntimeError('No selected file'))
    if file and allowed_file(file.filename):
        app.logger.info("File uploaded: %s", file.filename)
        ext = file.filename.rsplit('.', 1)[1]
        filename = None
        while filename == None or os.path.exists(filename):
            filename = random_word(10)
            filename = filename + "." + ext
        file.save(os.path.join(UPLOAD_FOLDER, filename))
        return redirect(url_for('main',
                                file=filename))

@app.route("/api/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER,
                               filename)

@app.route("/api/results/<path:filename>")
def results_file(filename):
    return send_from_directory(RESULTS_FOLDER,
                               filename)

@app.route('/static/<path:path>')
def send_report(path):
    return send_from_directory('static', path)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=25169, threaded=True)