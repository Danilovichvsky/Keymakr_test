import json
from fuzzywuzzy import process
from geopy.geocoders import Nominatim
import pycountry
import country_converter as coco


def normalize_city_name(city):
    known_cities = ["Kyiv", "London", "New York", "Tokyo", "Lviv"]
    matched_city, score = process.extractOne(city, known_cities)
    if score > 80:
        print("співпало з",matched_city)
        return matched_city
    else:
        print("Не має")
        return None


def get_country(city):
    geolocator = Nominatim(user_agent="test_work")
    location = geolocator.geocode(city)
    country = location.raw.get("display_name")
    country = country.split()[1]
    print(city, country)
    country_en = coco.convert(names=country, to="name_short", not_found=None)
    print(country_en)

    return country


def get_continent_by_country(country_name):
    # Конвертируем название страны в континент

    continent = coco.convert(names=country_name, to='continent')
    return continent if continent else "Unknown"

def main():
    city = "Kyiv"
    correct_city = normalize_city_name(city)
    country = get_country(correct_city)
    region = get_continent_by_country(country)
    print(region)

