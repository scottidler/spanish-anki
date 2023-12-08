#!/bin/env python3

import sys
import re
import os
import argparse

import pdfplumber
import hashlib
import json
import multiprocessing
import spacy_stanza
import stanza

from concurrent.futures import ProcessPoolExecutor
from ruamel.yaml import YAML
from collections import Counter
from functools import reduce

yaml = YAML(typ='rt')

# Constants
INFINITIVE_ENDINGS = ['ar', 'er', 'ir', 'ír']
REFLEXIVE_INFINTIVE_ENDINGS = ['arse', 'erse', 'irse', 'írse']
REFLEXIVE_ENDINGS = ['se', 'sela', 'selas', 'selo', 'selos', 'sé', 'me', 'te', 'nos', 'os']
GERUND_ENDINGS = ['ando', 'iendo']

class OrderedDumper(YAML):
    def represent_dict_order(self, data):
        return self.represent_dict(data.items())

def write_cache(cache_dir, filename, data):
    if filename.endswith('.json'):
        cache_file = os.path.join(cache_dir, filename)
        with open(cache_file, 'w') as file:
            json.dump(data, file, indent=2)
    else:
        cache_file = os.path.join(cache_dir, filename)
        with open(cache_file, 'w') as file:
            file.write(data)

def read_cache(cache_dir, filename):
    if filename.endswith('.json'):
        cache_file = os.path.join(cache_dir, filename)
        if os.path.exists(cache_file):
            with open(cache_file, 'r') as file:
                return json.load(file)
    else:
        cache_file = os.path.join(cache_dir, filename)
        if os.path.exists(cache_file):
            with open(cache_file, 'r') as file:
                return file.read()
    return None


def generate_cache_dir(pdf_path):
    with open(pdf_path, 'rb') as f:
        file_hash = hashlib.sha1(f.read()).hexdigest()
    cache_dir = f".{os.path.splitext(pdf_path)[0]}"
    hash_dir = os.path.join(cache_dir, file_hash)
    os.makedirs(hash_dir, exist_ok=True)
    return hash_dir

def load_word_list(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            words = set(line.strip() for line in file)
            return words
    return set()

def load_word_mappings(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            mappings = yaml.load(file)
            return mappings
    return {}

def preprocess_dialogue(text):
    text = re.sub(r' -', ' "', text)
    text = re.sub(r'-', '"', text)
    return text

def longest_common_substring(strings):
    def lcs(S, T):
        m, n = len(S), len(T)
        L = [[0] * (n+1) for i in range(m+1)]
        lcs_len, lcs_end = 0, 0
        for i in range(m):
            for j in range(n):
                if S[i] == T[j]:
                    L[i+1][j+1] = L[i][j] + 1
                    if L[i+1][j+1] > lcs_len:
                        lcs_len = L[i+1][j+1]
                        lcs_end = i + 1
                else:
                    L[i+1][j+1] = 0
        return S[lcs_end - lcs_len: lcs_end]

    return reduce(lcs, strings) if strings else None

def analyze_initial_pages(pdf_path, num_pages=20):
    first_lines, last_lines = [], []

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages[:num_pages]:
            page_text = page.extract_text()
            if page_text:
                lines = page_text.split('\n')
                if lines:
                    first_lines.append(lines[0])
                    last_lines.append(lines[-1])

    header = longest_common_substring(first_lines)
    footer = longest_common_substring(last_lines)

    print(f'header="{header}"')
    print(f'footer="{footer}"')

    header_pattern = re.compile(re.escape(header)) if header else None
    footer_pattern = re.compile(re.escape(footer) + r'\s*\d+\s*de\s*\d+') if footer else None

    return header_pattern, footer_pattern

def extract_text_from_pdf(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        page_numbers = range(len(pdf.pages))
        with ProcessPoolExecutor() as executor:
            texts = executor.map(extract_text_from_page, [pdf_path]*len(pdf.pages), page_numbers)
        full_text = "".join(texts)
        return full_text

def extract_text_from_page(pdf_path, page_number):
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[page_number]
        if page.extract_text():
            return page.extract_text() + "\n"
    return ""

def extract_text_from_pdf(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        page_numbers = range(len(pdf.pages))
        with ProcessPoolExecutor() as executor:
            texts = executor.map(extract_text_from_page, [pdf_path]*len(pdf.pages), page_numbers)
        return ''.join(texts)

def extract_text_from_page(pdf_path, page_number):
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[page_number]
        return page.extract_text() + "\n" if page.extract_text() else ""

def extract_sentences_from_text(text, header, footer):
    nlp = stanza.Pipeline('es', processors='tokenize')
    doc = nlp(text)
    return [
        preprocess_dialogue(clean_sentence(sentence.text.strip(), header, footer))
        for sentence
        in doc.sentences
    ]

def clean_sentence(sentence, header, footer):
    if header:
        print(f'applying header pattern="{header.pattern}" to sentence="{sentence}"')
        sentence = header.sub('', sentence)
    if footer:
        print(f'applying footer pattern="{footer.pattern}" to sentence="{sentence}"')
        sentence = footer.sub('', sentence)

    sentence = re.sub(r'-\s+', '', sentence)
    sentence = re.sub(r'(\w)([A-Z])', r'\1 \2', sentence)
    sentence = re.sub(r'[^\w\s-]', '', sentence)
    sentence = re.sub(r'\s+', ' ', sentence)
    return sentence.strip()

def add_reflexive_suffix(verb):
    if verb.endswith(tuple(INFINITIVE_ENDINGS)):
        return verb + 'se'
    return verb

def perform_and_cache_ner(sentences, cache_dir):
    ner_results = []
    for sentence in sentences:
        doc = nlp(sentence)
        for ent in doc.ents:
            ner_results.append({
                'text': ent.text,
                'start': ent.start_char,
                'end': ent.end_char,
                'label': ent.label_
            })
    ner_json = json.dumps(ner_results, indent=2)
    write_cache(cache_dir, 'ner.json', ner_json)
    return ner_results

def process_sentence(nlp, sentence, known_words, proper_nouns, mappings):
    words = Counter()
    verbs = Counter()
    errors = Counter()
    doc = nlp(sentence)

    for token in doc:
        if token.is_alpha:
            word_lower = token.text.lower()
            if word_lower in known_words or token.text in proper_nouns:
                continue
            elif token.pos_ == 'VERB':
                verb = token.lemma_.lower()
                next_token = doc[token.i + 1] if token.i + 1 < len(doc) else None
                if next_token and next_token.lower_ == 'se':
                    verb = add_reflexive_suffix(verb)
                elif ' ' in verb:
                    verb = add_reflexive_suffix(verb.split(' ')[0])
                if not verb.endswith(tuple(INFINITIVE_ENDINGS + REFLEXIVE_INFINTIVE_ENDINGS + GERUND_ENDINGS)):
                    if verb in mappings:
                        replacement = mappings[verb]
                        verbs[replacement] += 1
                    else:
                        errors[verb] += 1
                else:
                    verbs[verb] += 1
            else:
                word = word_lower
                words[word] += 1

    return words, verbs, errors

def sort_and_format(counter):
    return {word: count for word, count in sorted(counter.items(), key=lambda x: (-x[1], x[0]))}

def main(pdfs, clear_cache=False):
    known_words = load_word_list('known-words')
    proper_nouns = load_word_list('proper-nouns')
    mappings = load_word_mappings('mappings.yml')

    print(f'loaded: known={len(known_words)}, proper={len(proper_nouns)}, mappings={len(mappings)}')

    all_words = Counter()
    all_verbs = Counter()
    all_errors = Counter()

    for pdf in pdfs:
        cache_dir = generate_cache_dir(pdf)
        if clear_cache:
            print(f'clearing cache: {cache_dir}')
            os.system(f'rm -rf {cache_dir}/*')

        sentences = read_cache(cache_dir, 'sentences.txt')
        if sentences is None:
            text = extract_text_from_pdf(pdf)
            header, footer = analyze_initial_pages(pdf)
            sentences = extract_sentences_from_text(text, header, footer)
            write_cache(cache_dir, 'sentences.txt', "\n".join(sentences))
        else:
            sentences = sentences.split('\n')
        print('sentences processed and cached')

        nlp = spacy_stanza.load_pipeline('es', processors={
            'tokenize': 'ancora',
            'mwt': 'ancora',
            'pos': 'ancora_charlm',
            'lemma': 'ancora_nocharlm',
            'depparse': 'ancora_charlm'
        })
        for i, sentence in enumerate(sentences):
            print(f'{i}: {sentence}')
            words, verbs, errors = process_sentence(nlp, sentence, known_words, proper_nouns, mappings)
            all_words.update(words)
            all_verbs.update(verbs)
            all_errors.update(errors)

        sorted_words = sort_and_format(all_words)
        sorted_verbs = sort_and_format(all_verbs)
        sorted_errors = sort_and_format(all_errors)

        output = {
            "words": {"items": sorted_words, "count": len(sorted_words)},
            "verbs": {"items": sorted_verbs, "count": len(sorted_verbs)},
            "errors": {"items": sorted_errors, "count": len(sorted_errors)}
        }

        yaml = OrderedDumper(typ='unsafe', pure=True)
        yaml.default_flow_style = False
        yaml.Representer.add_representer(dict, OrderedDumper.represent_dict_order)

        output_file = os.path.splitext(pdf)[0] + '.yml'
        with open(output_file, 'w') as file:
            yaml.dump(output, file)


def parse_arguments():
    parser = argparse.ArgumentParser(description='Process PDF files and extract word frequency data.')
    parser.add_argument('pdfs', nargs='+', help='PDF file paths')
    parser.add_argument('-c', '--clear-cache', action='store_true', help='Clear the cache before processing')
    return parser.parse_args()

if __name__ == '__main__':
    args = parse_arguments()
    main(args.pdfs)
