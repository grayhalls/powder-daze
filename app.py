import streamlit as st
# from streamlit_option_menu import option_menu
import pandas as pd 
import numpy as np
import requests
import altair as alt
from helpers import *

#---------------SETTINGS--------------------
page_title = "Powder Daze"
page_icon = ":snowflake:"  #https://www.webfx.com/tools/emoji-cheat-sheet/
layout = "centered"
initial_sidebar_state="expanded"
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

st.sidebar.title('Powder Daze')  
# st.sidebar.caption(f"Routes last calculated for: **{st.session_state.get('last_update', 'N/A')}**")
nav = st.sidebar.radio("Navigate to section", [
    "Individual Store Breakdown", "Snowfall by District", "Uploads"
]) 

def password_authenticate(pwsd):

    if pwsd == st.secrets["ADMIN"]:
        return True

    if pwsd == st.secrets["PCs"]:
        return True

    else:
        return False  
st.sidebar.markdown('-----')
enter_password = st.sidebar.text_input("Password", type = 'password')

if password_authenticate(enter_password):
    st.session_state['valid_password'] = True
else: 
    st.warning("Enter Password to Access")
    st.session_state['valid_password'] = False

password = password_authenticate(enter_password)


if password == True:
    pricing_data = load_pricing_data()
    rd_data = load_rd_data(exclude_region=[1])
    salt_price_vec = np.vectorize(salt_price)

    # ----- FUNCTIONS -----

    def blank(): return st.write('') 

    def find_price(site, inch, pricing_data):
        if site not in pricing_data['pricing_dets']:
            print(f"Warning: Site '{site}' not found in pricing_data['pricing_dets'].")
            return 0
        
        site_data = pricing_data['pricing_dets'][site]

        if site_data['flat']:
            return site_data['flat_cost']
        else:
            inch_price = pricing_data['inch_pricing']
            # st.write(inch_price[site])
            if site in inch_price and str(inch) in inch_price[site]:
                return inch_price[site][str(inch)]
            else:
                print(f"Warning: No pricing found for {inch} inches at site '{site}'.")
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
        # print(weather_dict)
        if rd_select not in weather_dict:
            raise ValueError(f"rd_select {rd_select} not found in weather_dict")
        
        inches_snow = [math.floor(i) for i in weather_dict[rd_select].get('snow', [])]
        data = {'date': weather_dict[rd_select].get('date', []), 
                'snow': weather_dict[rd_select].get('snow', []), 
                'rain': weather_dict[rd_select].get('rain', []),
                'high temp': weather_dict[rd_select].get('high temp', []), 
                'low temp': weather_dict[rd_select].get('low temp', []), 
                'hours of precipitation': weather_dict[rd_select].get('hours of precipitation', [])}
        # st.write(data)
        # Calculate plow prices and estimated salt usage using vectorized functions
        vectorized_find_price = np.vectorize(find_price)
        plow_prices = np.where(np.array(inches_snow) < 1, 0, vectorized_find_price(rd_select, np.array(inches_snow), pricing_data))
        # st.write("Plow prices:", plow_prices)

        est_salt = np.where(plow_prices == 0, 0, salt_price(rd_select))
        # st.write("Estimated salt:", est_salt)

        # Add results to dictionary
        data['plow price'] = plow_prices.tolist()
        data['est salt'] = est_salt.tolist()
        # st.write("Data after calculations:", data)
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
            if location not in weather:
                continue
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
                results.append({'Store':location, 'plow cost': plow_cost, 
                                'days over inch': days_over_inch, 
                                'salt cost': salt_cost, 
                                'total cost': total_cost, 
                                'total snow': total_snow})

        return pd.DataFrame(results)



        # --- NAVIGATION MENU ---
    # selected = option_menu(
    #     menu_title=None,
    #     options=["Individual Store Breakdown", "Snowfall by District"],
    #     icons=["geo", "snow"],  # https://icons.getbootstrap.com/
    #     orientation="horizontal",
    #     )

    if nav == "Individual Store Breakdown":
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
            rd_select = col2.selectbox("Select a Store:", rd_data['stores'], key=str)
            
            element_keys = {'snow': 'snowfall_sum', 'rain': 'rain_sum', 'high temp': 'temperature_2m_max', 'low temp': 'temperature_2m_min', 'hours of precipitation': 'precipitation_hours'}
            elements = list(element_keys.keys())
            
            elements_select = col3.selectbox("Select weather data type:", elements)
            
            # -----INPUT PASSWORD-----
            col4, col5, col6 = st.columns(3)
            # pc_password = col4.text_input("Password", type="password") 
            snow = col6.checkbox('More Snow?')

            submitted = st.form_submit_button("Submit")
        
        if submitted:  
                
                # password_valid = password_authenticate(pc_password) 
                
                # if password_valid:  
                #     st.success("Valid Password", icon="❄️")
                if snow:
                    st.snow() 

                weather_data = grab_weather(start_date, end_date, rd_select, elements_select, rd_data)
                # st.write(weather_data)
                # new_data = {k: v for k, v in weather_data.values()}

                # Create a DataFrame from the new dictionary
                data = pd.DataFrame(weather_data[rd_select])
                # st.write(rd_select)
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
                    # st.write(pricing_data)
                    # st.write(chart_data)
                    if pricing_data['pricing_dets'][rd_select]['flat']:
                        snow_dataframe=snow_dataframe.drop(columns = ['plow price'])
                        days_over_inch = len(chart_data[chart_data['snow']>1])
                        # st.write('flat')
                        plow_cost = pricing_data['pricing_dets'][rd_select]['flat_cost']
                    else:
                        days_over_inch = len(snow_dataframe[snow_dataframe['plow price']>0])
                        # st.write(snow_dataframe)
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

                # else: 
                    # st.error("Invalid Password") 
                    # st.markdown("Contact Holly if you're having password issues")



    if nav == "Snowfall by District":
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
            rd_data = load_rd_data(exclude_region=[1])
            district_store_map = rd_data['district_store_map']
            districts = list(district_store_map.keys())
            
            selected_district = col2.selectbox("Select District:", ["All"] + districts)
            
            if selected_district == "All":
                rd_select = rd_data['stores']
            else:
                rd_select = district_store_map[selected_district]

            # -----INPUT PASSWORD-----
            # col4, col5, col6 = st.columns(3)
            # pc_password = col4.text_input("Password", type = 'password')  
            note = st.caption("Note: API calls may take some time depending on # stores selected and date range.")

            submitted = st.form_submit_button("Submit")
        
        if submitted:  
            
        #     password_valid = password_authenticate(pc_password) 
            
        #     if password_valid:  
        #         st.success('Valid Password', icon="❄️")
                # st.write(rd_select)
            with st.spinner("Calculating Weather and Estimated Costs..."):
                # st.write(rd_select)
                weather = all_weather(start_date, end_date, rd_select) 
                # st.write(weather)
                df = aggregate(pricing_data, rd_select, weather) 
                # st.write(df)

                chart_data = df.loc[df['total cost'] != 0, ['Store', 'total cost', 'days over inch']]


                bars = alt.Chart(chart_data).mark_bar().encode(
                    x=alt.X('total cost:Q', axis=alt.Axis(title='Total Cost')),
                    y=alt.Y('Store:N', sort='-x'),
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
            # else: 
                # st.error("Invalid Password") 
                # st.markdown("Contact Holly if you're having password issues")


    if nav == "Uploads":
        ## UPLOAD FILES TO S3
        st.header('Upload updated pricing or location info')
        # st.markdown('## Ops Promo Upload')
        st.markdown('File Descriptions: ')
        st.caption("""
            - **Location Info**: Contains individual store info such as code, latitude, longitude, district, and region.
            - **Snow Removal Pricing**: Contains pricing for individual stores depending on the contractor. Please include pricing by inches plowed or the monthly flat rate if applicable. Also, include the cost of salt if it is applied.
        """)

        file_mappings = {
            'Location Info': 'powder-daze/location_info.csv',
            'Snow Removal Pricing': 'powder-daze/snow_removal_pricing.csv',
        }

        blank()
        # Selection for the file to edit
        selection = st.selectbox('Select the file to download and edit:', list(file_mappings.keys()))

        # Read and display selected file
        file_path = file_mappings[selection]
        data = grab_s3_file(f = file_path, bucket = 'sroa-ops-files')
        original_columns = data.columns

        # Convert DataFrame to CSV for download
        csv = data.to_csv(index=False)
        st.download_button(label="Download Current File", data=csv, file_name=file_path.split('/')[-1], mime='text/csv')
        blank()
        # Upload modified file
        uploaded_file = st.file_uploader("Choose File to Upload")
        if uploaded_file is not None:
            # Assuming the file is in CSV format
            modified_data = pd.read_csv(uploaded_file)

           # Validate column names
            if list(modified_data.columns) == list(original_columns):
                # Save uploaded data back to S3
                if st.button('Upload New File'):
                    upload_file_to_s3(file_name=file_path, data=modified_data, bucket='sroa-ops-files')
                    st.success(f'{selection} updated successfully!')
            else:
                st.error('The uploaded file does not have the same column names as the original file.')


