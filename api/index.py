import requests
from flask import Flask, jsonify

app = Flask(__name__)

GITHUB_USER = "kenjimeunier"
GITHUB_REPO = "mvmnt-snake"
GITHUB_FOLDER = "images"

@app.route('/api/info')
def info():
    try:
        # Test direct de l'URL GitHub
        url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/contents/{GITHUB_FOLDER}"
        response = requests.get(url)
        
        return jsonify({
            "status": "debug",
            "url": url,
            "status_code": response.status_code,
            "response": response.text[:500] if response.text else "No response"
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        })

if __name__ == '__main__':
    app.run(debug=True)
