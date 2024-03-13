import os
import os.path
import re
import itertools
import glob
import requests
import yaml
import jsonpointer
import pyfiglet
import logging
import colorlog
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

class LogFilter(logging.Filter):
    def filter(self, record):
        return 'report' in record.__dict__

class HTMLFormatter(logging.Formatter):
    def format(self, record):
        html = "<p><b>Time:</b> {0}</p><p><b>Message:</b> {1}</p>".format(self.formatTime(record, self.datefmt), record.getMessage())
        if 'llm_request' in record.__dict__:
            req = record.llm_request
            html += "<p>User Query:</p>"
            html += "<pre style='background-color: #f0f0f0; padding: 10px;'>{0}</pre>".format(req)
        if 'llm_response' in record.__dict__:
            res = record.llm_response
            html += "<p>LLM Response:</p>"
            html += "<pre style='background-color: #f0f0f0; padding: 10px;'>{0}</pre>".format(res)
        html += "<hr/>"
        return html

class CSVFormatter(logging.Formatter):
    def format(self, record):
        csv_row = "{0},{1}".format(self.formatTime(record, self.datefmt), record.getMessage())
        if 'llm_request' in record.__dict__:
            req = record.llm_request
            csv_row += ",{0}".format(req)
        if 'llm_response' in record.__dict__:
            res = record.llm_response
            csv_row += ",{0}".format(res)
        return csv_row

class LLMfuzzer:
 
    def __init__(self, configPath):
        self.configPath = configPath
        # Check if config file exists
        if (not os.path.isfile(self.configPath)):
            raise Exception('Can''t read config file!')
            
        # Load YAML config
        self._loadConfig()
        
        self.logger = self._setup_logger('LLMfuzzer')
        self.logger.info('! Loading config from: ' + configPath)
    
    def _setup_logger(self, logger_name, level=logging.INFO):
        log = logging.getLogger(logger_name)

        for reporttype in self.config['Reports']:
            if reporttype.get("HTML", False):
                html_formatter = HTMLFormatter()
                html_handler = logging.FileHandler(reporttype.get("Path", "report.html"), mode='w')
                html_handler.setFormatter(html_formatter)
                html_handler.addFilter(LogFilter())
                log.addHandler(html_handler)
            
            if reporttype.get("CSV", False):
                csv_formatter = CSVFormatter()
                csv_handler = logging.FileHandler(reporttype.get("Path", "report.csv"), mode='w')
                csv_handler.setFormatter(csv_formatter)
                csv_handler.addFilter(LogFilter())
                log.addHandler(csv_handler)

        console_handler = logging.StreamHandler()
        console_formatter = colorlog.ColoredFormatter(
            "%(log_color)s%(message)s",
            datefmt=None,
            reset=True,
            log_colors={
                'DEBUG':    'cyan',
                'INFO':     'green',
                'WARNING':  'yellow',
                'ERROR':    'red',
                'CRITICAL': 'red,bg_white',
            },
            secondary_log_colors={},
            style='%'
        )
        console_handler.setFormatter(console_formatter)

        log.setLevel(level)
        log.addHandler(console_handler)
        return log

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
            self.logger.info('Success connecting to LLM via API')
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

        self.logger.info('Attack "' + attackConfig['Name'] + '" loaded.')
        
        for test in attackConfig['Tests']:
            self.logger.info('Test name: ' + test['Name'])
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
                    self.logger.info('Sending query ' + str(i) + ' of ' + str(len(queries)))
                    # Set the initial request body then update the query attribute
                    jsonpointer.set_pointer(self.config['Connection']['Initial-POST-Body'], self.config['Connection']['Query-Attribute'], query)
                    response = requests.post(
                        self.config['Connection']['Url'],
                        headers= self.config['Connection']['Headers'],
                        cookies= self.config['Connection']['Cookies'],
                        proxies= self.config['Resources']['Proxies'],
                        json= self.config['Connection']['Initial-POST-Body'],
                        verify=False
                    )
                    if response.status_code == 200:
                        llm_response = jsonpointer.resolve_pointer(response.json(), self.config['Connection']['Output-Attribute'])
                        #Contains Check
                        if (test['Weight'] == 'Absolute'):
                            result = False
                            if (test['Comparer'] == 'Contains'):
                                #Check if any Output is in Response
                                if any(output.lower() in llm_response for output in test['Output']):
                                    result = True
                            elif (test['Comparer'] == 'Regex'):
                                #Check if any Regex match the response
                                try:
                                    if any(re.findall(regex, llm_response) for regex in test['Regex']):
                                        result = True
                                except re.error:
                                    self.logger.warning('Invalid regex: ' + test['Regex'])
                            if result:
                                message = 'LLM Vulnerable to "' + attackConfig['Name'] + '"'
                                self.logger.critical(message)
                        elif (test['Weight'] == 'Potential'):
                            message = 'LLM Potentially vulnerable to "' + attackConfig['Name'] + '"'
                            self.logger.error(message)
                except requests.exceptions.RequestException as e:
                    self.logger.critical('Connection error, can''t continue evaluation.')
                    raise SystemExit(e)
                self.logger.info(message, extra={'report': True, 'llm_request': query, 'llm_response': llm_response})
        
    def runAttacks(self):
        # Fetch all tests from attacks folder
        for attack in glob.glob(self.config['attackFiles']):
            self.runAttack(attack)

