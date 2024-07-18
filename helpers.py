import streamlit as st
import pandas as pd 
import math 
import datetime 
from dateutil.relativedelta import relativedelta as delta 
import boto3 
import json  
from io import StringIO, BytesIO   

MASTER_ACCESS_KEY = st.secrets['MASTER_ACCESS_KEY']
MASTER_SECRET = st.secrets['MASTER_SECRET']

@st.cache_data
def convert_df(df):
    # IMPORTANT: Cache the conversion to prevent computation on every rerun
    return df.to_csv().encode('utf-8')

def get_dates(lookahead=1):
    # Get today's date
    end_date = datetime.date.today() -delta(days=8)
    # Add one week to today's date 
    start_date = end_date - delta(weeks=abs(lookahead)) 
    max_date=datetime.date.today() -delta(days=8)
    return start_date, end_date, max_date

@st.cache_data
def date_pull(): 
    start_date, end_date, max_date = get_dates()  
    start_date, end_date, max_date = get_dates(lookahead=-4) 
    return {'start_date': start_date, 'end_date': end_date, 'max_date': max_date} 

@st.cache_data 
def load_rd_data(exclude_region=None):
    if exclude_region is None:
        exclude_region = []
    
    rd_info = grab_s3_file(f = 'powder-daze/location_info.csv', bucket = 'sroa-ops-files')[['location', 'latitude', 'longitude', 'Region', 'District', 'rd']]
    rd_info = rd_info[~rd_info['Region'].isin(exclude_region)]

    rd_info['District'] = rd_info['District'].fillna(0).astype(int)

    rd_locs = {site: {'lat': lat, 'lng': lng, 'region': region, 'district': district, 'rd': rd} 
               for site, lat, lng, region, district, rd in rd_info.values}
    
    districts = rd_info['District'].unique().tolist()
    districts = sorted([int(d) for d in districts if pd.notna(d)]) 
    district_store_map = {district: rd_info[rd_info['District'] == district]['location'].tolist() for district in districts}

    rds = rd_info['rd'].dropna().tolist()
    stores = rd_info['location'].values.tolist()
    regions = rd_info['Region'].unique().tolist()

    return {'rd_loc_dict': rd_locs, 'stores': stores, 'rds': rds, 'regions': regions, 'district_store_map': district_store_map}


# @st.cache_data
def load_pricing_data():
    pricing = grab_s3_file(f = 'powder-daze/snow_removal_pricing.csv', bucket = 'sroa-ops-files')
    pricing = pricing.map(lambda x: x.strip() if isinstance(x, str) else x)
    pricing = pricing.rename(columns=lambda x: x.strip())
    pricing = pricing.replace('N/A', '0').replace('$-', '0')
   
    pricing = pricing.astype({col: float for col in pricing.columns[2:15]})
    # print(pricing) 
    inch_pricing = pricing.drop(columns=['Salting', 'Flat Monthly Cost', 'Vendor', 'Notes','RD'])
    dict_list = []
    for _, row in inch_pricing.iterrows():
        site = row['Location']
        # print(site)
        inch_dict = {col.strip('\"'): val for col, val in row.items() if col != 'Location'}
        # print(inch_dict)
        for key in inch_dict.keys():
            if pd.isna(inch_dict[key]):
                inch_dict[key] = inch_dict[prev_key]
            else:
                prev_key = key
        inch_dict = pd.DataFrame(inch_dict, index=[0]).fillna(0).to_dict('records')[0]
        dict_list.append({site: inch_dict})
  
    inch_pricing_dict = {k: v for d in dict_list for k, v in d.items()}
 
    pricing_dets = pricing[['Location', 'Salting', 'Flat Monthly Cost', 'Vendor', 'Notes']]
    pricing_dets = {site:{'salt':salt, 'flat_cost': flat_cost, 'vendor': vendor, 'notes': notes, 'flat': not math.isnan(flat_cost)} for site, salt,flat_cost,vendor,notes in pricing_dets.to_dict('split')['data']}

    return {'inch_pricing':inch_pricing_dict, 'pricing_dets': pricing_dets}



@st.cache_data
def salt_price(site):
    pricing_data = load_pricing_data()
    dets = pricing_data['pricing_dets']
    if site in dets and 'salt' in dets[site]:
        try:
            return float(dets[site]['salt'])
        except ValueError:
            st.error(f"Salt price for {site} is not a valid float.")
            return 0.0
    else:
        return 0


def s3_init():  
    
    # --- s3 client --- 
    s3 = boto3.client('s3', region_name = 'us-west-1', 
          aws_access_key_id=MASTER_ACCESS_KEY, 
          aws_secret_access_key=MASTER_SECRET) 
    return s3 

def grab_s3_file(f, bucket, idx_col=None, is_json=False):
    s3 = s3_init()
    data = s3.get_object(Bucket=bucket, Key=f)['Body'].read().decode('utf-8') 
    
    # Check if the file is a JSON
    if is_json:
        return json.loads(data)  # Return the parsed JSON data as a dictionary
    
    # If the file is a CSV
    if idx_col is None:
        data = pd.read_csv(StringIO(data)) 
    else:
        data = pd.read_csv(StringIO(data), index_col=idx_col)

# we can add a pickle function to this if needed
    return data 

def upload_file_to_s3(bucket, file_name, data, file_type = 'csv'):
    s3 = s3_init()
    csv_buffer = StringIO()
    if file_type == 'csv':
        # If the data is a DataFrame and needs to be uploaded as CSV
        csv_buffer = StringIO()
        data.to_csv(csv_buffer, index=False)
        body = csv_buffer.getvalue()
    elif file_type == 'json':
        # If the data is a dict/list and needs to be uploaded as JSON
        json_buffer = BytesIO(json.dumps(data).encode('utf-8'))
        body = json_buffer.getvalue()
    else:
        raise ValueError(f"Unsupported file_type: {file_type}")

    # Use the S3 client to upload the file
    s3.put_object(Bucket=bucket, Key=file_name, Body=body)
