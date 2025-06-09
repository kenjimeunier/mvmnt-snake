from flask import Flask, render_template_string, jsonify
import requests
import base64
from PIL import Image
import io
import json

app = Flask(__name__)

# Configuration GitHub
GITHUB_FOLDER = ""  # Au lieu de "images"
GITHUB_REPO = "mvmnt-snake"
GITHUB_FOLDER = "images"  # Changez en "" si les images sont à la racine
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/contents/{GITHUB_FOLDER}"

# Cache pour éviter trop d'appels API
image_cache = {}
files_list_cache = None

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>-m-v-m-n-t- Snake Player</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            background: #000; 
            color: #0f0; 
            font-family: 'Courier New', monospace;
            overflow: hidden;
        }
        #container { 
            width: 100vw; 
            height: 100vh; 
            display: flex; 
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }
        #title { 
            font-size: 2em; 
            margin-bottom: 20px; 
            text-align: center;
            text-shadow: 0 0 10px #0f0;
        }
        #canvas { 
            border: 2px solid #0f0; 
            max-width: 90vw; 
            max-height: 70vh;
            cursor: crosshair;
        }
        #controls { 
            margin-top: 20px; 
            text-align: center;
            font-size: 1.2em;
        }
        #mode { color: #ff0; margin-bottom: 10px; }
        #info { color: #0ff; }
        #speed-bar { 
            width: 400px; 
            height: 20px; 
            background: #333; 
            margin: 10px auto;
            position: relative;
            border: 1px solid #0f0;
        }
        #speed-indicator { 
            width: 10px; 
            height: 18px; 
            background: #ff0; 
            position: absolute;
            top: 1px;
            transition: left 0.1s;
        }
        #dead-zone { 
            position: absolute; 
            background: rgba(255,0,0,0.3); 
            height: 18px; 
            top: 1px;
            left: 35%; 
            width: 30%;
        }
        .loading { color: #ff0; }
    </style>
</head>
<body>
    <div id="container">
        <div id="title">-m-v-m-n-t- Snake Player</div>
        <canvas id="canvas"></canvas>
        <div id="controls">
            <div id="mode">Mode: AUTO (25fps)</div>
            <div id="speed-bar">
                <div id="dead-zone"></div>
                <div id="speed-indicator"></div>
            </div>
            <div id="info" class="loading">Chargement depuis GitHub...</div>
        </div>
    </div>

    <script>
        class SnakePlayer {
            constructor() {
                this.canvas = document.getElementById('canvas');
                this.ctx = this.canvas.getContext('2d');
                this.currentFrame = 0;
                this.totalFrames = 0;
                this.speed = 0.833;
                this.manualControl = false;
                this.mouseX = 0;
                this.lastMouseMove = Date.now();
                
                this.setupUI();
                this.init();
            }
            
            setupUI() {
                const speedBar = document.getElementById('speed-bar');
                
                speedBar.addEventListener('mousemove', (e) => {
                    const rect = speedBar.getBoundingClientRect();
                    this.mouseX = (e.clientX - rect.left) / rect.width;
                    this.manualControl = true;
                    this.lastMouseMove = Date.now();
                    this.updateSpeedIndicator();
                });
                
                setInterval(() => {
                    if (this.manualControl && Date.now() - this.lastMouseMove > 3000) {
                        this.manualControl = false;
                        this.updateUI();
                    }
                }, 100);
            }
            
            updateSpeedIndicator() {
                const indicator = document.getElementById('speed-indicator');
                const pos = this.mouseX * 100;
                indicator.style.left = Math.max(0, Math.min(390, pos * 4)) + 'px';
            }
            
            async init() {
                try {
                    document.getElementById('info').textContent = 'Connexion à GitHub...';
                    const response = await fetch('/api/info');
                    const data = await response.json();
                    this.totalFrames = data.total;
                    
                    if (this.totalFrames > 0) {
                        document.getElementById('info').textContent = `${this.totalFrames} images trouvées sur GitHub`;
                        this.startAnimation();
                    } else {
                        document.getElementById('info').textContent = 'Aucune image trouvée sur GitHub';
                    }
                } catch (error) {
                    console.error('Erreur:', error);
                    document.getElementById('info').textContent = 'Erreur de connexion GitHub';
                }
            }
            
            getSpeedFromMouse() {
                if (!this.manualControl) return 0.833;
                
                const normalized = (this.mouseX * 2) - 1;
                const deadZone = 0.15;
                
                if (Math.abs(normalized) < deadZone) return 0;
                
                const sign = normalized > 0 ? 1 : -1;
                const remapped = (Math.abs(normalized) - deadZone) / (1 - deadZone);
                
                return sign * remapped * 5;
            }
            
            async loadFrame(index) {
                try {
                    const response = await fetch(`/api/frame/${Math.floor(index)}`);
                    const data = await response.json();
                    
                    if (data.success) {
                        const img = new Image();
                        img.onload = () => {
                            this.canvas.width = Math.min(img.width, window.innerWidth * 0.9);
                            this.canvas.height = (this.canvas.width / img.width) * img.height;
                            this.ctx.drawImage(img, 0, 0, this.canvas.width, this.canvas.height);
                        };
                        img.src = data.image;
                    }
                } catch (error) {
                    console.error('Erreur frame:', error);
                }
            }
            
            updateUI() {
                const mode = document.getElementById('mode');
                const info = document.getElementById('info');
                
                const fps = Math.abs(this.speed * 30);
                const modeText = this.manualControl ? 'MANUEL' : 'AUTO';
                const timeRemaining = this.manualControl ? 
                    Math.max(0, 3 - (Date.now() - this.lastMouseMove) / 1000) : 0;
                
                mode.textContent = this.manualControl ? 
                    `Mode: ${modeText} (${fps.toFixed(0)}fps) - Auto dans ${timeRemaining.toFixed(1)}s` :
                    `Mode: ${modeText} (25fps)`;
                
                const progress = (this.currentFrame / this.totalFrames * 100).toFixed(1);
                info.textContent = `Frame ${Math.floor(this.currentFrame)}/${this.totalFrames} - ${fps.toFixed(0)}fps - ${progress}% - GitHub`;
            }
            
            startAnimation() {
                const animate = () => {
                    this.speed = this.getSpeedFromMouse();
                    this.currentFrame += this.speed;
                    
                    if (this.currentFrame >= this.totalFrames) {
                        this.currentFrame = 0;
                    } else if (this.currentFrame < 0) {
                        this.currentFrame = this.totalFrames - 1;
                    }
                    
                    this.loadFrame(this.currentFrame);
                    this.updateUI();
                    
                    requestAnimationFrame(animate);
                };
                
                animate();
            }
        }
        
        window.addEventListener('DOMContentLoaded', () => {
            new SnakePlayer();
        });
    </script>
</body>
</html>
'''

def get_github_files():
    """Récupère la liste des fichiers depuis GitHub"""
    global files_list_cache
    
    if files_list_cache is not None:
        return files_list_cache
    
    try:
        response = requests.get(GITHUB_API_URL, timeout=10)
        if response.status_code == 200:
            files_data = response.json()
            # Filtrer les images
            image_files = [
                f for f in files_data 
                if f['type'] == 'file' and 
                f['name'].lower().endswith(('.png', '.jpg', '.jpeg'))
            ]
            # Trier par nom
            image_files.sort(key=lambda x: x['name'])
            files_list_cache = image_files
            return image_files
        else:
            print(f"Erreur GitHub API: {response.status_code}")
            return []
    except Exception as e:
        print(f"Erreur lors de la récupération des fichiers: {e}")
        return []

def handler(request):
    with app.test_request_context(path=request.url, method=request.method):
        try:
            return app.full_dispatch_request()
        except Exception as e:
            return jsonify({'error': str(e)}), 500

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/info')
def get_info():
    try:
        files = get_github_files()
        return jsonify({
            'total': len(files),
            'status': 'ready' if files else 'no_images',
            'source': 'github'
        })
    except Exception as e:
        return jsonify({'total': 0, 'status': 'error', 'message': str(e)})

@app.route('/api/frame/<int:index>')
def get_frame(index):
    try:
        files = get_github_files()
        
        if not files or index < 0 or index >= len(files):
            return jsonify({'success': False, 'error': 'Index invalide'})
        
        file_info = files[index]
        
        # Vérifier le cache
        if file_info['name'] in image_cache:
            return jsonify({
                'success': True,
                'image': image_cache[file_info['name']],
                'index': index,
                'total': len(files),
                'cached': True
            })
        
        # Télécharger l'image depuis GitHub
        response = requests.get(file_info['download_url'], timeout=15)
        if response.status_code != 200:
            return jsonify({'success': False, 'error': 'Erreur téléchargement'})
        
        # Traiter l'image avec PIL
        img = Image.open(io.BytesIO(response.content))
        
        # Redimensionner si nécessaire
        if img.width > 1200:
            ratio = 1200 / img.width
            new_size = (int(img.width * ratio), int(img.height * ratio))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
        
        # Convertir en RGB si nécessaire
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Encoder en base64
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=85)
        img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        data_url = f"data:image/jpeg;base64,{img_base64}"
        
        # Mettre en cache (limiter la taille du cache)
        if len(image_cache) < 50:  # Limiter à 50 images en cache
            image_cache[file_info['name']] = data_url
        
        return jsonify({
            'success': True,
            'image': data_url,
            'index': index,
            'total
