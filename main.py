import click
from InquirerPy import prompt
import io
import requests
import json
from time import sleep
import os
import re


OPENROUTERAI_API_KEY = os.environ.get('OPENROUTERAI_API_KEY', 'sk-or-v1-XXXXX')
ANKICONNECT_API_URL = os.environ.get('ANKICONNECT_URL', 'http://127.0.0.1:8765')
OPENROUTERAI_API_URL = os.environ.get('OPENROUTERAI_API_URL', "https://openrouter.ai/api/v1/chat/completions")
LOCAL_PATH_TO_ANKIEXE = os.environ.get('LOCAL_PATH_TO_ANKIEXE', r'C:\Users\fabik\AppData\Local\Programs\Anki\anki.exe')

MODELS: dict[str, float] = {
    'nousresearch/hermes-3-llama-3.1-405b:free': 0.0,
    'mistralai/pixtral-12b:free': 0.0,
    'openai/chatgpt-4o-latest': 0.000005,
    'openai/gpt-4-turbo': 0.000010
}

from itertools import cycle
from shutil import get_terminal_size
from threading import Thread


class Loader:
    def __init__(self, desc="Loading...", end="", timeout=1000):
        """
        A loader-like context manager

        Args:
            desc (str, optional): The loader's description. Defaults to "Loading...".
            end (str, optional): Final print. Defaults to "Done!".
            timeout (float, optional): Sleep time between prints. Defaults to 0.1.
        """
        self.desc = desc
        self.end = end
        self.timeout = timeout

        self._thread = Thread(target=self._animate, daemon=True)
        self.steps = ["⢿", "⣻", "⣽", "⣾", "⣷", "⣯", "⣟", "⡿"]
        self.done = False

    def start(self):
        self._thread.start()
        return self

    def _animate(self):
        for c in cycle(self.steps):
            if self.done:
                break
            print(f"\r{self.desc} {c}", flush=True, end="")
            sleep(self.timeout)

    def __enter__(self):
        self.start()

    def stop(self):
        self.done = True
        cols = get_terminal_size((80, 20)).columns
        print("\r" + " " * cols, end="", flush=True)
        print(f"\r{self.end}", flush=True)

    def __exit__(self, exc_type, exc_value, tb):
        self.stop()

    # Thanks to https://stackoverflow.com/questions/22029562/python-how-to-make-simple-animated-loading-while-process-is-running



@click.command()
@click.argument("file", type=click.File("rb"))
def cli(file: io.BufferedReader):
    markup_text: str = file.read().decode()

    selected_model: str = prompt([{
        'type': 'list',
        'name': 'model',
        'message': 'Choose a model:',
        'choices': list(MODELS.keys()),

    }])['model']

    click.echo("Contacting Openrouter.ai. Waiting for a response from the selected model")

    with Loader("This might take a few moments..."):
        response, tokens_used = handle_api_request(selected_model, markup_text)

    click.echo("Answer received:\n\n\33[33m" +
               '\n'.join(['\t' + line for line in response.splitlines()]) +
               '\33[0m' + '\n'*2
               )

    click.echo(f"Tokens used: \33[35m{tokens_used}\33[0m for a total price of \33[35m{tokens_used*MODELS[selected_model]}$ \33[0m\n")

    click.echo("Converting model response to Anki Cards")
    qa_pairs, clozes = convert_aiansw_to_ankicard(response)

    click.echo(f"found \33[35m{len(qa_pairs)}\33[0m QA pairs and \33[35m{len(clozes)}\33[0m clozes: ")
    click.echo("QA-Pairs:")
    for pair in qa_pairs:
        click.echo("QUESTION:")
        click.echo('\33[32m' + '\n'.join(['\t' + line for line in pair[0].splitlines()]) + '\33[0m')

        click.echo("\n\nANSWER:")
        click.echo('\33[33m' + '\n'.join(['\t' + line for line in pair[1].splitlines()]) + '\33[0m')

    click.echo("\n\nClozes:")
    for cloze in clozes:
        click.echo("CLOZE:")
        click.echo('\33[33m' + '\n'.join(['\t' + line for line in cloze.splitlines()]) + '\33[0m')

    click.echo("\n\n")

    user_confirmation: bool = prompt([{
        'type': 'confirm',
        'name': 'confirm',
        'message': 'Do you want to continue?'
    }])['confirm']
    if not user_confirmation:
        return

    click.echo("Starting Anki to open the local API server (AnkiConnect)" + '\n'*5 +'\33[30m')

    os.system(rf'start "Anki" cmd /c "{LOCAL_PATH_TO_ANKIEXE}"')
    sleep(5)
    click.echo('\33[0m')

    deck_names: list[str] = get_deck_names()

    selected_deck_name: str = prompt([{
        'type': 'list',
        'name': 'deck_name',
        'message': 'Choose a deck name:',
        'choices': deck_names,
    }])['deck_name']


    click.echo("Adding these to Anki")
    note_ids = create_notes(qa_pairs, clozes, selected_deck_name)

    click.echo("Cards were added to anki.")

    open_in_anki()



def create_notes(qa_pairs, clozes, deck_name) -> tuple[bool, list[int, ]]:
    notes_list = [{
        "deckName": deck_name,
        "modelName": "Einfach",
        "fields": {
            "Vorderseite": question,
            "Rückseite": answer
        },
        "tags": ["AIgenerated", ]
    } for question, answer in qa_pairs]


    notes_list += [{
        "deckName": deck_name,
        "modelName": "Lückentext",
        "fields": {
            "Text": text,
            "Rückseite Extra": ""
        },
        "tags": ["AIgenerated", ]
    } for text in clozes]

    response = requests.get(
        url=ANKICONNECT_API_URL,
        data=json.dumps({
            "action": "addNotes",
            "version": 6,
            "params": {"notes": notes_list}
        })
    )

    assert response.status_code == 200 and response.ok and response.json()['error'] is None
    return True, response.json()['result']

def open_in_anki():
    response = requests.get(
        url=ANKICONNECT_API_URL,
        data=json.dumps({
            "action": "guiBrowse",
            "version": 6,
            "params": {
                "query": "added:1",
            }
        })
    )

def convert_aiansw_to_ankicard(answer: str):
    qa_blocks = re.search(r'<QA>(.*?)<\/QA>', answer, flags=re.DOTALL)

    qa_pairs: list[tuple[str, str]] = []
    for qa_block in qa_blocks.groups():
        qa_block = qa_block.replace('<QA>',  '')
        qa_block = qa_block.replace('</QA>', '')
        qa_question: str = qa_block.split('[Q]:')[1].split('[A]:')[0].strip()
        qa_answer:   str = qa_block.split('[Q]:')[1].split('[A]:')[1].strip()
        qa_pairs.append((qa_question, qa_answer))

    cloze_blocks = re.search(r'<Cloze>(.*?)<\/Cloze>', answer, flags=re.DOTALL)
    clozes: list[str] = []
    for cloze_block in cloze_blocks.groups():
        cloze_block = cloze_block.replace('<Cloze>', '')
        cloze_block = cloze_block.replace('</Cloze>', '')
        cloze_block = cloze_block.replace('{', '{{')
        cloze_block = cloze_block.replace('}', '}}')
        cloze_block = cloze_block.replace(':', '::')
        cloze_block = cloze_block.replace('"', '"')
        cloze_block = cloze_block.strip()
        clozes.append(cloze_block)

    return qa_pairs, clozes



def get_deck_names() -> list[str]:
    response = requests.get(
        url=ANKICONNECT_API_URL,
        data=json.dumps({
            "action": "deckNames",
            "version": 6
        })
    )

    if response.status_code == 200 and response.ok:
        deck_names = response.json()['result']
        return deck_names





def handle_api_request(model: str, markup_text: str):
    prompt_text = """
Dir wird eine Markup-Datei überreicht, welche eine Mitschrift von einer Vorlesung an der Universität ist. Deine Aufgabe ist es, daraus 1-5 Lernkarten für das Lernprogramm Anki zu erstellen. 
Dabei kann sowohl der Frage-Antwort Stil, als auch der sog. Cloze-Stil (Lückentext) verwendet werden. 
Es ist deine Aufgabe zu entscheiden, was besser passt. Die Stils können sich dabei auch von Karte zu Karte unterscheiden.
Benutze Emojis, wenn hilfreich, aber nicht im Übermaß.

Formatiere wie folgt:
<QA>
[Q]: "Schreibe hierhin die Frage?" 
[A]: "
- Lösung
- in Stichpunkten 🧷
"
</QA>

<Cloze> 
"Dies ist eine {c1:Cloze-Karte}. Die {c1:Clozies} werden durchnummiert 🔢. 
Mehrere {c2: Lücken} können auch einer {c2:Antwort} zugeordnet werden, indem man ihnen die gleich Nummer nach dem c gibt. (c1, c1, c1).
 Ist das nicht {c3:toll 😀}?"
</Cloze>
"""

    response = requests.post(
        url=OPENROUTERAI_API_URL,
        headers={
            "Authorization": f"Bearer {OPENROUTERAI_API_KEY}",
        },
        data=json.dumps({
            "model": model,  # Optional
            "prompt": prompt_text + '---\n\n\n' + markup_text
        })
    )

    if response.status_code == 200 and response.ok:
        result: dict = response.json()
        answer: str = result['choices'][0]['text']
        tokens_used: int = result['usage']['total_tokens']

    return answer, tokens_used


if __name__ == "__main__":
    cli()

