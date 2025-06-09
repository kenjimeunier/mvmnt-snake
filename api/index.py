from flask import Flask, render_template_string, jsonify, request, send_from_directory
import os
import glob
import base64
import cv2
import numpy as np
import time
from threading import Lock

app = Flask(__name__)

# Configuration
IMAGES_FOLDER = os.path.join(os.path.dirname(__file__), '..', 'images')
AUTO_SPEED = 25.0 / 30.0
MANUAL_SPEED_FACTOR = 15.0
MOUSE_TIMEOUT = 3.0

# Variables globales
current_frame = 0.0
total_frames = 0
images_cache = []
last_mouse_time = time.time()
manual_control = False
cache_lock = Lock()

# Template HTML intégré
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
        }
        .loading { 
            color: #ff0; 
            font-size: 1.5em; 
            text-align: center;
            margin-top: 50px;
        }
    </style>
</head>
<body>
    <div id="container">
        <div id="title">-m-v-m-n-t- Snake - Web Player</div>
        <canvas id="canvas"></canvas>
        <div id="controls">
            <div id="mode">Mode: AUTO (25fps)</div>
            <div id="speed-bar">
                <div id="dead-zone"></div>
                <div id="speed-indicator"></div>
            </div>
            <div id="info">Chargement...</div>
        </div>
    </div>

    <script>
        class SnakePlayer {
            constructor() {
                this.canvas = document.getElementById('canvas');
                this.ctx = this.canvas.getContext('2d');
                this.currentFrame = 0;
                this.totalFrames = 0;
                this.speed = 0.833; // 25fps
                this.manualControl = false;
                this.mouseX = 0;
                this.lastMouseMove = Date.now();
                this.animationId = null;
                
                this.setupUI();
                this.init();
            }
            
            setupUI() {
                const speedBar = document.getElementById('speed-bar');
                const deadZone = document.getElementById('dead-zone');
                const indicator = document.getElementById('speed-indicator');
                
                // Zone morte au centre (15% de chaque côté)
                deadZone.style.left = '35%';
                deadZone.style.width = '30%';
                
                // Événements souris
                speedBar.addEventListener('mousemove', (e) => {
                    const rect = speedBar.getBoundingClientRect();
                    this.mouseX = (e.clientX - rect.left) / rect.width;
                    this.manualControl = true;
                    this.lastMouseMove = Date.now();
                    this.updateSpeedIndicator();
                });
                
                speedBar.addEventListener('mouseleave', () => {
                    // Ne pas désactiver le contrôle manuel immédiatement
                });
                
                // Vérification du timeout toutes les 100ms
                setInterval(() => {
                    if (this.manualControl && Date.now() - this.lastMouseMove > 3000) {
                        this.manualControl = false;
                        this.updateUI();
                    }
                }, 100);
                
                // Contrôles clavier
                document.addEventListener('keydown', (e) => {
                    switch(e.code) {
                        case 'Space':
                            e.preventDefault();
                            this.manualControl = true;
                            this.speed = 0;
                            this.lastMouseMove = Date.now();
                            break;
                        case 'KeyA':
                            this.manualControl = false;
                            break;
                        case 'KeyR':
                            this.currentFrame = 0;
                            break;
                    }
                });
            }
            
            updateSpeedIndicator() {
                const indicator = document.getElementById('speed-indicator');
                const pos = this.mouseX * 100;
                indicator.style.left = Math.max(0, Math.min(390, pos * 4)) + 'px';
            }
            
            async init() {
                try {
                    const response = await fetch('/api/info');
                    const data = await response.json();
                    this.totalFrames = data.total;
                    
                    if (this.totalFrames > 0) {
                        this.startAnimation();
                    } else {
                        document.getElementById('info').textContent = 'Aucune image trouvée';
                    }
                } catch (error) {
                    console.error('Erreur:', error);
                    document.getElementById('info').textContent = 'Erreur de chargement';
                }
            }
            
            getSpeedFromMouse() {
                if (!this.manualControl) return 0.833; // 25fps
                
                const normalized = (this.mouseX * 2) - 1; // [-1, 1]
                const deadZone = 0.15;
                
                if (Math.abs(normalized) < deadZone) return 0;
                
                const sign = normalized > 0 ? 1 : -1;
                const remapped = (Math.abs(normalized) - deadZone) / (1 - deadZone);
                
                return sign * remapped * 5; // Max 5x speed
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
                info.textContent = `Frame ${Math.floor(this.currentFrame)}/${this.totalFrames} - ${fps.toFixed(0)}fps - ${progress}%`;
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
                    
                    this.animationId = requestAnimationFrame(animate);
                };
                
                animate();
            }
        }
        
        // Démarrer l'application
        window.addEventListener('DOMContentLoaded', () => {
            new SnakePlayer();
        });
    </script>
</body>
</html>
'''

def load_images():
    """Charge toutes les images au démarrage"""
    global images_cache, total_frames
    
    with cache_lock:
        if images_cache:  # Déjà chargé
            return
            
        print("Chargement des images...")
        exts = ("*.dpx", "*.tif", "*.tiff", "*.png", "*.jpg", "*.jpeg")
        files = []
        
        for ext in exts:
            files.extend(glob.glob(os.path.join(IMAGES_FOLDER, ext)))
        
        files = sorted(files)
        total_frames = len(files)
        
        if total_frames == 0:
            print(f"Aucune image trouvée dans {IMAGES_FOLDER}")
            return
            
        print(f"Chargement de {total_frames} images...")
        
        for i, file_path in enumerate(files):
            if i % 50 == 0:
                print(f"Chargement... {i}/{total_frames}")
            
            try:
                img = cv2.imread(file_path)
                if img is not None:
                    images_cache.append(img)
                else:
                    print(f"Erreur lecture: {file_path}")
            except Exception as e:
                print(f"Erreur {file_path}: {e}")
        
        print(f"✅ {len(images_cache)} images chargées")

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/info')
def get_info():
    load_images()
    return jsonify({
        'total': len(images_cache),
        'status': 'ready' if images_cache else 'no_images'
    })

@app.route('/api/frame/<int:index>')
def get_frame(index):
    global last_mouse_time, manual_control
    
    load_images()
    
    if not images_cache or index < 0 or index >= len(images_cache):
        return jsonify({'success': False, 'error': 'Index invalide'})
    
    try:
        img = images_cache[index]
        
        # Redimensionner si trop grand
        h, w = img.shape[:2]
        if w > 1200:
            ratio = 1200 / w
            new_w, new_h = int(w * ratio), int(h * ratio)
            img = cv2.resize(img, (new_w, new_h))
        
        # Encoder en JPEG
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 85]
        _, buffer = cv2.imencode('.jpg', img, encode_param)
        img_base64 = base64.b64encode(buffer).decode('utf-8')
        
        return jsonify({
            'success': True,
            'image': f"data:image/jpeg;base64,{img_base64}",
            'index': index,
            'total': len(images_cache)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# Précharger les images au démarrage
@app.before_first_request
def startup():
    load_images()

if __name__ == '__main__':
    app.run(debug=True)
