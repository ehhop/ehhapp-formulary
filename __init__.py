from __future__ import print_function
import os, json
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, make_response
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
	error_prompt = '' #create filler for error prompt div
	return render_template('index.html', error_prompt=error_prompt)

@app.route('/selection', methods=['POST'])
def process_file():

	#check for missing files and save uploaded file paths
	uploaded_files = request.files.getlist("file")
	upload_filename_list = []

	for file in uploaded_files:

		if file.filename == '':  #return error if there are missing files
			error_prompt = 'Please check that all files have been selected for upload'
			return render_template('index.html', error_prompt=error_prompt)

		if file and allowed_file(file.filename):
			filename = secure_filename(file.filename)
			file.save(os.path.join(app.config['UPLOAD_FOLDER'],filename))
			upload_filename_list.append(file.filename) # old: currenly not tracking upload files

	formulary = str(upload_filename_list[0])
	invoice = str(upload_filename_list[1])
	pricetable = str(upload_filename_list[2])

	#run update function for pricetable and formulary and capture fuzzy matches
	pricetable_unmatched_meds, output_filename_list, screen_output, fuzzymatches = update_rx(formulary, invoice, pricetable)

	#store output files list, screen output, and unmatched medications as cookies
	#render selection.html page
	resp = make_response(render_template('selection.html', output_filename_list=output_filename_list, screen_output=screen_output, pricetable_unmatched_meds=pricetable_unmatched_meds, fuzzymatches=fuzzymatches))

	json_output_filename_list = json.dumps(output_filename_list)
	json_screen_output = json.dumps(screen_output)
	json_pricetable_unmatched_meds = json.dumps(pricetable_unmatched_meds)

	resp.set_cookie('output_filename_list', json_output_filename_list)
	resp.set_cookie('screen_output', json_screen_output)
	resp.set_cookie('pricetable_unmatched_meds', json_pricetable_unmatched_meds)

	return resp

@app.route('/output/<filename>')
def output_file(filename):
	return send_from_directory(app.config['OUTPUT_FOLDER'],filename)

@app.route('/result', methods=['POST'])
def result():
	json_output_filename_list = request.cookies.get('output_filename_list')
	json_screen_output = request.cookies.get('screen_output')
	json_pricetable_unmatched_meds = request.cookies.get('pricetable_unmatched_meds')

	output_filename_list = json.loads(json_output_filename_list)
	screen_output = json.loads(json_screen_output)
	pricetable_unmatched_meds = json.loads(json_pricetable_unmatched_meds)

	'''
	app.logger.debug("Checking cookies...") #debugging
	app.logger.debug(output_filename_list) #debugging
	app.logger.debug(screen_output) #debugging
	app.logger.debug(pricetable_unmatched_meds) #debugging
	'''

	user_matches = request.form.getlist('usermatches')
	app.logger.debug(matches) #debugging

	#function for adding user matches
	#function for updating summary information
	#function for processing file outputs

	return render_template('result.html')
	'''
	return render_template('result.html', output_filename_list=output_filename_list, screen_output=screen_output, pricetable_unmatched_meds=pricetable_unmatched_meds)
	'''

if __name__ == '__main__':
	port = int(os.environ.get('PORT', 5050))
	app.run(
		host='0.0.0.0',
		port=port,
		debug=True,
		use_reloader=True
	)