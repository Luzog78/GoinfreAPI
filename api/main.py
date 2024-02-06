import os
import json
from flask import Flask, request, jsonify


def load_data(folder: str):
	for root, dirs, files in os.walk(folder):
		for filename in files:
			if filename.endswith(".json"):
				with open(os.path.join(root, filename)) as f:
					try:
						content = json.load(f)
					except:
						content = {}
					data_name = os.path.join(root, filename) \
						.removeprefix(folder).removeprefix("/")[:-5]
					data[data_name] = content


files_to_delete = []
data = {}
load_data("data")


def get_file_tree():
	tree = {}
	for filename in data.keys():
		branch = tree
		for p in filename.split("/")[:-1]:
			if p not in branch:
				branch[p] = {}
			branch = branch[p]
		if filename.split("/")[-1] not in branch:
			size = os.path.getsize(f"data/{filename}.json")
			branch[filename.split("/")[-1] + ".json"] = size
	return tree


def get_flat_tree():
	default_tree = get_file_tree()
	tree = {}

	def flatten(branch: dict, path: str = ".") -> int:
		file_count = 0
		for k, v in branch.items():
			if isinstance(v, dict):
				tree["/".join([path, k])] = flatten(v, "/".join([path, k]))
			else:
				tree["/".join([path, k])] = None
			file_count += 1
		return file_count
	
	flatten(default_tree)
	return {k[2:]: v for k, v in tree.items()}


def parse_path(path: str):
	if path == "":
		return []
	p = []
	start_idx = 0
	path_cpy = path[:] + "."
	for i in range(len(path_cpy)):
		if path_cpy[i] == ".":
			elem = path_cpy[start_idx:i]
			start_idx = i + 1
			if elem == "":
				return None
			elif elem.isdigit():
				elem = int(elem)
			elif elem[0] == "'" and elem[-1] == "'" \
				or elem[0] == "\"" and elem[-1] == "\"":
				elem = elem[1:-1]
			p.append(elem)
	return p


def parse_key(key: str):
	key = key.strip()
	if key[0] == "'" and key[-1] == "'" \
		or key[0] == "\"" and key[-1] == "\"":
		return key[1:-1]
	return key


def parse_value(value: str) -> str | int | float | bool | list | dict:
	print(f"parse_value({value})")
	value = value.strip()
	if value == "":
		raise ValueError("Empty value")
	if value.isdigit():
		return int(value)
	elif (value.count(".") == 1 and value.replace(".", "").isdigit()) \
		or (value[-1] == "f" and value[:-1].isdigit()) \
		or (value[-1] == "d" and value[:-1].isdigit()):
		return float(value.replace(",", ".").replace("f", "").replace("d", ""))
	elif value.lower() == "true":
		return True
	elif value.lower() == "false":
		return False
	elif value.lower() == "null" or value.lower() == "none":
		return None
	elif value[0] == "'" and value[-1] == "'" \
		or value[0] == "\"" and value[-1] == "\"":
		return value[1:-1]
	elif value[0] == "[" and value[-1] == "]":
		return [parse_value(v) for v in value[1:-1].split(",")]
	elif value[0] == "{" and value[-1] == "}":
		return {parse_key(v.split(":")[0]): parse_value(v.split(":")[1].strip()) for v in value[1:-1].split(",")}
	return value


app = Flask(__name__)


@app.route("/", methods=["GET"])
def route_index():
	return '''
		<h1>API</h1>
		<p>API for managing JSON files</p>
		<p>Endpoints:</p>
		<ul>
			<li><a href="/reload_all">/reload_all</a></li>
			<li><a href="/save_all">/save_all</a></li>
			<li><a href="/file/load?file=filename">/file/load?file=filename</a></li>
			<li><a href="/file/save?file=filename">/file/save?file=filename</a></li>
			<li><a href="/data/get?file=filename&path=path">/data/get?file=filename&path=path</a></li>
			<li><a href="/data/set?file=filename&path=path&value=value">/data/set?file=filename&path=path&value=value</a></li>
			<li><a href="/data/unset?file=filename&path=path">/data/unset?file=filename&path=path</a></li>
			<li><a href="/data/append?file=filename&path=path&value=value">/data/append?file=filename&path=path&value=value</a></li>
			<li><a href="/data/replace?file=filename&path=path&value=value">/data/replace?file=filename&path=path&value=value</a></li>
			<li><a href="/file/create?file=filename">/file/create?file=filename</a></li>
			<li><a href="/file/delete?file=filename">/file/delete?file=filename</a></li>
			<li><a href="/file/tree">/file/tree</a></li>
			<li><a href="/file/flat_tree">/file/flat_tree</a></li>
			<li><a href="/data/all">/data/all</a></li>
		</ul>
	'''


@app.route("/reload_all", methods=["GET"])
def route_global_reload():
	data.clear()
	load_data("data")
	return jsonify({"status": 0})


@app.route("/save_all", methods=["GET"])
def route_global_save():
	deleted = []
	saved = []
	for filename in files_to_delete:
		try:
			os.remove(f"data/{filename}.json")
			deleted.append(filename)
		except:
			pass
	for filename in data:
		try:
			with open(f"data/{filename}.json", "w" if os.path.exists(f"data/{filename}.json") else "x") as f:
				json.dump(data[filename], f, indent=2)
			saved.append(filename)
		except:
			pass
	try:
		for root, dirs, files in os.walk("data"):
			if not files and not dirs:
				os.rmdir(root)
	except:
		pass
	return jsonify({"status": 0, "deleted": deleted, "saved": saved})


@app.route("/file/load", methods=["GET"])
def route_load():
	filename = request.args.get("file")
	if filename is None:
		return jsonify({"status": 1, "message": "No file specified"})
	if filename not in data:
		return jsonify({"status": 1, "message": "File not found"})
	with open(f"data/{filename}.json") as f:
		try:
			content = json.load(f)
		except:
			content = {}
		data[filename] = content
	return jsonify({"status": 0, "file": filename})


@app.route("/file/save", methods=["GET"])
def route_save():
	filename = request.args.get("file")
	if filename is None:
		return jsonify({"status": 1, "message": "No file specified"})
	if filename in files_to_delete:
		try:
			os.remove(f"data/{filename}.json")
		except:
			return jsonify({"status": 1, "message": "Failed to delete file"})
		files_to_delete.remove(filename)
		try:
			for root, dirs, files in os.walk("data"):
				if not files and not dirs:
					os.rmdir(root)
		except:
			pass
		return jsonify({"status": 0, "file": filename})
	if filename not in data:
		return jsonify({"status": 1, "message": "File not found"})
	with open(f"data/{filename}.json", "w" if os.path.exists(f"data/{filename}.json") else "x") as f:
		json.dump(data[filename], f, indent=2)
	return jsonify({"status": 0, "file": filename})


@app.route("/data/get", methods=["GET"])
def route_get():
	filename = request.args.get("file")
	if filename is None:
		return jsonify({"status": 1, "message": "No file specified"})
	if filename not in data:
		return jsonify({"status": 1, "message": "File not found"})

	path = request.args.get("path")
	if path is None:
		return jsonify({"status": 1, "message": "No path specified", "file": filename})

	path = parse_path(path)
	if path is None:
		return jsonify({"status": 1, "message": "Invalid path", "file": filename})

	obj = data[filename]
	for p in path:
		try:
			obj = obj[p]
		except:
			return jsonify({"status": 1, "message": "Path not found", "file": filename, "path": path})

	return jsonify({"status": 0, "file": filename, "path": path, "value": obj})


@app.route("/data/set", methods=["GET"])
def route_set():
	filename = request.args.get("file")
	if filename is None:
		return jsonify({"status": 1, "message": "No file specified"})
	if filename not in data:
		return jsonify({"status": 1, "message": "File not found"})

	path = request.args.get("path")
	if path is None:
		return jsonify({"status": 1, "message": "No path specified", "file": filename})

	path = parse_path(path)
	if path is None:
		return jsonify({"status": 1, "message": "Invalid path", "file": filename})

	value = request.args.get("value")
	if value is None:
		return jsonify({"status": 1, "message": "No value specified", "file": filename, "path": path})

	try:
		value = parse_value(value)
	except:
		return jsonify({"status": 1, "message": "Invalid value", "file": filename, "path": path})

	try:
		obj = data[filename]
		pathh = list(path[:-1])
		for i, p in enumerate(pathh):
			if isinstance(obj, list):
				if p == len(obj):
					obj.append([] if isinstance(pathh[i+1], int) else {})
				elif p > len(obj):
					raise IndexError(f"Index out of range: {p} > {len(obj)}")
			elif isinstance(p, int):
				raise ValueError(f"Index given when string key expected ({p})")
			if isinstance(obj, dict) and p not in obj:
				obj[p] = [] if isinstance(pathh[i+1], int) else {}
			obj = obj[p]

		if path[-1] not in obj:
			if isinstance(obj, list):
				if path[-1] == len(obj):
					obj.append(None)
				elif path[-1] > len(obj):
					raise IndexError(f"Index out of range: {path[-1]} > {len(obj)}")
			elif isinstance(path[-1], int):
				raise ValueError(f"Index given when string key expected ({path[-1]})")
			if isinstance(obj, dict) and path[-1] not in obj:
				obj[p] = None
	except Exception as e:
		return jsonify({"status": 1, "message": "Access error", "info": str(e), "file": filename, "path": path})

	if (isinstance(obj[path[-1]], list) and not isinstance(value, list)) \
		or (isinstance(obj[path[-1]], dict) and not isinstance(value, dict)):
		return jsonify({"status": 1, "message": "Path already exists", "file": filename, "path": path})

	try:
		obj[path[-1]] = value
	except Exception as e:
		return jsonify({"status": 1, "message": "Set failed", "info": str(e), "file": filename, "path": path, "value": value})

	return jsonify({"status": 0, "file": filename, "path": path, "value": value})


@app.route("/data/unset", methods=["GET"])
def route_unset():
	filename = request.args.get("file")
	if filename is None:
		return jsonify({"status": 1, "message": "No file specified"})
	if filename not in data:
		return jsonify({"status": 1, "message": "File not found"})

	path = request.args.get("path")
	if path is None:
		return jsonify({"status": 1, "message": "No path specified", "file": filename})

	path = parse_path(path)
	if path is None:
		return jsonify({"status": 1, "message": "Invalid path", "file": filename})

	try:
		obj = data[filename]
		for p in path[:-1]:
			obj = obj[p]
		obj[path[-1]]
	except Exception as e:
		return jsonify({"status": 1, "message": "Access error", "info": str(e), "file": filename, "path": path})

	try:
		del obj[path[-1]]
	except Exception as e:
		return jsonify({"status": 1, "message": "Unset failed", "info": str(e), "file": filename, "path": path})

	return jsonify({"status": 0, "file": filename, "path": path})


@app.route("/data/append", methods=["GET"])
def route_append():
	filename = request.args.get("file")
	if filename is None:
		return jsonify({"status": 1, "message": "No file specified"})
	if filename not in data:
		return jsonify({"status": 1, "message": "File not found"})

	path = request.args.get("path")
	if path is None:
		return jsonify({"status": 1, "message": "No path specified", "file": filename})

	path = parse_path(path)
	if path is None:
		return jsonify({"status": 1, "message": "Invalid path", "file": filename})

	value = request.args.get("value")
	if value is None:
		return jsonify({"status": 1, "message": "No value specified", "file": filename, "path": path})

	try:
		value = parse_value(value)
	except:
		return jsonify({"status": 1, "message": "Invalid value", "file": filename, "path": path})

	try:
		obj = data[filename]
		for p in path:
			obj = obj[p]
	except Exception as e:
		return jsonify({"status": 1, "message": "Access error", "info": str(e), "file": filename, "path": path})

	if not isinstance(obj, list):
		return jsonify({"status": 1, "message": "Path is not a list", "file": filename, "path": path})
	
	try:
		obj.append(value)
	except Exception as e:
		return jsonify({"status": 1, "message": "Append failed", "info": str(e), "file": filename, "path": path, "value": value})
	
	return jsonify({"status": 0, "file": filename, "path": path, "value": value})


@app.route("/data/replace", methods=["GET"])
def route_replace():
	filename = request.args.get("file")
	if filename is None:
		return jsonify({"status": 1, "message": "No file specified"})
	if filename not in data:
		return jsonify({"status": 1, "message": "File not found"})

	path = request.args.get("path")
	if path is None:
		return jsonify({"status": 1, "message": "No path specified", "file": filename})

	path = parse_path(path)
	if path is None:
		return jsonify({"status": 1, "message": "Invalid path", "file": filename})

	value = request.args.get("value")
	if value is None:
		return jsonify({"status": 1, "message": "No value specified", "file": filename, "path": path})

	try:
		value = parse_value(value)
	except:
		return jsonify({"status": 1, "message": "Invalid value", "file": filename, "path": path})

	try:
		obj = data[filename]
		for p in path[:-1]:
			obj = obj[p]
		obj[path[-1]]
	except Exception as e:
		return jsonify({"status": 1, "message": "Access error", "info": str(e), "file": filename, "path": path})

	try:
		obj[path[-1]] = value
	except Exception as e:
		return jsonify({"status": 1, "message": "Replace failed", "info": str(e), "file": filename, "path": path, "value": value})

	return jsonify({"status": 0, "file": filename, "path": path, "value": value})


@app.route("/file/create", methods=["GET"])
def route_file_create():
	filename = request.args.get("file")
	if filename is None:
		return jsonify({"status": 1, "message": "No file specified"})
	if filename in data:
		return jsonify({"status": 1, "message": "File already exists"})
	
	if ".." in filename:
		return jsonify({"status": 1, "message": "Invalid filename"})

	data[filename] = {}
	return jsonify({"status": 0, "file": filename})


@app.route("/file/delete", methods=["GET"])
def route_file_delete():
	filename = request.args.get("file")
	if filename is None:
		return jsonify({"status": 1, "message": "No file specified"})
	if filename not in data:
		return jsonify({"status": 1, "message": "File not found"})

	del data[filename]
	files_to_delete.append(filename)
	return jsonify({"status": 0, "file": filename})


@app.route("/file/tree", methods=["GET"])
def route_file_tree():
	return jsonify({"status": 0, "tree": get_file_tree()})


@app.route("/file/flat_tree", methods=["GET"])
def route_flat_tree():
	return jsonify({"status": 0, "flat_tree": get_flat_tree()})


@app.route("/data/all", methods=["GET"])
def route_data_all():
	return jsonify({"status": 0, "data": data})


app.run(debug=True, host="0.0.0.0", port=5001)
