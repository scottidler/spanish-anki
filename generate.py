#!/bin/env python3

import os
import argparse
import genanki
import time

def load_flat_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read().strip()

def create_anki_card(front, back, model):
    return genanki.Note(
        model=model,
        fields=[front, back]
    )

def process_flat_file(file_path, deck, model):
    file_name = os.path.splitext(os.path.basename(file_path))[0]  # Spanish verb is file name
    english_meaning = load_flat_file(file_path)
    front = f"{file_name}"
    back = f"{english_meaning}"
    deck.add_note(create_anki_card(front, back, model))

def process_directory(path, deck, model):
    for root, dirs, files in os.walk(path):
        for file in files:
            process_flat_file(os.path.join(root, file), deck, model)

def main(args):
    # Use current timestamp as deck_id
    deck_id = int(time.time())
    deck = genanki.Deck(deck_id, args.deck_name)
    model = genanki.Model(
        int(time.time() * 1000),  # Unique model ID based on current timestamp
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
        elif os.path.isfile(item):
            process_flat_file(item, deck, model)

    deck.write_to_file(args.output_file)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create Anki cards from flat files")
    parser.add_argument(
        'paths',
        metavar='[FILE..]',
        nargs='+',
        help='Paths to flat files or directories containing flat files')
    parser.add_argument(
        '-n',
        '--deck-name',
        metavar='NAME',
        default='Spanish Infinitives',
        help='Name of the Anki deck')
    parser.add_argument(
        '-f',
        '--output-file',
        metavar='FILE',
        default='spanish_infinitives.apkg',
        help='Output APKG file')
    args = parser.parse_args()
    main(args)

