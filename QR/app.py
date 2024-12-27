from flask import Flask, jsonify, send_file, render_template
import qrcode
import io

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html') 

@app.route('/generate_qr', methods=['GET'])
def generate_qr():
    qr_data = "https://example.com/inscripcion"
    qr_img = qrcode.make(qr_data)

    img_io = io.BytesIO()
    qr_img.save(img_io, 'PNG')
    img_io.seek(0)

    return jsonify({"qr_code_url": "/qr_code_image"})

@app.route('/qr_code_image', methods=['GET'])
def qr_code_image():
    qr_data = "https://example.com/inscripcion"
    qr_img = qrcode.make(qr_data)

    img_io = io.BytesIO()
    qr_img.save(img_io, 'PNG')
    img_io.seek(0)

    return send_file(img_io, mimetype='image/png')

if __name__ == '__main__':
    app.run(debug=True)
