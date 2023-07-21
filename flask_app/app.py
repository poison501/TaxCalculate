from flask import Flask, request, jsonify, render_template
import pandas as pd
from Taxable import calculate

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False  # Add this line

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'csv'}  # Set of allowed file extensions
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/', methods=['GET'])
def upload_form():
    return render_template('upload.html')

@app.route('/upload', methods=['POST'])
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

            # (Insert your DataFrame processing code here)
            result = calculate(df)

            item_summary = result['Item Summary']

            return render_template('results.html', 
                                   item_summary=item_summary, 
                                   num_multi_item_parcel=result['Number of multi-item ParcelNumbers'], 
                                   taxable_proportion=result['Proportion of taxable ParcelNumbers'], 
                                   unique_分单号_count=result['Sum of unique ParcelNumbers'], 
                                   total_tax=result['Total tax for taxable parcels'])
    return redirect('/')



if __name__ == '__main__':
    app.run(debug=True)
