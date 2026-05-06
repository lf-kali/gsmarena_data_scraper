import utils.file_routines as frt
import json
import requests

BASE_URL = 'http://localhost:3000/'

JWT_TOKEN = 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJrYWxpQGZyYW5jYS5jb20iLCJpYXQiOjE3NzY1MjQxMDIsImV4cCI6MTc3NjU1MjkwMn0.9SQ7HMq6HvIstwUG1i7l2K6kKJgtd9tgRkvWVL8Tu8k'

HEADERS = {'Authorization': JWT_TOKEN}

BRAND_DATA_DIR = f'./output/brands'

brand_data_file_search = frt.FileSearch(BRAND_DATA_DIR)

brand_data_file_search.run()

brand_data_files = brand_data_file_search.get_results()

def get_digit_index(name: str) -> str:
    for i, c in enumerate(name):
        if c.isdigit():
            return i
        
def parse_brand_name(name: str) -> str:
    raw_brand_name = name
    digitIndex = get_digit_index(raw_brand_name)
    brand_name = raw_brand_name[:digitIndex]
    return brand_name

for brand_file in brand_data_files:
    if isinstance(brand_file, frt.Arquivo):
        with open(brand_file.caminho, 'r', encoding='utf-8') as f:
            data = json.load(f)
            brand_name = parse_brand_name(data["brand"]["name"])
            print(f'\nCADASTRANDO MARCA {brand_name}\n')
            brand_response = requests.post(F'{BASE_URL}/cellphone-brands/new?returnBrandOnExisting=true', json={'name': brand_name}, headers=HEADERS)
            brand_json = None
            brand_id = None
            if brand_response.ok:
                brand_json = brand_response.json()
                print('\n', brand_json, '\n')
                brand_id = brand_json["id"]
            else:
                brand_response.raise_for_status()
            
            model_names = [device["name"] for device in data["devices"]]
            for model_name in model_names:
                print(f'CADASTRANDO MODELO {model_name}')
                model_response = requests.post(f'{BASE_URL}/cellphone-models/new', json={'name': model_name, 'brandId': brand_id}, headers=HEADERS)
                if not model_response.ok:
                    if model_response.status_code == 406:
                        print(f'\nMODELO "{model_name}" JÁ EXISTE NA MARCA "{brand_name}", PRÓXIMO MODELO...\n')
                        continue
                    else:
                        model_response.raise_for_status()
                print('\n', model_response.json(), '\n')

