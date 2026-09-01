# FlyPrice AI

FlyPrice AI is a full-stack flight price prediction web application that uses a pre-trained Random Forest Regression pipeline to estimate ticket prices from user travel details.

## Overview

The app allows a user to input airline, source and destination cities, departure and arrival times, stop count, class, duration, and days left. The backend validates the request, maps values to the exact model contract, calls the saved pipeline, and returns the predicted price in INR and an approximate JOD value.

## Features

- Responsive landing page and prediction experience
- Clean dashboard-style UI built with React and Tailwind CSS
- FastAPI backend for model inference
- Real prediction using the saved `random_forest_pipeline.pkl`
- Input validation and friendly error messaging
- Price display in INR and JOD
- Model loading at application startup instead of per request

## Machine Learning Model

The backend loads a pre-trained pipeline saved as `random_forest_pipeline.pkl`.

This pipeline includes:

- feature preprocessing
- categorical encoding for airline, flight, cities, times, stops, and class
- a trained Random Forest Regressor for price prediction

The app does not retrain the model. The exact feature names and category values must match the saved pipeline.

## Dataset

The model was trained on historical flight-price data. The specific source dataset is not bundled in this app, but the trained pipeline is included and used at runtime.

## Technologies

- Frontend: React, Tailwind CSS
- Backend: Python, FastAPI
- ML: scikit-learn, joblib, pandas
- Testing: pytest

## Project Structure

```text
flight-price-ai/
├── backend/
│   ├── main.py
│   ├── model/
│   │   └── random_forest_pipeline.pkl
│   ├── requirements.txt
│   └── tests/
│       └── test_predict.py
├── frontend/
│   ├── package.json
│   ├── package-lock.json
│   ├── public/
│   └── src/
├── README.md
└── .gitignore
```

## Installation

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Frontend

```bash
cd frontend
npm install
```

## Run the Backend

```bash
cd backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:

- http://localhost:8000
- POST /predict

## Run the Frontend

```bash
cd frontend
npm run dev -- --host 0.0.0.0 --port 5173
```

Open the frontend in the browser at:

- http://localhost:5173

## API Endpoint

### POST /predict

```json
{
  "airline": "Vistara",
  "flight": "UK-123",
  "source_city": "Delhi",
  "departure_time": "Morning",
  "stops": "one",
  "arrival_time": "Afternoon",
  "destination_city": "Mumbai",
  "class": "Economy",
  "duration": 5.5,
  "days_left": 20
}
```

### Example Response

```json
{
  "predicted_price_inr": 12500,
  "predicted_price_jod": 106.0
}
```

## Notes

- The backend loads the saved model once at startup.
- The frontend sends user-friendly values, and the backend maps them to the model’s exact required format.
- The prediction is an estimate and should not be treated as a guaranteed booking price.
