from flask import Flask, request, render_template, redirect, url_for
import pandas as pd
from Taxable import calculate, hscode_mapping

app = Flask(__name__)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'csv'}

@app.route('/add', methods=['GET', 'POST'])
def add_good():
    if request.method == 'POST':
        hscode = int(request.form['hscode'])
        goods_type = request.form['goods_type']
        tax_rate = float(request.form['tax_rate'].strip('%')) / 100
        legal_unit = request.form['legal_unit']
        tax_price = float(request.form['tax_price'])
        if hscode not in hscode_mapping:
            hscode_mapping[hscode] = {'商品类型': goods_type, '关税税率': tax_rate, '法定单位': legal_unit, '完税价格': tax_price}
        else:
            return 'HSCode already exists'
    return render_template('AddGood.html', hscode_mapping=hscode_mapping)

@app.route('/', methods=['GET'])
def home():
    return redirect(url_for('upload_file'))

@app.route('/upload', methods=['GET', 'POST'])  # Change this line to accept GET requests
def upload_file():
    if request.method == 'POST':
        # check if the post request has the file part
        if 'file' not in request.files:
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            return redirect(request.url)
        if file and allowed_file(file.filename):
            # Read the file
            df = pd.read_csv(file)
            # 提取不带扩展名的文件名
            cargo_batch = file.filename.rsplit('.', 1)[0]
            result = calculate(df)
            return render_template('results.html', result=result)
    elif request.method == 'GET':  # Handle GET requests
        return render_template('upload.html')

if __name__ == '__main__':
    app.run(debug=True)
