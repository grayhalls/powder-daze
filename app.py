import streamlit as st
import plotly.graph_objects as go
import calendar
import datetime 
from dateutil.relativedelta import relativedelta as delta 
import streamlit_option_menu as option_menu
import pandas as pd 
import requests

#---------------SETTINGS--------------------
page_title = "Powder Daze"
page_icon = ":snowflake:"  #https://www.webfx.com/tools/emoji-cheat-sheet/
layout = "centered"
#-------------------------------------------

st.set_page_config(page_title=page_title, page_icon=page_icon, layout=layout)
st.title(page_title + " " + page_icon)

@st.cache_data
def convert_df(df):
    # IMPORTANT: Cache the conversion to prevent computation on every rerun
    return df.to_csv().encode('utf-8')

# --- HIDE STREAMLIT STYLE ---
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)


def get_dates(lookahead=1):
    # Get today's date
    end_date = datetime.date.today() -delta(days=7)
    # Add one week to today's date 
    start_date = end_date - delta(weeks=abs(lookahead)) 
    max_date=datetime.date.today() -delta(days=7)
    return start_date, end_date, max_date

@st.cache_data()
def date_pull(): 
    start_date, end_date, max_date = get_dates()  
    start_date, end_date, max_date = get_dates(lookahead=-4) 
    return {'start_date': start_date, 'end_date': end_date, 'max_date': max_date} 




# --- SELECT DATE RANGE ---
st.header(f"Select a date range")
with st.form("entry_form", clear_on_submit=False):
    dts = date_pull() 
    end_date = dts['end_date'] 
    start_date = dts['start_date'] 
    max_date = dts['max_date']
    start_date, end_date = st.date_input("Select date range", (start_date, end_date))
    # col1, col2 = st.columns(2)
    # start_date = col1.date_input("Start Date", value = dt.date(2023,1,1))
    # max_date = dt.date.today()- delta(days=7)
    # end_date = col2.date_input("End Date", value = max_date)
    # error msgs
    if start_date > end_date:
        st.error('Error: End date must fall after start date.')
    if max_date < end_date:
        st.error('Error: Data is not available more recently than a week ago.')

    "---"
# --- SELECT RD ---    
    rd_info = pd.read_csv('rd_info.csv')[['rd', 'latitude', 'longitude']]
    rds = rd_info['rd'].values.tolist()
    # rd_select = st.selectbox("Select a RD:", rds, key=str)
    rd_select = st.multiselect("Select a RD:", rds, key=str)
    
    submitted = st.form_submit_button("Submit")
 

# site --> lat, lng build dict up above and just query the dict
def site_lat_lng(site):
    rd_locs = {site:{'lat': lat, 'lng': lng} for site,lat,lng in rd_info.values}
    return rd_locs[site]['lat'], rd_locs[site]['lng']
    

def f(start_date, end_date, lat, lng): 
    # call the api - api is updated daily but with a 5 day delay
    r = requests.get(f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lng}&start_date={start_date}&end_date={end_date}&daily=snowfall_sum,rain_sum,apparent_temperature_min,apparent_temperature_max&timezone=auto&precipitation_unit=inch&temperature_unit=fahrenheit")
    res = r.json()
    return pd.DataFrame({
            'date': res['daily']['time'], 
            'snowfall': [round(snow,1) for snow in res['daily']['snowfall_sum']],
            'rainfall': [round(rain,1) for rain in res['daily']['rain_sum']] ,
            'max_temp': res['daily']['temperature_2m_max'],
            'min_temp':res['daily']['temperature_2m_min']
        })

if submitted:   
    st.success("Data saved!")

    lat, lng = site_lat_lng(rd_select)
    data = f(start_date, end_date, lat, lng)
    data['snowfall'] = data['snowfall']/2.54
# for metric in data['daily']: 
    # st.write(metric, len(data['daily'][metric]))
    st.write(data)


    st.download_button(
        label='Download data',
        data=convert_df(data),
        file_name=f'{rd_select}_{str(start_date)}_{str(end_date)}_weather_data.csv',
        mime='text/csv'
        )

# #----NAVIGATION MENU ---
# selected = option_menu(
#     menu_title = None,
#     option=["Data Entry", "Data Visualization"],
#     icons=["pencil-fill", "bar-chart-fill"], #https://icons.getbootstrap.com/
#     orientation="horizontal"
# )

# # --- INPUT & SAVE PERIODS ---
# if selected == "Data Entry":
#     st.header(f"Data Entry in {currency}")
#     with st.form("entry_form", clear_on_submit=True):
#         col1, col2 = st.columns(2)
#         col1.selectbox("Select Month:", months, key="month")
#         col2.selectbox("Select Year:", years, key="year")

#         "---"
#         with st.expander("Income"):
#             for income in incomes:
#                 st.number_input(f"{income}:", min_value=0, format="%i", step=10, key=income)
#         with st.expander("Expenses"):
#             for expense in expenses:
#                 st.number_input(f"{expense}:", min_value=0, format="%i", step=10, key=expense)
#         with st.expander("Comment"):
#             comment = st.text_area("", placeholder="Enter a comment here ...")

        
#         "---"
#         submitted = st.form_submit_button("Save Data")
#         if submitted:
#             period = str(st.session_state["year"]) + "_" + str(st.session_state["month"])
#             incomes = {income: st.session_state[income] for income in incomes}
#             expenses = {expense: st.session_state[expense] for expense in expenses}
#             st.success("Data saved!")


