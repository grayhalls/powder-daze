# Powder Daze Streamlit App

This Streamlit application helps visualize weather data and estimate snow removal costs for individual self-storage stores operated by SROA. 

## Features

- **Individual Store Breakdown:** Select a store and view detailed weather data and cost estimates.
- **Snowfall by District:** Visualize snowfall data aggregated by district.
- **Uploads:** Download and upload files for data manipulation.

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/grayhalls/powder-daze.git
   cd powder-daze
2. Create and activate a virtual environment on Windows:

    ```bash
    python -m venv venv
    .\venv\Scripts\activate
    pip install -r requirements.txt
3. Run the Streamlit app:

    ```bash
    streamlit run app.py

## Functions

### Main Sidebar
- **Title:** "Powder Daze"
- **Navigation:** Allows users to navigate between "Individual Store Breakdown", "Snowfall by District", and "Uploads".

### Weather and Pricing Data
- **`load_pricing_data()`**: Loads pricing data.
- **`load_rd_data()`**: Loads store data, excluding specified regions.
- **`salt_price()`**: Vectorized function to get salt prices.

### Data Processing
- **`grab_weather(start_date, end_date, rd_select, elements_select, rd_data)`**: Fetches weather data from Open-Meteo, an open source API.
- **`add_pricing(weather_dict, rd_select)`**: Adds estimated plow cost information to the weather data.
- **`all_weather(start_date, end_date, rds_select)`**: Aggregates weather data for multiple stores.
- **`aggregate(pricing_data, rd_select, weather)`**: Aggregates pricing and weather data to produce a summary.

### UI Components
- **Forms:** Users can select date ranges, stores, and weather data types.
- **Charts:** Uses Altair to create interactive bar charts.
- **Metrics:** Displays key metrics like plow days, total snowfall, plow cost, and estimated salt cost.
- **Dataframes:** Displays detailed data in tabular format.
- **Download Buttons:** Allows users to download the displayed data as CSV files.

### Uploads
Self-service portal to allow users to make changes to the store data and pricing data. CSV files are stored in AWS S3.
- **Location Info**: Contains individual store info such as code, latitude, longitude, district, and region.
- **Snow Removal Pricing**: Contains pricing for individual stores depending on the contractor. Please include pricing by inches plowed or the monthly flat rate if applicable. Also, include the cost of salt if it is applied.
