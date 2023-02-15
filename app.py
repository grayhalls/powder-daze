import streamlit as st
import calendar
import datetime 
from dateutil.relativedelta import relativedelta as delta 
from streamlit_option_menu import option_menu
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


# --- HIDE STREAMLIT STYLE ---
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)


# ----- FUNCTIONS -----

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

def password_authenticate(pwsd):

    if pwsd == st.secrets["ADMIN"]:
        return True

    if pwsd == st.secrets["PCs"]:
        return True

    else:
        return False

# --- API function ---
@st.cache_data
def f(start_date, end_date, rd_select, elements_select):

    lat, lng = rd_locs[rd_select]['lat'], rd_locs[rd_select]['lng']

    # call the api - api is updated daily but with a 5 day delay

    if elements_select == 'all':
        selected_keys = list(element_keys.values())
    else:
        selected_keys = [element_keys[e] for e in [elements_select]]
    r = requests.get(f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lng}&start_date={start_date}&end_date={end_date}&daily={','.join(selected_keys)}&timezone=auto&precipitation_unit=inch&temperature_unit=fahrenheit")
    res = r.json()
    
    # create the dataframe 
    df_dict = {'date': res['daily']['time']}
    for e in selected_keys:
        for k, v in element_keys.items():
            if v == e:
                df_dict[k] = res['daily'][e]

    return pd.DataFrame(df_dict)


    # --- NAVIGATION MENU ---
selected = option_menu(
    menu_title=None,
    options=["Individual RD Breakdown", "Snowfall Summary"],
    icons=["geo", "snow"],  # https://icons.getbootstrap.com/
    orientation="horizontal",
    )

if selected == "Individual RD Breakdown":
    # --------- FORM: SELECT DATE RANGE --------
    st.header(f"Select a date range")
    with st.form("entry_form", clear_on_submit=False):
        dts = date_pull() 
        end_date = dts['end_date'] 
        start_date = dts['start_date'] 
        max_date = dts['max_date']

        col1, col2, col3 = st.columns(3)
        start_date, end_date = col1.date_input("Select date range", (start_date, end_date))

        # error msgs
        if start_date > end_date:
            st.error('Error: End date must fall after start date.')
        if max_date < end_date:
            st.error('Error: Data is not available more recently than a week ago.')

        # ----- SELECT RD -----    
        rd_info = pd.read_csv('rd_info.csv')
        rd_locs = {site:{'lat': lat, 'lng': lng} for site,lat,lng in rd_info.values}
        rds = rd_info['rd'].values.tolist()
        rd_select = col2.selectbox("Select a RD:", rds, key=str)
        
        element_keys = {'snow': 'snowfall_sum', 'rain': 'rain_sum', 'high temp': 'temperature_2m_max', 'low temp': 'temperature_2m_min', 'hours of precipitation': 'precipitation_hours'}
        elements = list(element_keys.keys())
        elements.insert(0,'all')
        
        elements_select = col3.selectbox("Select weather data type:", elements)
        
        "---"
        # -----INPUT PASSWORD-----
        pc_password = st.text_input("Password") 

        submitted = st.form_submit_button("Submit")
    
    if submitted:  
            
            password_valid = password_authenticate(pc_password) 
            
            if password_valid:  
                st.success("Valid Password")

                data = f(start_date, end_date, rd_select, elements_select)

                if 'snow' in elements_select or 'all' in elements_select:
                    data['snow'] = round(data['snow']/2.54, 1)
                if 'rain' in elements_select:
                    data['rain'] = round(data['rain'], 1)
                
                if 'snow' in elements_select or 'all' in elements_select:
                    chart_data = data[['date', 'snow']]
                    y_axis_label = 'Snowfall (in)'
                    bars = alt.Chart(chart_data).mark_bar(width=18).encode(
                    x=alt.X('date:T', title='Date'),
                    y=alt.Y(f'sum(snow):Q', title=y_axis_label)
                    )
                    line = alt.Chart(pd.DataFrame({'y': [1]})).mark_rule(color = 'pink', strokeWidth=2, strokeDash=[5,5]).encode(
                        y='y:Q'
                    )
                    chart = (bars + line).interactive()
                    total_snow = data['snow'].sum()
                    total_snow = round(total_snow, 2)
                    days_over_inch = len(chart_data[chart_data['snow']>1])

                else:
                    chart_data = data[['date', elements_select]]
                    y_axis_label = ' '.join([e.capitalize() for e in elements_select])
                    
                    chart = alt.Chart(chart_data).mark_bar(width=18).encode(
                    x=alt.X('date:T', title='Date'),
                    y=alt.Y(f'sum({[elements_select]}):Q', title=y_axis_label)
                    ).interactive()


                "---"
                st.altair_chart(chart, theme="streamlit", use_container_width=True )
                if 'snow' in elements_select or 'all' in elements_select:
                    col1, col2, col3, col4, col5, col6 = st.columns(6)
                    col3.metric("Plow Days", f"{days_over_inch}")
                    col4.metric("Total Snowfall", f"{total_snow}")
            
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


if selected == "Snowfall Summary":
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
        
        # elements = {'snow', 'high temp', 'low temp', 'rain', 'hours of precipitation'}
        # elements_selected = col2.multiselect("Select weather data type:", elements)

         # ----- SELECT RD -----    
        rd_info = pd.read_csv('rd_info.csv')[['rd', 'latitude', 'longitude']]
        rd_locs = {site:{'lat': lat, 'lng': lng} for site,lat,lng in rd_info.values}
        rd_values = rd_info['rd'].values.tolist()
        # rd_values.extend(('North', 'Central'))
        rd_values.insert(0, 'North')
        rd_values.insert(1, 'Central')
        rd_select = col2.multiselect("Select a Region or multiple RDs:", rd_values, key=str)

        "---"
        # -----INPUT PASSWORD-----
        # pc_password = st.text_input("Password") 

        submitted = st.form_submit_button("Submit")
    
        if submitted:  
            
            # password_valid = password_authenticate(pc_password) 
            
            # if password_valid:  
                st.success("Valid Password")

                data(start_date, end_date, 

