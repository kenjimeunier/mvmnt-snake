from flask import Flask, render_template_string

app = Flask(__name__)

@app.route('/')
def index():
    return '''
    <h1>-m-v-m-n-t- Snake Player</h1>
    <p>Test version - Images loading...</p>
    <p>Site is working!</p>
    '''

@app.route('/api/info')
def get_info():
    return {'total': 0, 'status': 'test'}

if __name__ == '__main__':
    app.run(debug=True)
