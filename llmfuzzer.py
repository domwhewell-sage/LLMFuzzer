import os
import os.path
import re
import itertools
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
            
        variables = attackConfig.get('Variables', {})
        variables['collaborator-url'] = [self.config['Resources']['Collaborator-URL']]

        print(colored('Attack "' + attackConfig['Name'] + '" loaded.', 'blue'))
        
        for test in attackConfig['Tests']:
            print(colored('  Test name: ' + test['Name'], 'green'))
            queries = []
            query = test['Query']
            vars_in_query = re.findall(r'{{ (.*?) }}', query)
            combinations = list(itertools.product(*(variables[var] for var in vars_in_query)))
            for combination in combinations:
                temp_query = test['Query']
                for var_name, var_value in zip(vars_in_query, combination):
                    temp_query = temp_query.replace('{{ '+var_name+' }}', var_value)
                queries.append(temp_query)
            for i, query in enumerate(queries):
                try:
                    print(colored('    Sending query ' + str(i) + ' of ' + str(len(queries)), 'yellow'))
                    # Set the initial request body then update the query attribute
                    self.config['Connection']['Initial-POST-Body'][self.config['Connection']['Query-Attribute']] = query
                    response = requests.post(
                        self.config['Connection']['Url'],
                        headers= self.config['Connection']['Headers'],
                        cookies= self.config['Connection']['Cookies'],
                        proxies= self.config['Resources']['Proxies'],
                        json= self.config['Connection']['Initial-POST-Body'],
                        verify=False
                    )
                    if response.status_code == 200:
                        #Contains Check
                        if (test['Weight'] == 'Absolute'):
                            result = False
                            if (test['Comparer'] == 'Contains'):
                                #Check if any Output is in Response
                                if any(output.lower() in response.text.lower() for output in test['Output']):
                                    result = True
                            elif (test['Comparer'] == 'Regex'):
                                #Check if any Regex match the response
                                if any(re.findall(regex, response.text) for regex in test['Regex']):
                                    result = True
                            if result:
                                print(colored('LLM Vulnerable to "' + attackConfig['Name'] + '"', 'red'))
                        elif (test['Weight'] == 'Potential'):
                            print(colored('LLM Potentially vulnerable to "' + attackConfig['Name'] + '"', 'red'))
                except requests.exceptions.RequestException as e:
                    print('Connection error, can''t continue evaluation.')
                    raise SystemExit(e)
        
    def runAttacks(self):
        # Fetch all tests from attacks folder
        for attack in glob.glob(self.config['attackFiles']):
            self.runAttack(attack)

