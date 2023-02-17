import streamlit as st
from streamlit_option_menu import option_menu
import pandas as pd 
import requests
import altair as alt
from helpers import *

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
def password_authenticate(pwsd):

    if pwsd == st.secrets["ADMIN"]:
        return True

    if pwsd == st.secrets["PCs"]:
        return True

    else:
        return False

def blank(): return st.write('') 

# --- API function ---
@st.cache_data
def grab_weather(start_date, end_date, rd_select, elements_select):
    rd_data = load_rd_data()
    rd_locs = rd_data['rd_loc_dict']
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

def add_pricing(start_date,end_date,rd_select):
    data= grab_weather(start_date,end_date,rd_select,'all')
    data['snow'] = round(data['snow']/2.54, 1)
    data['inches_snow'] = (data['snow']).astype(int)
    plow_prices = []
    for i in data['inches_snow']:
        if i < 1:
            plow_price=0
        else:
            plow_price = find_price(rd_select,i)
        plow_prices.append(plow_price)

    data['plow price'] = plow_prices
    data=data.drop(columns=['inches_snow'])
    return data 

    # --- NAVIGATION MENU ---
selected = option_menu(
    menu_title=None,
    options=["Individual RD Breakdown", "Snowfall Summary"],
    icons=["geo", "snow"],  # https://icons.getbootstrap.com/
    orientation="horizontal",
    )

if selected == "Individual RD Breakdown":
    # --------- FORM: SELECT DATE RANGE --------
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
        rd_data = load_rd_data()
        rd_select = col2.selectbox("Select a RD:", rd_data['rds'], key=str)
        
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

                data = grab_weather(start_date, end_date, rd_select, elements_select)

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

                    snow_dataframe = add_pricing(start_date, end_date, rd_select)
                    plow_cost = snow_dataframe['plow price'].sum()
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
                    col1, col2, col3, col4, col5 = st.columns(5)
                    col2.metric("Plow Days", f"{days_over_inch}")
                    col3.metric("Total Snowfall", f"{total_snow}")
                    col4.metric("Total Plow Cost", f"{plow_cost}")
                    blank() 
                    table = st.dataframe(snow_dataframe,1000)
                else:
                    blank()
                    table =st.dataframe(data,1000)

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
    # st.header(f"Select a date range")
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
        rd_data = load_rd_data(exclude_region=['South'])
        rd_values = rd_data['rds']
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

                # data(start_date, end_date, 

