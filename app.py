import streamlit as st
from streamlit_option_menu import option_menu
import pandas as pd 
import numpy as np
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
            MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)


pricing_data = load_pricing_data()
rd_data = load_rd_data(exclude_region=['South'])
salt_price_vec = np.vectorize(salt_price)

# ----- FUNCTIONS -----
def password_authenticate(pwsd):

    if pwsd == st.secrets["ADMIN"]:
        return True

    if pwsd == st.secrets["PCs"]:
        return True

    else:
        return False

def blank(): return st.write('') 

def find_price(site, inch, pricing_data):
    if pricing_data['pricing_dets'][site]['flat']:
        return pricing_data['pricing_dets'][site]['flat_cost']
    else:
        inch_price = pricing_data['inch_pricing']
        if site in inch_price and str(inch) in inch_price[site]:
            return inch_price[site][str(inch)]
        else:
            return 0
# --- API function ---
# @st.cache_data
def grab_weather(start_date, end_date, rd_select, elements_select, rd_data):
    rd_locs = rd_data['rd_loc_dict']
    lat, lng = rd_locs[rd_select]['lat'], rd_locs[rd_select]['lng']

    # call the api - api is updated daily but with a 5 day delay

    if elements_select == 'snow':
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

    return {rd_select: df_dict}
       
@st.cache_data
def add_pricing(weather_dict, rd_select):
    print(weather_dict)
    inches_snow = [int(round(i,0)) for i in weather_dict[rd_select].get('snow', [])]
    data = {'date': weather_dict[rd_select].get('date', []), 'snow': weather_dict[rd_select].get('snow', []), 
            'rain': weather_dict[rd_select].get('rain', []),
            'high temp': weather_dict[rd_select].get('high temp', []), 
            'low temp': weather_dict[rd_select].get('low temp', []), 
            'hours of precipitation': weather_dict[rd_select].get('hours of precipitation', [])}
    
    # Calculate plow prices and estimated salt usage using vectorized functions
    vectorized_find_price = np.vectorize(find_price)
    plow_prices = np.where(np.array(inches_snow) < 1, 0, vectorized_find_price(rd_select, np.array(inches_snow), pricing_data))
    est_salt = np.where(plow_prices == 0, 0, salt_price(rd_select))

    # Add results to dictionary
    data['plow price'] = plow_prices.tolist()
    data['est salt'] = est_salt.tolist()

    return data

@st.cache_data
def all_weather(start_date, end_date, rds_select):
    weather = {}
    for site in rds_select: 
        print(site)
        weather_dict = grab_weather(start_date, end_date, site, 'snow', rd_data)
        weather[site]={'date': weather_dict[site]['date'], 'snow': weather_dict[site]['snow']}

    return weather 


@st.cache_data
def aggregate(pricing_data, rd_select, weather):
    results = []
    for location in rd_select:
        snow_data = weather[location]['snow']  

        if location in pricing_data['pricing_dets']:
        
            if pricing_data['pricing_dets'][location]['flat']:
                days_over_inch = sum(1 for snow in snow_data if snow > 1)
                plow_cost = find_price(location, 1, pricing_data)  
                total_cost = plow_cost
                salt_cost = days_over_inch * salt_price(location)
            # elif snow_data.isnull().any():
            #     days_over_inch = sum(1 for snow in snow_data if snow > 1)
            #     plow_cost = 0 #data['plow price'].sum()
            else:
                pricing = add_pricing(weather, location) 
                days_over_inch = len([x for x in pricing['plow price'] if x >0])
                plow_cost = sum(pricing['plow price'])

                salt_cost = sum(pricing['est salt'])
                total_cost = salt_cost + plow_cost 
            
            #print(weather, type(weather))
            total_snow = round(sum(weather[location]['snow']), 2)
            results.append({'RD':location, 'plow cost': plow_cost, 
                            'days over inch': days_over_inch, 
                            'salt cost': salt_cost, 
                            'total cost': total_cost, 
                            'total snow': total_snow})

    return pd.DataFrame(results)



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
        
        elements_select = col3.selectbox("Select weather data type:", elements)
        
        # -----INPUT PASSWORD-----
        col4, col5, col6 = st.columns(3)
        pc_password = col4.text_input("Password") 
        snow = col5.checkbox('More Snow?')

        submitted = st.form_submit_button("Submit")
    
    if submitted:  
            
            password_valid = password_authenticate(pc_password) 
            
            if password_valid:  
                st.success("Valid Password", icon="❄️")
                if snow:
                    st.snow() 

                weather_data = grab_weather(start_date, end_date, rd_select, elements_select, rd_data)
                # st.write(weather_data)
                # new_data = {k: v for k, v in weather_data.values()}

                # Create a DataFrame from the new dictionary
                data = pd.DataFrame(weather_data[rd_select])

                if 'snow' in elements_select:
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
                    
                    snow_dataframe = add_pricing(weather_data, rd_select)
                    snow_dataframe = pd.DataFrame(snow_dataframe)

                    if pricing_data['pricing_dets'][rd_select]['flat']:
                        snow_dataframe=snow_dataframe.drop(columns = ['plow price'])
                        days_over_inch = len(chart_data[chart_data['snow']>1])
                        plow_cost = pricing_data['pricing_dets'][rd_select]['flat_cost']
                    else:
                        days_over_inch = len(snow_dataframe[snow_dataframe['plow price']>0])
                        plow_cost = snow_dataframe['plow price'].sum()

                    salt_cost = snow_dataframe['est salt'].sum()

                else:
                    chart_data = data[['date', elements_select]]
                    y_axis_label = ' '.join([e.capitalize() for e in elements_select])
                    
                    chart = alt.Chart(chart_data).mark_bar(width=18).encode(
                    x=alt.X('date:T', title='Date'),
                    y=alt.Y(f'sum({[elements_select]}):Q', title=y_axis_label)
                    ).interactive()

                "---"
                st.altair_chart(chart, theme="streamlit", use_container_width=True )
                
                if 'snow' in elements_select: 
                    col1, col2, col3, col4 = st.columns(4)
                    col4.metric("Plow Days", f"{days_over_inch}")
                    col3.metric("Total Snowfall", f"{total_snow} in")
                    
                    if pricing_data['pricing_dets'][rd_select]['flat']:
                        col1.metric("Flat Rate for the Month", f"${plow_cost}")
                    else:
                        col1.metric("Total Plow Cost", f"${plow_cost}")
                        

                    col2.metric("Est Salt", f"${salt_cost}")

                    blank() 
                    table = st.dataframe(snow_dataframe,1000)
                    download = snow_dataframe
                else:
                    blank()
                    table =st.dataframe(data,1000)
                    download = data

                st.download_button(
                    label='Download data',
                    data=convert_df(download),
                    file_name=f'{rd_select}_{str(start_date)}_{str(end_date)}_weather_data.csv',
                    mime='text/csv'
                    )
                vendor = pricing_data['pricing_dets'][rd_select]['vendor']
                notes = pricing_data['pricing_dets'][rd_select]['notes']
                st.markdown(f"The vendor is {vendor}.")
                st.markdown(f"Additional Notes: {notes}.")

            else: 
                st.error("Invalid Password") 
                st.markdown("Contact Holly if you're having password issues")


if selected == "Snowfall Summary":
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
        
        element_keys = {'snow': 'snowfall_sum', 'rain': 'rain_sum', 'high temp': 'temperature_2m_max', 'low temp': 'temperature_2m_min', 'hours of precipitation': 'precipitation_hours'}

         # ----- SELECT RD -----    
        rd_data = load_rd_data(exclude_region=['South'])
        rd_values = rd_data['rds'].copy()
        rd_values.insert(0,'All')
        rd_values.insert(1, 'North')
        rd_values.insert(2, 'Central')
        rd_select = col2.multiselect("Select All, a Region, or multiple RDs:", rd_values, key=str)

        if 'All' in rd_select:
            rd_select = rd_data['rds']
        elif rd_select == ['North'] :
            rd_select = rd_data['north_rds']
        elif rd_select == ['Central']:
            rd_select = rd_data['central_rds']
        
        # -----INPUT PASSWORD-----
        col4, col5, col6 = st.columns(3)
        pc_password = col4.text_input("Password")  
        note = col5.markdown("Note: API calls may take some time depending on # RDs selected and date range.")

        submitted = st.form_submit_button("Submit")
    
    if submitted:  
        
        password_valid = password_authenticate(pc_password) 
        
        if password_valid:  
            st.success('Valid Password', icon="❄️")
            
            with st.spinner("Calculating Weather..."):
                weather = all_weather(start_date, end_date, rd_select) 
                # st.write(weather)
                df = aggregate(pricing_data, rd_select, weather) 
                # st.write(df)

                chart_data = df.loc[df['total cost'] != 0, ['RD', 'total cost', 'days over inch']]


                bars = alt.Chart(chart_data).mark_bar().encode(
                    x=alt.X('total cost:Q', axis=alt.Axis(title='Total Cost')),
                    y=alt.Y('RD:N', sort='-x'),
                    color = alt.Color('days over inch', scale=alt.Scale(scheme='tealblues'))
                )
                text = bars.mark_text(
                    align='left',
                    baseline='middle',
                    dx=3
                ).encode(
                    text = 'total cost:Q'
                )
                if len(rd_select) < 25:
                    chart = (bars).properties()
                else: 
                    chart = (bars).properties(height = 700)
                st.altair_chart(chart, use_container_width=True)

                table = st.dataframe(df,1000)
                download = df 

                st.download_button(
                    label='Download data',
                    data=convert_df(download),
                    file_name=f'{str(start_date)}_{str(end_date)}_plow_data.csv',
                    mime='text/csv'
                    )
        else: 
            st.error("Invalid Password") 
            st.markdown("Contact Holly if you're having password issues")

