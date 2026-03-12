from flask import Flask, send_from_directory, jsonify
import os

app = Flask(__name__, static_folder="public", static_url_path="")

# API route
@app.route("/api/")
@app.route("/api/<path:path>")
def api(path=None):
    return jsonify({"message": "Hello API"})

# Serve static files
@app.route("/")
def index():
    return send_from_directory("public", "index.html")

@app.route("/<path:path>")
def static_files(path):
    public_dir = os.path.join(os.getcwd(), "public")
    return send_from_directory(public_dir, path)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)