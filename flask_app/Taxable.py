import pandas as pd
from prettytable import PrettyTable
from termcolor import colored

# Move hscode_mapping outside the function to make it a global variable
hscode_mapping = {
    1010700: {"商品类型": "婴幼儿配方奶粉", "关税税率": 0.13, "法定单位": "公斤", "完税价格": 200},
    1029900: {"商品类型": "其他饮料", "关税税率": 0.13, "法定单位": "公斤", "完税价格": None},
    1019900: {"商品类型": "其他食品", "关税税率": 0.13, "法定单位": "件", "完税价格": None},
    9020190: {"商品类型": "其他清洁用品", "关税税率": 0.20, "法定单位": "件", "完税价格": None},
    12990000: {"商品类型": "其他家具", "关税税率": 0.13, "法定单位": "件", "完税价格": None},
    9029900: {"商品类型": "其他清洁护理品", "关税税率": 0.20, "法定单位": "件", "完税价格": None},
    9020292: {"商品类型": "其他护肤用品", "关税税率": 0.20, "法定单位": "件", "完税价格": None}

}

# Function to calculate the package value and tax
def calculate_value_and_tax(row):
    price = row["Price"]
    quantity = row["数量"]
    tax_price = row["完税价格"]
    tax_rate = row["关税税率"]

    if pd.isnull(tax_price):
        value = price * quantity
        tax = value * tax_rate
    elif 0.5 * tax_price <= price <= 2 * tax_price:
        value = tax_price * quantity
        tax = value * tax_rate
    else:
        value = price * quantity
        tax = value * tax_rate

    return pd.Series([value, tax])

def calculate(df):
    # Create a set to store undefined HSCodes
    undefined_hscodes = set()

    # Create new columns and track undefined HSCodes
    df["申报单位"] = df["商品编码"].map(lambda x: hscode_mapping.get(x, {}).get("法定单位") if hscode_mapping.get(x) is not None else undefined_hscodes.add(x))
    df["完税价格"] = df["商品编码"].map(lambda x: hscode_mapping.get(x, {}).get("完税价格") if hscode_mapping.get(x) is not None else undefined_hscodes.add(x))
    df["关税税率"] = df["商品编码"].map(lambda x: hscode_mapping.get(x, {}).get("关税税率") if hscode_mapping.get(x) is not None else undefined_hscodes.add(x))

    # If there are undefined HSCodes, print them and exit
    if undefined_hscodes:
        print("Undefined HSCodes found, please add them: " + "; ".join(map(str, undefined_hscodes)))
        return

    # Rename a column
    df.rename(columns={"申报单价": "Price"}, inplace=True)

    # Calculate value and tax for each item
    df[["Value", "Tax"]] = df.apply(calculate_value_and_tax, axis=1)

    # Calculate tax status for each ParcelNumber
    tax_sum = df.groupby("分单号")["Tax"].sum()
    df["TaxStatus"] = df["分单号"].map(lambda x: "免税" if tax_sum[x] <= 50 else "出税")

    # Calculate the proportion of ParcelNumbers with a taxable status
    total_parcel_number = df['分单号'].nunique()
    taxable_parcel_number = df[df["TaxStatus"] == "出税"]['分单号'].nunique()
    taxable_proportion = taxable_parcel_number / total_parcel_number
    print(colored(f"The proportion of ParcelNumbers with a taxable status is {taxable_proportion*100:.2f}%.", "blue"))

    # Count the number of ParcelNumbers that contain more than one item
    multi_item_parcel_number = df['分单号'].value_counts()
    multi_item_parcel_number = multi_item_parcel_number[multi_item_parcel_number > 1]
    num_multi_item_parcel = len(multi_item_parcel_number)
    print(colored(f"There are {num_multi_item_parcel} ParcelNumbers that contain more than one item.", "red"))

    # Calculate the sum of tax for all parcels with "出税" status
    total_tax = df[df["TaxStatus"] == "出税"]["Tax"].sum()
    print(colored(f"The total tax for all parcels with a taxable status is {total_tax:.2f}.", "yellow"))

    # Calculate the tax average
    Tax_average = total_tax / taxable_parcel_number if taxable_parcel_number else 0

    # Output the sum of "数量" for each unique "物品名称"
    item_quantity_sum = df.groupby('物品名称')['数量'].sum().round(2).reset_index()

    # Calculate the number of unique "分单号" for each "物品名称"
    item_parcel_number_count = df.groupby('物品名称')['分单号'].nunique().reset_index()
    item_parcel_number_count.columns = ['物品名称', '分单数量']

    # Merge the two dataframes
    item_summary = pd.merge(item_quantity_sum, item_parcel_number_count, on='物品名称')
    item_summary.columns = ['物品名称', '数量之和', '分单数量']

    result = {
        'All Parcel Numbers': total_parcel_number,
        'Proportion of taxable ParcelNumbers': f"{taxable_proportion*100:.2f}%",
        'Number of multi-item ParcelNumbers': num_multi_item_parcel,
        'Total tax for taxable parcels': f"{total_tax:.2f}",
        'Tax average': f"{Tax_average:.2f}",
        'Item Summary': item_summary.to_dict(orient='records')  # Convert DataFrame to list of dicts
    }

    return result
