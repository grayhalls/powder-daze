import streamlit as st
import pandas as pd 
import math 

@st.cache_data
def load_pricing_data():
    pricing = pd.read_excel('snow_removal_pricing.xlsx')
    pricing = pricing.replace('N/A', 'NaN').replace('N/A ', 'NaN').replace('.*/Bag', 'NaN', regex=True).replace('.*/bag', 'NaN', regex=True)
    pricing = pricing.astype({col: float for col in pricing.columns[2:16]})

    inch_pricing = pricing.drop(columns=['Region', 'Salting ', 'Flat Monthly Cost ', 'Unnamed: 17', 'Vendor ', 'Notes'])
    dict_list = []
    for _, row in inch_pricing.iterrows():
        site = row['RD']
        inch_dict = {col.strip('\"'): val for col, val in row.items() if col != 'RD'}
        dict_list.append({site: inch_dict})
    inch_pricing_dict = {k: v for d in dict_list for k, v in d.items()}
 
    pricing_dets = pricing[['RD', 'Salting ', 'Flat Monthly Cost ', 'Vendor ', 'Notes']]
    pricing_dets = {site:{'salt':salt, 'flat_cost': flat_cost, 'vendor': vendor, 'notes': notes} for site, salt,flat_cost,vendor,notes in pricing_dets.values}
 
    return {'inch_pricing':inch_pricing_dict, 'pricing_dets': pricing_dets}

@st.cache_data
def flat_monthly_rates(site):
    pricing_data = load_pricing_data()
    dets = pricing_data['pricing_dets']
    flat = dets.get(site,{}).get('flat_cost', 'N/A')
    if not math.isnan(flat):
        return True
    else:
        return False 
    
@st.cache_data
def find_price(site,inch):
    if inch < 1:
        return 0
    else:
        flat = flat_monthly_rates(site)
        pricing_data = load_pricing_data()
        if flat == True:
            return 0
        else:
            inch_price = pricing_data['inch_pricing']
            price = inch_price.get(site,{}).get(inch, 'N/A')
            return price

@st.cache_data
def salt_price(site,inch):
    if inch < 1:
        return 0
    else:
        pricing_data = load_pricing_data()
        dets = pricing_data['pricing_dets']
        salt = dets.get(site,{}).get('salt', 'N/A')
        return salt 
