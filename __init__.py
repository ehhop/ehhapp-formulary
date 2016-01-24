from __future__ import print_function
import os
from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def homepage():
    return render_template('index.html')

if __name__ == '__main__':
	port = int(os.environ.get('PORT', 5050))
	app.run(host='0.0.0.0', port=port, debug=True, use_reloader=True)