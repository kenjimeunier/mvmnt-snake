from .index import app, get_frame
import re

def handler(request):
    # Extraire l'index de l'URL
    path = request.url
    match = re.search(r'/api/frame/(\d+)', path)
    if match:
        index = int(match.group(1))
        with app.test_request_context():
            return get_frame(index)
    return {'error': 'Invalid frame index'}, 400
