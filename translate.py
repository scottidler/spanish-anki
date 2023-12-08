#!/bin/env python3

import os
import sys
import requests
import yaml  # Make sure to install PyYAML

MWD_API_KEY = os.environ.get('MWD_API_KEY')

def translate_word(word, api_key):
    url = f'https://dictionaryapi.com/api/v3/references/spanish/json/{word}?key={api_key}'
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        return f"Error: {response.status_code}"

def save_as_yaml(data, filename, path='verbs'):
    with open(os.path.join(path, filename), 'w') as file:
        yaml.dump(data, file)

def main(args):
    if not MWD_API_KEY:
        print("Error: MWD_API_KEY environment variable not set.")
        sys.exit(1)

    for word in args:
        translation = translate_word(word, MWD_API_KEY)
        filename = f'{word}.yml'
        save_as_yaml(translation, filename)
        print(f'{filename}')

if __name__ == "__main__":
    main(sys.argv[1:])

