import streamlit as st
import pandas as pd 
import math 
import datetime 
from dateutil.relativedelta import relativedelta as delta 

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
    rd_info = pd.read_csv('rd_info.csv')[['rd', 'latitude', 'longitude', 'Region']]
    
    rd_info = rd_info[~rd_info['Region'].isin(exclude_region)]
    rd_locs = {site:{'lat': lat, 'lng': lng, 'region': region} for site, lat, lng, region in rd_info.values}
    rds = rd_info['rd'].values.tolist()
    regions = rd_info['Region'].values.tolist()

    central_rds = rd_info[rd_info['Region'] == 'Central']['rd'].values.tolist()
    north_rds = rd_info[rd_info['Region'] == 'North']['rd'].values.tolist()

    return {'rd_loc_dict': rd_locs, 'rds': rds, 'regions':regions, 'central_rds': central_rds,'north_rds':north_rds}


@st.cache_data
def load_pricing_data():
    pricing = pd.read_csv('snow_removal_pricing.csv')
    pricing = pricing.applymap(lambda x: x.strip() if isinstance(x, str) else x)
    pricing = pricing.rename(columns=lambda x: x.strip())
    pricing = pricing.replace('N/A', '0').replace('$-', '0')
   
    pricing = pricing.astype({col: float for col in pricing.columns[2:16]})

    inch_pricing = pricing.drop(columns=['Region', 'Salting', 'Flat Monthly Cost', 'Unnamed: 17', 'Vendor', 'Notes'])
    dict_list = []
    for _, row in inch_pricing.iterrows():
        site = row['RD']
        inch_dict = {col.strip('\"'): val for col, val in row.items() if col != 'RD'}
        for key in inch_dict.keys():
            if pd.isna(inch_dict[key]):
                inch_dict[key] = inch_dict[prev_key]
            else:
                prev_key = key
        inch_dict = pd.DataFrame(inch_dict, index=[0]).fillna(0).to_dict('records')[0]
        dict_list.append({site: inch_dict})
  
    inch_pricing_dict = {k: v for d in dict_list for k, v in d.items()}
 
    pricing_dets = pricing[['RD', 'Salting', 'Flat Monthly Cost', 'Vendor', 'Notes']]
    pricing_dets = {site:{'salt':salt, 'flat_cost': flat_cost, 'vendor': vendor, 'notes': notes, 'flat': not math.isnan(flat_cost)} for site, salt,flat_cost,vendor,notes in pricing_dets.to_dict('split')['data']}

    return {'inch_pricing':inch_pricing_dict, 'pricing_dets': pricing_dets}



@st.cache_data
def salt_price(site):
    pricing_data = load_pricing_data()
    dets = pricing_data['pricing_dets']
    if site in dets and 'salt' in dets[site]:
        return dets[site]['salt']
    else:
        return 0
