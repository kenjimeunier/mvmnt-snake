import requests
from flask import Flask, jsonify

app = Flask(__name__)

GITHUB_USER = "kenjimeunier"
GITHUB_REPO = "mvmnt-snake"
GITHUB_FOLDER = "images"

@app.route('/api/info')
def info():
    try:
        url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/contents/{GITHUB_FOLDER}"
        response = requests.get(url)
        
        if response.status_code != 200:
            return jsonify({
                "status": "error",
                "message": f"GitHub API returned {response.status_code}",
                "total": 0
            })
        
        files = response.json()
        image_files = [f for f in files if f['name'].lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp'))]
        
        return jsonify({
            "status": "success",
            "total": len(image_files),
            "images": [{"name": f['name'], "url": f['download_url']} for f in image_files]
        })
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
            "total": 0
        })

if __name__ == '__main__':
    app.run(debug=True)
