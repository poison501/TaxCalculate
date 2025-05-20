from flask import Flask, request, render_template, redirect, url_for, flash
import pandas as pd
import os
import datetime
from Taxable import calculate, hscode_mapping

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Required for flashing messages

# 确保log目录存在
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'log')
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'csv'}

@app.route('/add', methods=['GET', 'POST'])
def add_good():
    if request.method == 'POST':
        try:
            hscode = int(request.form['hscode'])
            goods_type = request.form['goods_type']
            tax_rate_str = request.form['tax_rate'].strip('%')
            tax_rate = float(tax_rate_str) / 100
            legal_unit = request.form['legal_unit']
            tax_price_str = request.form['tax_price']
            
            # Validate input
            if not goods_type:
                flash('商品类型不能为空', 'error')
                return render_template('AddGood.html', hscode_mapping=hscode_mapping)
            
            if not legal_unit:
                flash('法定单位不能为空', 'error')
                return render_template('AddGood.html', hscode_mapping=hscode_mapping)
            
            # Handle empty tax_price (can be None)
            tax_price = float(tax_price_str) if tax_price_str else None
            
            if hscode not in hscode_mapping:
                hscode_mapping[hscode] = {'商品类型': goods_type, '关税税率': tax_rate, '法定单位': legal_unit, '完税价格': tax_price}
                flash(f'HSCode {hscode} 已成功添加', 'success')
            else:
                flash(f'HSCode {hscode} 已存在', 'error')
        except ValueError:
            flash('请输入有效的数字值', 'error')
        
    return render_template('AddGood.html', hscode_mapping=hscode_mapping)

@app.route('/', methods=['GET'])
def home():
    return redirect(url_for('upload_file'))

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        # Check if the post request has the file part
        if 'file' not in request.files:
            flash('未选择文件', 'error')
            return redirect(request.url)
            
        file = request.files['file']
        if file.filename == '':
            flash('未选择文件', 'error')
            return redirect(request.url)
            
        if file and allowed_file(file.filename):
            try:
                # Read the file
                df = pd.read_csv(file)
                
                # Extract filename without extension
                cargo_batch = file.filename.rsplit('.', 1)[0]
                
                # Validate required columns
                required_columns = ["商品编码", "申报单价", "数量", "分单号", "物品名称"]
                missing_columns = [col for col in required_columns if col not in df.columns]
                
                if missing_columns:
                    flash(f'CSV文件缺少必要的列: {", ".join(missing_columns)}', 'error')
                    return render_template('upload.html')
                
                # Validate data types
                try:
                    # Convert columns to appropriate types
                    df["商品编码"] = df["商品编码"].astype(int)
                    df["申报单价"] = pd.to_numeric(df["申报单价"], errors='coerce')
                    df["数量"] = pd.to_numeric(df["数量"], errors='coerce')
                    
                    # Check for NaN values after conversion
                    if df["申报单价"].isna().any() or df["数量"].isna().any():
                        flash('CSV文件中包含无效的数值数据', 'error')
                        return render_template('upload.html')
                        
                except Exception as e:
                    flash(f'数据类型转换错误: {str(e)}', 'error')
                    return render_template('upload.html')
                
                # Check for undefined HSCodes before calculation
                undefined_hscodes = set()
                for hscode in df["商品编码"]:
                    if hscode not in hscode_mapping:
                        undefined_hscodes.add(hscode)
                
                if undefined_hscodes:
                    flash_msg = f'发现未定义的HSCode: {", ".join(map(str, undefined_hscodes))}, 请先添加这些HSCode'
                    flash(flash_msg, 'error')
                    return render_template('upload.html')
                
                # Calculate results
                result = calculate(df)
                
                if result:
                    # 获取计算后的完整数据
                    result_df = result['full_data']
                    
                    # 创建简化版导出数据
                    # 复制原始上传的CSV列
                    original_columns = df.columns.tolist()
                    export_df = result_df[original_columns].copy()
                    
                    # 添加两列：是否出税和税金金额
                    export_df['是否出税'] = result_df['TaxStatus']
                    export_df['税金金额'] = result_df['Tax']
                    
                    # 生成当前日期字符串(yyyymmdd)
                    today = datetime.datetime.now().strftime('%Y%m%d')
                    
                    # 构建日志文件名
                    log_filename = f"{cargo_batch}_{today}.csv"
                    log_path = os.path.join(log_dir, log_filename)
                    
                    # 保存CSV文件
                    export_df.to_csv(log_path, index=False, encoding='utf-8-sig')  # 使用utf-8-sig编码以支持Excel中的中文
                    
                    flash(f'已将计算结果导出到日志文件: {log_filename}', 'success')
                    return render_template('results.html', result=result, cargo_batch=cargo_batch)
                else:
                    flash('计算过程中出现错误', 'error')
                    return render_template('upload.html')
                    
            except pd.errors.EmptyDataError:
                flash('上传的CSV文件为空', 'error')
                return render_template('upload.html')
            except pd.errors.ParserError:
                flash('CSV文件格式错误', 'error')
                return render_template('upload.html')
            except Exception as e:
                flash(f'处理文件时出错: {str(e)}', 'error')
                return render_template('upload.html')
        else:
            flash('仅允许上传CSV文件', 'error')
            return render_template('upload.html')
    elif request.method == 'GET':
        return render_template('upload.html')

if __name__ == '__main__':
    app.run(debug=True)
