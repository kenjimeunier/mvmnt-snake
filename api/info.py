from .index import app, get_info

def handler(request):
    with app.test_request_context():
        return get_info()
