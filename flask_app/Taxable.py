import pandas as pd
from prettytable import PrettyTable
from termcolor import colored
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Move hscode_mapping outside the function to make it a global variable
hscode_mapping = {
    1010700: {"商品类型": "婴幼儿配方奶粉", "关税税率": 0.13, "法定单位": "公斤", "完税价格": None},
    1029900: {"商品类型": "其他饮料", "关税税率": 0.13, "法定单位": "公斤", "完税价格": None},
    1019900: {"商品类型": "其他食品", "关税税率": 0.13, "法定单位": "件", "完税价格": None},
    9020190: {"商品类型": "其他清洁用品", "关税税率": 0.20, "法定单位": "件", "完税价格": None},
    12990000: {"商品类型": "其他家具", "关税税率": 0.13, "法定单位": "件", "完税价格": None},
    9029900: {"商品类型": "其他清洁护理品", "关税税率": 0.20, "法定单位": "件", "完税价格": None},
    9020292: {"商品类型": "其他护肤用品", "关税税率": 0.20, "法定单位": "件", "完税价格": None},
    9020110: {"商品类型": "洗面奶、洁面霜", "关税税率": 0.20, "法定单位": "支", "完税价格": None},
    9020232:{"商品类型":"面霜及乳液", "关税税率":0.20, "法定单位":"瓶", "完税价格":None},
    1010100:{"商品类型":"奶粉", "关税税率":0.13, "法定单位":"公斤", "完税价格":None},
    9020220:{"商品类型":"普通涂抹式护肤品", "关税税率":0.20, "法定单位":"支", "完税价格":None}
}

# Function to calculate the package value and tax
def calculate_value_and_tax(row):
    try:
        price = row["Price"]
        quantity = row["数量"]
        tax_price = row["完税价格"]
        tax_rate = row["关税税率"]

        # Check for NaN or invalid values
        if pd.isna(price) or pd.isna(quantity) or pd.isna(tax_rate):
            logger.warning(f"Found NaN values in row: {row}")
            return pd.Series([0, 0])  # Return zeros for invalid data

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
    except Exception as e:
        logger.error(f"Error calculating value and tax for row: {row}. Error: {str(e)}")
        return pd.Series([0, 0])  # Return zeros for error cases

def calculate(df):
    try:
        # Validate DataFrame
        if df.empty:
            logger.warning("Empty DataFrame provided")
            return None

        # Create a set to store undefined HSCodes
        undefined_hscodes = set()

        # Create new columns and track undefined HSCodes
        df["申报单位"] = df["商品编码"].map(lambda x: hscode_mapping.get(x, {}).get("法定单位") if hscode_mapping.get(x) is not None else undefined_hscodes.add(x))
        df["完税价格"] = df["商品编码"].map(lambda x: hscode_mapping.get(x, {}).get("完税价格") if hscode_mapping.get(x) is not None else undefined_hscodes.add(x))
        df["关税税率"] = df["商品编码"].map(lambda x: hscode_mapping.get(x, {}).get("关税税率") if hscode_mapping.get(x) is not None else undefined_hscodes.add(x))

        # If there are undefined HSCodes, log them and return None
        if undefined_hscodes:
            undefined_msg = "Undefined HSCodes found: " + "; ".join(map(str, undefined_hscodes))
            logger.warning(undefined_msg)
            return None

        # Rename a column
        df.rename(columns={"申报单价": "Price"}, inplace=True)

        # Calculate value and tax for each item
        df[["Value", "Tax"]] = df.apply(calculate_value_and_tax, axis=1)

        # Round Tax to 2 decimal places
        df["Tax"] = df["Tax"].round(2)

        # Calculate tax status for each ParcelNumber
        tax_sum = df.groupby("分单号")["Tax"].sum()
        df["TaxStatus"] = df["分单号"].map(lambda x: "免税" if tax_sum[x] <= 50 else "出税")

        # Calculate the proportion of ParcelNumbers with a taxable status
        total_parcel_number = df['分单号'].nunique()
        taxable_parcel_number = df[df["TaxStatus"] == "出税"]['分单号'].nunique()
        
        # Avoid division by zero
        if total_parcel_number > 0:
            taxable_proportion = taxable_parcel_number / total_parcel_number
        else:
            taxable_proportion = 0
            logger.warning("No unique ParcelNumbers found")
            
        # Log instead of print to console
        logger.info(f"The proportion of ParcelNumbers with a taxable status is {taxable_proportion*100:.2f}%.")

        # Count the number of ParcelNumbers that contain more than one item
        multi_item_parcel_number = df['分单号'].value_counts()
        multi_item_parcel_number = multi_item_parcel_number[multi_item_parcel_number > 1]
        num_multi_item_parcel = len(multi_item_parcel_number)
        logger.info(f"There are {num_multi_item_parcel} ParcelNumbers that contain more than one item.")

        # Calculate the sum of tax for all parcels with "出税" status
        total_tax = df[df["TaxStatus"] == "出税"]["Tax"].sum()
        logger.info(f"The total tax for all parcels with a taxable status is {total_tax:.2f}.")

        # Calculate the tax average with zero division check
        Tax_average = total_tax / taxable_parcel_number if taxable_parcel_number > 0 else 0

        # Output the sum of "数量" for each unique "物品名称"
        item_quantity_sum = df.groupby('物品名称')['数量'].sum().round(2).reset_index()

        # Calculate the number of unique "分单号" for each "物品名称"
        item_parcel_number_count = df.groupby('物品名称')['分单号'].nunique().reset_index()
        item_parcel_number_count.columns = ['物品名称', '分单数量']

        # Merge the two dataframes
        item_summary = pd.merge(item_quantity_sum, item_parcel_number_count, on='物品名称')
        item_summary.columns = ['物品名称', '数量之和', '分单数量']

        # Calculate tax details by HSCode
        # Get only taxable parcels
        taxable_df = df[df["TaxStatus"] == "出税"]
        
        # Group by HSCode and calculate tax statistics
        hscode_tax_stats = []
        if not taxable_df.empty:
            # Get unique HSCodes
            unique_hscodes = df["商品编码"].unique()
            
            for hscode in unique_hscodes:
                # Filter data for this HSCode
                hscode_data = taxable_df[taxable_df["商品编码"] == hscode]
                
                if not hscode_data.empty:
                    # Count unique taxable parcel numbers for this HSCode
                    taxable_parcels_count = hscode_data["分单号"].nunique()
                    
                    # Sum tax for this HSCode
                    total_tax_for_hscode = hscode_data["Tax"].sum()
                    
                    # Add to results
                    hscode_tax_stats.append({
                        "HSCode": hscode,
                        "商品类型": hscode_mapping.get(hscode, {}).get("商品类型", "未知"),
                        "出税分单数": taxable_parcels_count,
                        "出税金额": round(total_tax_for_hscode, 2)
                    })

        result = {
            'All Parcel Numbers': total_parcel_number,
            'Proportion of taxable ParcelNumbers': f"{taxable_proportion*100:.2f}%",
            'Number of multi-item ParcelNumbers': num_multi_item_parcel,
            'Total tax for taxable parcels': f"{total_tax:.2f}",
            'Tax average': f"{Tax_average:.2f}",
            'Item Summary': item_summary.to_dict(orient='records'),  # Convert DataFrame to list of dicts
            'HSCode Tax Details': hscode_tax_stats,  # Add the new HSCode tax details
            'full_data': df  # Add the full DataFrame with calculations to the result
        }

        return result
    except Exception as e:
        logger.error(f"Error in calculate function: {str(e)}")
        return None
