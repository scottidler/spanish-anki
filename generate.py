#!/bin/env python3

import os
import argparse
import genanki

from ruamel.yaml import YAML

def load_yaml_file(file_path):
    yaml = YAML(typ='safe')
    with open(file_path, 'r', encoding='utf-8') as file:
        return yaml.load(file)

def create_anki_card(front, back, model):
    return genanki.Note(
        model=model,
        fields=[front, back]
    )

def process_yaml_file(file_path, deck, model):
    data = load_yaml_file(file_path)
    for entry in data:
        spanish_word = entry['hwi']['hw']
        english_meaning = "; ".join(entry.get('shortdef', []))
        front = f"{spanish_word}"
        back = f"{english_meaning}"
        deck.add_note(create_anki_card(front, back, model))

def process_directory(path, deck, model):
    for root, dirs, files in os.walk(path):
        for file in files:
            if file.endswith('.yml'):
                process_yaml_file(os.path.join(root, file), deck, model)

def main(args):
    deck_id = 123456789
    deck = genanki.Deck(deck_id, args.deck_name)
    model = genanki.Model(
        1607392319,
        'Simple Model',
        fields=[
            {'name': 'Question'},
            {'name': 'Answer'},
        ],
        templates=[
            {
                'name': 'Card 1',
                'qfmt': '{{Question}}',
                'afmt': '{{FrontSide}}<hr id="answer">{{Answer}}',
            },
        ])

    for item in args.paths:
        if os.path.isdir(item):
            process_directory(item, deck, model)
        elif os.path.isfile(item) and item.endswith('.yml'):
            process_yaml_file(item, deck, model)

    deck.write_to_file(args.output_file)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create Anki cards from YAML files")
    parser.add_argument(
        'paths',
        metavar='[YML..]',
        nargs='+',
        help='Paths to YAML files or directories containing YAML files')
    parser.add_argument(
        '-n',
        '--deck-name',
        metavar='NAME',
        default='Spanish Infinitives',
        help='default="%(default)s"; Name of the Anki deck')
    parser.add_argument(
        '-f',
        '--output-file',
        metavar='FILE',
        default='spanish_infinitives.apkg',
        help='default="%(default)s"; Output APKG file')
    args = parser.parse_args()
    main(args)

