from .index import get_frame
import re

def handler(request):
    path = request.url
    match = re.search(r'/api/frame/(\d+)', path)
    if match:
        index = int(match.group(1))
        return get_frame(index)
    return {'error': 'Invalid frame index'}, 400
