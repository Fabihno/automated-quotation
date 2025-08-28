from flask import send_file, abort
import os

from app import app

@app.route('/download')
def download_file():
    file_path = request.args.get('file')
    if not file_path:
        abort(400, description="No file specified")
    
    full_path = os.path.join(app.config['QUOTATIONS_DIR'], file_path)
    if not os.path.exists(full_path):
        abort(404, description="File not found")
    
    return send_file(full_path, as_attachment=True)