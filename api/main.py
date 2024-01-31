import os
import json
from flask import Flask, request, jsonify


def load_data(folder: str):
	for root, dirs, files in os.walk(folder):
		for filename in files:
			if filename.endswith('.json'):
				with open(os.path.join(root, filename)) as f:
					data[filename[:-5]] = json.load(f)


data = {}
load_data('data')

app = Flask(__name__)

@app.route('/load', methods=['GET'])
def route_load():
	filename = request.args.get("file")
	if filename is None:
		return jsonify({"status": 1, "message": "No file specified"})
	if filename not in data:
		return jsonify({"status": 1, "message": "File not found"})
	with open(f"data/{filename}.json") as f:
		data[filename] = json.load(f)
	return jsonify({"status": 0})

@app.route('/save', methods=['GET'])
def route_save():
	filename = request.args.get("file")
	if filename is None:
		return jsonify({"status": 1, "message": "No file specified"})
	if filename not in data:
		return jsonify({"status": 1, "message": "File not found"})
	with open(f"data/{filename}.json", 'w') as f:
		json.dump(data[filename], f, indent=2)
	return jsonify({"status": 0})


app.run(debug=True, host='0.0.0.0', port=5001)
