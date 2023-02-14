import streamlit as st
import calendar
import datetime 
from dateutil.relativedelta import relativedelta as delta 
import streamlit_option_menu as option_menu
import pandas as pd 
import requests
import altair as alt

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

@st.cache_data
def date_pull(): 
    start_date, end_date, max_date = get_dates()  
    start_date, end_date, max_date = get_dates(lookahead=-4) 
    return {'start_date': start_date, 'end_date': end_date, 'max_date': max_date} 

def password_authenticate(pwsd):

    if pwsd == st.secrets["ADMIN"]:
        return True

    if pwsd == st.secrets["PCs"]:
        return True

    else:
        return False



# --------- FORM: SELECT DATE RANGE --------
st.header(f"Select a date range")
with st.form("entry_form", clear_on_submit=False):
    dts = date_pull() 
    end_date = dts['end_date'] 
    start_date = dts['start_date'] 
    max_date = dts['max_date']

    col1, col2 = st.columns(2)
    start_date, end_date = col1.date_input("Select date range", (start_date, end_date))

    # error msgs
    if start_date > end_date:
        st.error('Error: End date must fall after start date.')
    if max_date < end_date:
        st.error('Error: Data is not available more recently than a week ago.')

    # ----- SELECT RD -----    
    rd_info = pd.read_csv('rd_info.csv')[['rd', 'latitude', 'longitude']]
    rd_locs = {site:{'lat': lat, 'lng': lng} for site,lat,lng in rd_info.values}
    rds = rd_info['rd'].values.tolist()
    rd_select = col2.selectbox("Select a RD:", rds, key=str)

    "---"
    # -----INPUT PASSWORD-----
    pc_password = st.text_input("Password") 

    submitted = st.form_submit_button("Submit")
 
if submitted:  
        
        password_valid = password_authenticate(pc_password) 
        
        if password_valid:  
            st.success("Valid Password")
            # --- API function ---
            @st.cache_data
            def f(start_date, end_date, rd_select): 

                lat,lng = rd_locs[rd_select]['lat'], rd_locs[rd_select]['lng']

                # call the api - api is updated daily but with a 5 day delay
                r = requests.get(f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lng}&start_date={start_date}&end_date={end_date}&daily=snowfall_sum,rain_sum,temperature_2m_min,temperature_2m_max&timezone=auto&precipitation_unit=inch&temperature_unit=fahrenheit")
                res = r.json()
                
                return pd.DataFrame({
                        'date': res['daily']['time'], 
                        'snowfall': res['daily']['snowfall_sum'],
                        'rainfall': res['daily']['rain_sum'],
                        'max_temp': res['daily']['temperature_2m_max'],
                        'min_temp':res['daily']['temperature_2m_min']
                    })

                

            data = f(start_date, end_date, rd_select)

            data['snowfall'] = data['snowfall']/2.54
            data['snowfall'] = round(data['snowfall'],1)
            data['rainfall'] = round(data['rainfall'],1)

            chart_date = data[['date','snowfall']]
            chart = alt.Chart(chart_date).mark_bar().encode(
                x='date',
                y='sum(snowfall)'
            ).interactive() 

            st.altair_chart(chart, theme="streamlit", use_container_width=True )

            st.dataframe(data,1000)

            st.download_button(
                label='Download data',
                data=convert_df(data),
                file_name=f'{rd_select}_{str(start_date)}_{str(end_date)}_weather_data.csv',
                mime='text/csv'
                )

        else: 
            st.error("Invalid Password") 
            st.markdown("Contact Holly if you're having password issues")


