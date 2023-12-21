#!/bin/env python3

import os
import sys
import requests
from ruamel.yaml import YAML
import argparse

MWD_API_KEY = os.environ.get('MWD_API_KEY')
LIBRETRANSLATE_URL = 'http://0.0.0.0:5000/translate'  # Adjust as needed
VALID_APIS = ('libre', 'merriam-webster')

def translate_word_merriam(word, api_key):
    url = f'https://dictionaryapi.com/api/v3/references/spanish/json/{word}?key={api_key}'
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if not data or 'shortDef' not in data[0] or not data[0]['shortDef']:
            return None  # No translation found
        return '; '.join(data[0]['shortDef'])
    else:
        return None

def translate_word_libre(word):
    body = {
        'q': word,
        'source': 'es',
        'target': 'en',
        'format': 'text',
        'api_key': ''  # Replace with your API key if you have one
    }
    headers = {'Content-Type': 'application/json'}
    response = requests.post(LIBRETRANSLATE_URL, json=body, headers=headers)
    if response.status_code == 200:
        data = response.json()
        translated_text = data.get('translatedText')
        if not translated_text or translated_text.lower() == word.lower():
            return None  # No valid translation or same as input word
        return translated_text
    else:
        return None

def save_as_flat_file(data, filename, path):
    os.makedirs(path, exist_ok=True)
    with open(os.path.join(path, filename), 'w') as file:
        file.write(data)

def save_as_yaml(data, filename, path):
    os.makedirs(path, exist_ok=True)
    yaml = YAML()
    yaml.indent(mapping=2, sequence=4, offset=2)
    with open(os.path.join(path, filename + '.yml'), 'w') as file:
        yaml.dump({'translation': data}, file)

def parse_arguments(args):
    parser = argparse.ArgumentParser(description='Translate words and save as file.')
    parser.add_argument('words', nargs='+', help='Words to translate')
    parser.add_argument('-o', '--output', default='output', help='Output directory')
    parser.add_argument('-a', '--api', choices=VALID_APIS, default='merriam-webster', help='API to use for translation')
    parser.add_argument('-y', '--yaml', action='store_true', help='Output in YAML format')
    return parser.parse_args(args)

def main(args):
    parsed_args = parse_arguments(args)

    if parsed_args.api == 'merriam-webster' and not MWD_API_KEY:
        print('Error: MWD_API_KEY environment variable not set.', file=sys.stderr)
        sys.exit(1)

    for word in parsed_args.words:
        if parsed_args.api == 'merriam-webster':
            translation = translate_word_merriam(word, MWD_API_KEY)
        elif parsed_args.api == 'libre':
            translation = translate_word_libre(word)
        else:
            print('Invalid API choice', file=sys.stderr)
            sys.exit(1)

        if translation:
            if parsed_args.yaml:
                save_as_yaml(translation, word, parsed_args.output)
                print(f'Translated {word} using {parsed_args.api}, saved in {word}.yml')
            else:
                save_as_flat_file(translation, word, parsed_args.output)
                print(f'Translated {word} using {parsed_args.api}, saved in {word}')
        else:
            print(f'No valid translation found for "{word}" using {parsed_args.api}.', file=sys.stderr)

if __name__ == '__main__':
    main(sys.argv[1:])

