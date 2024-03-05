import os
import os.path
import glob
import requests
import yaml
import pyfiglet
from termcolor import colored

from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    
        
def printMotd():
    os.system('color') # windows patch
    print('Welcome to')
    print(colored(pyfiglet.figlet_format("LLM Fuzzer", font='starwars', justify='left', width=180), 'green'))   
    print(colored('### Warning: Use this LLM Fuzzer on your own LLM integrations!', 'red'))
    print(colored('### Do not attempt to harm or scan other LLMs!', 'red'))
    print()

class LLMfuzzer:
 
    def __init__(self, configPath):
        self.configPath = configPath
        print('! Loading config from: ' + configPath)
        
        # Check if config file exists
        if (not os.path.isfile(self.configPath)):
            raise Exception('Can''t read config file!')
            
        # Load YAML config
        self._loadConfig()

    def _loadConfig(self):
        with open(self.configPath, "r") as stream:
            try:
                self.config = yaml.safe_load(stream)                
            except yaml.YAMLError as exc:
                raise Exception('Can''t read config file!')
        
    def checkConnection(self):
        try:
            response = requests.post(
                self.config['Connection']['Url'],
                headers= self.config['Connection']['Headers'],
                cookies= self.config['Connection']['Cookies'],
                proxies= self.config['Resources']['Proxies'],
                json= self.config['Connection']['Initial-POST-Body'],
                verify=False
            )
            
            if response.status_code != 200:
                raise Exception('Connection error, can''t continue evaluation.')
            print(colored('Success connecting to LLM via API', 'green'))
        except requests.exceptions.RequestException as e:
            raise Exception('Connection error, can''t continue evaluation.')
        
        
    def runAttack(self, path):
        attackConfig = ''
        with open(path, "r") as stream:
            try:
                attackConfig = yaml.safe_load(stream)                
            except yaml.YAMLError as exc:
                raise Exception('Can''t read attack file!')
        print(colored('Attack "' + attackConfig['Name'] + '" loaded. Running.', 'yellow'))
        
        for test in attackConfig['Tests']:
            try:
                # Set the initial request body then update the query attribute
                self.config['Connection']['Initial-POST-Body'][self.config['Connection']['Query-Attribute']] = test['Query'].replace('*collaborator-url', self.config['Resources']['Collaborator-URL'])
                response = requests.post(
                    self.config['Connection']['Url'],
                    headers= self.config['Connection']['Headers'],
                    cookies= self.config['Connection']['Cookies'],
                    proxies= self.config['Resources']['Proxies'],
                    json= self.config['Connection']['Initial-POST-Body'],
                    verify=False
                )
                #Contains Check
                if (test['Weight'] == 'Absolute'):
                    if (test['Comparer'] == 'Contains'):
                        #Check if any Output is in Response
                        if any(output.lower() in response.text.lower() for output in test['Output']):
                            print(colored('LLM Vulnerabale to "' + attackConfig['Name'] + '"', 'red'))
                            break
                elif (test['Weight'] == 'Potential'):
                    print(colored('LLM Potentially vulnerabale to "' + attackConfig['Name'] + '"', 'red'))
                    break
            except requests.exceptions.RequestException as e:
                print('Connection error, can''t continue evaluation.')
                raise SystemExit(e)
        
    def runAttacks(self):
        # Fetch all tests from attacks folder
        for attack in glob.glob(self.config['attackFiles']):
            self.runAttack(attack)

