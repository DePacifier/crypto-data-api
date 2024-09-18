# Crypto Data API

Crypto Data API is a cloud-based API designed to collect, store, and provide comprehensive cryptocurrency data, including spot, futures, bidders, sentiment, and other key metrics from Binance. The API is built for deployment on the Deta Space cloud platform and offers extensive historical data in various granularities, from 1-minute intervals to weekly summaries.

## Features

- Collects over 50+ features of cryptocurrency data from Binance.
- Stores data in Google Sheets, organized by year and month.
- Provides two key API endpoints to retrieve historical data either by year or by month.
- Returns data in JSON format, ready to use for analysis.

## Table of Contents

- [Features](#features)
- [Deployment on Deta Space](#deployment-on-deta-space)
- [API Endpoints](#api-endpoints)
- [How to Use](#how-to-use)

## Deployment on Deta Space

This API is designed to be deployed on [Deta Space](https://deta.space). Follow these steps to deploy:

1. **Create a Deta Space Account**: You will need to create a free account on Deta Space.
2. **Set up Google Sheets Credentials**: 
   - Create Google Sheets API credentials using Google Cloud Platform (GCP).
   - Download the credentials file and provide the necessary details in the `.env` folder.
3. **Deploy to Deta Space**: Upload your project files and environment variables to Deta Space and deploy the application.

## API Endpoints

### 1. `/get_year_data`
   - **Description**: Retrieves cryptocurrency data for a specific year.
   - **Method**: `GET`
   - **Parameters**:
     - `year`: The year for which data is requested (e.g., 2023).
     - `symbol`: The cryptocurrency symbol (e.g., BTCUSDT).
   - **Response**: JSON object with the collected data.

### 2. `/get_month_data`
   - **Description**: Retrieves cryptocurrency data for a specific year and month.
   - **Method**: `GET`
   - **Parameters**:
     - `year`: The year for which data is requested (e.g., 2023).
     - `month`: The month for which data is requested (e.g., 05 for May).
     - `symbol`: The cryptocurrency symbol (e.g., BTCUSDT).
   - **Response**: JSON object with the collected data.

## How to Use

After deploying the API on Deta Space, you can access the endpoints by sending `GET` requests to the respective routes.

Example of a GET request to retrieve yearly data:

```bash
GET /get_year_data?year=2023&symbol=BTCUSDT
```

Example of a GET request to retrieve monthly data:

```bash
GET /get_month_data?year=2023&month=05&symbol=BTCUSDT
```

Both endpoints will return a JSON object containing the requested data.