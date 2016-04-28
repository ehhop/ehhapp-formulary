from __future__ import print_function
import os, os.path, json, datetime
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, make_response
from werkzeug import secure_filename
from app.rxparse import process_pricetable, process_formulary, process_usermatches

UPLOAD_FOLDER = 'app/input'
PERSISTENT_FOLDER = 'app/persistent'
BACKUP_FOLDER = 'app/markdown-backup'
OUTPUT_FOLDER = 'app/output'
ALLOWED_EXTENSIONS = set(['txt','xls','xlsx','csv','tsv','md', 'markdown'])
PERSISTENT_PRICETABLE_FILENAME = 'persistent-pricetable.tsv'

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PERSISTENT_FOLDER'] = PERSISTENT_FOLDER
app.config['BACKUP_FOLDER'] = BACKUP_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 100*1024*1024 # Set max upload file size to 100mb

def json_encode_set(obj):
    if isinstance(obj, set):
        return list(obj)
    raise TypeError

def allowed_file(filename):
	return '.' in filename and \
		filename.rsplit('.',1)[1] in ALLOWED_EXTENSIONS

@app.route('/')
def index():
	error_prompt = '' # Create filler for error prompt div
	return render_template('index.html', error_prompt=error_prompt)

@app.route('/selection', methods=['POST'])
def process_file():
	# Check for missing files and save uploaded file paths
	uploaded_files = request.files.getlist("file")
	upload_filepath_list = []

	for file in uploaded_files:

		# If file is missing, return error and remain on start page
		if file.filename == '':  
			error_prompt = 'Please check that all files have been selected for upload'
			return render_template('index.html', error_prompt=error_prompt)

		# Save files and create list of file paths
		if file and allowed_file(file.filename):

			# Save files in upload folder
			filename = secure_filename(file.filename)
			file.save(os.path.join(app.config['UPLOAD_FOLDER'],filename))
			upload_filepath_list.append(os.path.join(app.config['UPLOAD_FOLDER'],filename))

			# Also save additional backup of the markdown file with a datetime in filename
			if filename.split('.')[-1] == 'md' or filename.split('.')[-1] == 'markdown':
				datetime_string = datetime.datetime.now().strftime("%Y.%m.%d") # Override previous backups for currrent day
				backup_directory = app.config['BACKUP_FOLDER']
				num_files = len([f for f in os.listdir(backup_directory) if os.path.isfile(os.path.join(backup_directory,f))])
				filename_datetime = datetime_string+'_backup_'+filename
				file.save(os.path.join(backup_directory,filename_datetime))

				# Only keep 15 most recent backups
				num_files = len([f for f in os.listdir(backup_directory) if os.path.isfile(os.path.join(backup_directory,f))])
				if num_files > 15:
					first_file = os.listdir(path)[0]
					os.remove(os.path.join(backup_directory,first_file))

	formulary_md_path = str(upload_filepath_list[0])
	invoice_path = str(upload_filepath_list[1])
	pricetable_persist_path = os.path.join(app.config['PERSISTENT_FOLDER'],PERSISTENT_PRICETABLE_FILENAME)

	# Run update function for pricetable and formulary and capture fuzzy matches
	screen_output, output_filename_list, pricetable_output_path = process_pricetable(invoice_path, pricetable_persist_path, verbose_debug=False)
	
	pricetable_unmatched_meds, output_filename_list, screen_output, fuzzymatches = process_formulary(pricetable_persist_path, formulary_md_path, output_filename_list, screen_output)

	app.logger.debug(screen_output) #debugging
	
	# Store output files list, screen output, and unmatched medications as cookies
	# Render selection.html page
	resp = make_response(render_template('selection.html', output_filename_list=output_filename_list, screen_output=screen_output, pricetable_unmatched_meds=pricetable_unmatched_meds, fuzzymatches=fuzzymatches))

	json_output_filename_list = json.dumps(output_filename_list)
	json_pricetable_unmatched_meds = json.dumps(pricetable_unmatched_meds, default=json_encode_set)
	json_screen_output = json.dumps(screen_output)

	resp.set_cookie('formulary_md_path', formulary_md_path)
	resp.set_cookie('output_filename_list', json_output_filename_list)
	resp.set_cookie('screen_output', json_screen_output)
	resp.set_cookie('pricetable_unmatched_meds', json_pricetable_unmatched_meds)
	resp.set_cookie('pricetable_persist_path', pricetable_persist_path)
	resp.set_cookie('pricetable_output_path', pricetable_output_path)
	return resp

@app.route('/output/<filename>')
def output_file(filename):
	return send_from_directory(app.config['OUTPUT_FOLDER'],filename)

@app.route('/result', methods=['POST'])
def result():
	json_output_filename_list = request.cookies.get('output_filename_list')
	json_screen_output = request.cookies.get('screen_output')
	json_pricetable_unmatched_meds = request.cookies.get('pricetable_unmatched_meds')
	formulary_md_path = request.cookies.get('formulary_md_path')
	pricetable_persist_path = request.cookies.get('pricetable_persist_path')
	pricetable_output_path = request.cookies.get('pricetable_output_path')
	
	output_filename_list = json.loads(json_output_filename_list)
	pricetable_unmatched_meds_list = json.loads(json_pricetable_unmatched_meds)
	screen_output = json.loads(json_screen_output)

	pricetable_unmatched_meds = set()
	for entry in pricetable_unmatched_meds_list:
		pricetable_unmatched_meds.add(entry)
	
	usermatches = request.form.getlist('usermatches')
	app.logger.debug(usermatches) #debugging
	
	pricetable_unmatched_meds, screen_output = process_usermatches(usermatches, formulary_md_path, pricetable_unmatched_meds, pricetable_persist_path, pricetable_output_path, output_filename_list, screen_output)

	# Convert screen output from array to strings
	screen_output_strings = []
	for line in screen_output:
		screen_output_strings.append(line[0] + ': ' + str(line[1]))
	screen_output = screen_output_strings
	
	return render_template('result.html', output_filename_list=output_filename_list, screen_output=screen_output, pricetable_unmatched_meds=pricetable_unmatched_meds)

if __name__ == '__main__':
	port = int(os.environ.get('PORT', 5050))
	app.run(
		host='0.0.0.0',
		port=port,
		debug=True,
		use_reloader=True
	)
