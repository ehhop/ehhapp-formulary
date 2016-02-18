from __future__ import print_function
import os
from flask import Flask, render_template, request, redirect, url_for, send_from_directory
from werkzeug import secure_filename
from app.rxparse import update_rx

UPLOAD_FOLDER = 'app/input'
OUTPUT_FOLDER = 'app/output'
ALLOWED_EXTENSIONS = set(['txt','xls','xlsx','csv','tsv','md', 'markdown'])

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 100*1024*1024 #set max upload file size to 100mb

def allowed_file(filename):
	return '.' in filename and \
		filename.rsplit('.',1)[1] in ALLOWED_EXTENSIONS

@app.route('/')
def index():
	error_prompt = ''
	return render_template('index.html', error_prompt=error_prompt)

@app.route('/selection', methods=['POST'])
def process_file():
	uploaded_files = request.files.getlist("file")
	upload_filename_list = []
	for file in uploaded_files:
		if file.filename == '':
			error_prompt = 'Please check that all files have been selected for upload'
			return render_template('index.html', error_prompt=error_prompt)
		if file and allowed_file(file.filename):
			filename = secure_filename(file.filename)
			file.save(os.path.join(app.config['UPLOAD_FOLDER'],filename))
			upload_filename_list.append(file.filename) # old: currenly not tracking upload files
	formulary = str(upload_filename_list[0])
	invoice = str(upload_filename_list[1])
	pricetable = str(upload_filename_list[2])

	pricetable_unmatched_meds, output_filename_list, screen_output, fuzzymatches = update_rx(formulary, invoice, pricetable)

	app.logger.debug(screen_output)
	
	return render_template('selection.html', output_filename_list=output_filename_list, screen_output=screen_output, pricetable_unmatched_meds=pricetable_unmatched_meds, fuzzymatches=fuzzymatches)

@app.route('/output/<filename>')
def output_file(filename):
	return send_from_directory(app.config['OUTPUT_FOLDER'],filename)

@app.route('/result', methods=['GET','POST'])
def result():
	app.logger.debug("JSON received...")
	app.logger.debug(request.json)
	request_json = request.get_json()

	return request_json_data
	'''
	output_filename_list = []
	pricetable_unmatched_meds = []
	print('stored!')
	return render_template('output.html', output_filename_list=output_filename_list, screen_output=screen_output, pricetable_unmatched_meds=pricetable_unmatched_meds)
	'''
if __name__ == '__main__':
	port = int(os.environ.get('PORT', 5050))
	app.run(
		host='0.0.0.0',
		port=port,
		debug=True,
		use_reloader=True
	)