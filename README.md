
# Markup to Ankicard AI

A single-file python CL application that aims to use a .md, .txt or any text-only file as input, and uses the openrouter.ai API and a LLM to automatically create Anki Cards and add them to the Anki app.



## Usage/Examples

```cmd
python main.py /Obsidian/test.md
```



## ⚠ Warning
The project was designed for an Anki-Instance running in German on a Windows machine. It should but may not work on other machines. To make it work for Anki-Instances in other languages, you will have to translate the Fields inside the AnkiConnect API requests. You will also have to translate the prompt that is given to the LLM. If you have done so, feel free to contribute.
## Installation

1. Clone this repo.
2. Install the requirements

```cmd
pip install requirements.txt
```

3. Install Anki, and also install the AnkiConnect plugin. 
A guide can be found here:

<https://foosoft.net/projects/anki-connect/index.html#graphical-actions>

Big thanks to Alex Yatskov for creating this awesome plugin.

4. Create an account <https://openrouter.ai> and create a new API key at <https://openrouter.ai/settings/keys>

⚠ I _highly_ recommend that you set a limit at only a few dollars, as I can and will not be the one in charge if this script starts making thousands API calls for no reason and you go bankrupt.

If you want to use another API to access your LLMs, you will have to implement this yourself. Feel free to contribute!

5. The script uses environmental Variables. You can either modify the defaults inside the script or (e.g. because you want to create a docker container) you can set these whilst before the start of your program.

```python
OPENROUTERAI_API_KEY = os.environ.get('OPENROUTERAI_API_KEY', 'sk-or-v1-XXXXX')
ANKICONNECT_API_URL = os.environ.get('ANKICONNECT_URL', 'http://127.0.0.1:8765')
OPENROUTERAI_API_URL = os.environ.get('OPENROUTERAI_API_URL', "https://openrouter.ai/api/v1/chat/completions")
LOCAL_PATH_TO_ANKIEXE = os.environ.get('LOCAL_PATH_TO_ANKIEXE', r'C:\Users\{USER}\AppData\Local\Programs\Anki\anki.exe')
```

set OPENROUTERAI_API_KEY to the key your Openrouter api key.
You usually won't have to change the ANKICONNECT_URL.
The OPENROUTERAI_API_URL stays unchanged as well.
LOCAL_PATH_TO_ANKIEXE must be modified. Change {USER} to your Windows Username. 
If Anki is installed at another Path, you can easily find that out on Windows.
Start a PowerShell instance.
```Powershell
get-StartApps
```

6. You're good to go. Start the script by:
```cmd
python main.py C:\Path\To\File\to\Convert.md


