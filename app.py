from flask import Flask, render_template, request
import numpy as np
import requests
import sys
print(sys.path)
from datetime import datetime, timedelta

app = Flask(__name__)

def get_historical_weather(latitude, longitude):
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": "precipitation,wind_speed_10m,temperature_2m",
        "timezone": "America/New_York"
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        if "hourly" in data:
            hourly_data = data["hourly"]
            precipitation = np.mean(hourly_data['precipitation'])
            wind_speed = np.mean(hourly_data['wind_speed_10m'])
            temperature = np.mean(hourly_data['temperature_2m'])
            return precipitation, wind_speed, temperature
    except requests.RequestException as e:
        print(f"Error fetching weather data: {e}")
    return None, None, None

def convert_to_fahrenheit(celsius):
    return (celsius * 9/5) + 32

def calculate_score(precipitation, wind_speed, temperature_fahrenheit, altitude):
    precip_score = 100 if precipitation == 0 else 80 if precipitation < 0.1 else 60 if precipitation < 0.5 else 20
    wind_score = 100 if wind_speed < 5 else 70 if wind_speed < 15 else 30
    temp_score = 100 if 60 <= temperature_fahrenheit <= 80 else 70 if 50 <= temperature_fahrenheit < 60 or 80 < temperature_fahrenheit <= 90 else 40
    altitude_score = 100 if altitude < 5000 else 70 if 5000 <= altitude < 10000 else 50
    avg_score = (precip_score + wind_score + temp_score + altitude_score) / 4
    return avg_score

def convert_time_to_value(time_str):
    time_obj = datetime.strptime(time_str, "%I:%M %p")
    return 0 if time_obj.hour < 12 else 1

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        latitude = float(request.form["latitude"])
        longitude = float(request.form["longitude"])
        start_date = request.form["start_date"]
        end_date = request.form["end_date"]
        start_time = request.form["start_time"]
        end_time = request.form["end_time"]
        target_altitude = float(request.form["altitude"])

        start_time_value = convert_time_to_value(start_time)
        end_time_value = convert_time_to_value(end_time)

        current_date = datetime.strptime(start_date, "%m-%d-%Y")
        end_date = datetime.strptime(end_date, "%m-%d-%Y")

        total_precipitation = 0
        total_wind_speed = 0
        total_temperature = 0
        total_scores = 0
        valid_days_count = 0

        while current_date <= end_date:
            precipitation, wind_speed, temperature = get_historical_weather(latitude, longitude)
            if precipitation is not None and wind_speed is not None and temperature is not None:
                temperature_fahrenheit = convert_to_fahrenheit(temperature)
                score = calculate_score(precipitation, wind_speed, temperature_fahrenheit, target_altitude)

                total_precipitation += precipitation
                total_wind_speed += wind_speed
                total_temperature += temperature
                total_scores += score
                valid_days_count += 1

            current_date += timedelta(days=1)

        if valid_days_count > 0:
            avg_precipitation = total_precipitation / valid_days_count
            avg_wind_speed = total_wind_speed / valid_days_count
            avg_temperature = total_temperature / valid_days_count
            avg_score = total_scores / valid_days_count
            result = {
                "avg_precipitation": avg_precipitation,
                "avg_wind_speed": avg_wind_speed,
                "avg_temperature": convert_to_fahrenheit(avg_temperature),
                "avg_score": avg_score,
                "target_altitude": target_altitude,
                "start_time_value": start_time_value,
                "end_time_value": end_time_value
            }
        else:
            result = None

        return render_template("index.html", result=result)

    return render_template("index.html", result=None)

if __name__ == "__main__":
    app.run(debug=True)
