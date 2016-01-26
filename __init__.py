from __future__ import print_function
import os
from flask import Flask, render_template, request, redirect, url_for, send_from_directory
from werkzeug import secure_filename

UPLOAD_FOLDER = '/app/input'
ALLOWED_EXTENSIONS = set(['txt','xls','xlsx','csv','tsv','md'])

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 100*1024*1024 #set max upload file size to 100mb

def allowed_file(filename):
	return '.' in filename and \
		filename.rsplit('.',1)[1] in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET','POST'])
def upload_file():
	if request.method == 'POST':
		file = request.files['files']
		if file and allowed_file(file.filename):
			filename = secure_filename(file.filename)
			file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
			return redirect(url_for('upload_file', filename=filename))
	return render_template('index.html')

@app.route('/uploads/<filename>')
def uploaded_file(filename):
	return send_form_directory(app.config['UPLOAD_FOLDER'])

if __name__ == '__main__':
	port = int(os.environ.get('PORT', 5050))
	app.run(host='0.0.0.0', port=port, debug=True, use_reloader=True)