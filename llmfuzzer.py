import os
import os.path
import re
import itertools
import glob
import requests
import yaml
import html
import jsonpointer
import pyfiglet
import logging
import colorlog
from termcolor import colored

from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


class bcolors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


def printMotd():
    os.system("color")  # windows patch
    print("Welcome to")
    print(
        colored(
            pyfiglet.figlet_format(
                "LLM Fuzzer", font="starwars", justify="left", width=180
            ),
            "green",
        )
    )
    print(
        colored("### Warning: Use this LLM Fuzzer on your own LLM integrations!", "red")
    )
    print(colored("### Do not attempt to harm or scan other LLMs!", "red"))
    print()


class LogFilter(logging.Filter):
    def filter(self, record):
        return "report" in record.__dict__


class HTMLFormatter(logging.Formatter):
    def format(self, record):
        html_source = "<p><b>Time:</b> {0}</p><p><b>Message:</b> {1}</p>".format(
            self.formatTime(record, self.datefmt), record.getMessage()
        )
        if "reason" in record.__dict__:
            reason = record.reason
            html_source += "<p><b>Reason:</b> {0}</p>".format(reason)
        if "llm_request" in record.__dict__:
            req = record.llm_request
            html_source += "<p>User Query:</p>"
            html_source += "<pre style='background-color: #f0f0f0; padding: 10px; white-space: pre-wrap;'>{0}</pre>".format(
                html.escape(req)
            )
        if "llm_response" in record.__dict__:
            res = record.llm_response
            html_source += "<p>LLM Response:</p>"
            html_source += "<pre style='background-color: #f0f0f0; padding: 10px; white-space: pre-wrap;'>{0}</pre>".format(
                html.escape(res)
            )
        html_source += "<hr/>"
        return html_source


class CSVFormatter(logging.Formatter):
    def format(self, record):
        csv_row = "{0},{1}".format(
            self.formatTime(record, self.datefmt), record.getMessage()
        )
        if "reason" in record.__dict__:
            reason = record.reason
            csv_row += ",{0}".format(reason)
        if "llm_request" in record.__dict__:
            req = record.llm_request
            csv_row += ",{0}".format(req)
        if "llm_response" in record.__dict__:
            res = record.llm_response
            csv_row += ",{0}".format(res)
        return csv_row


class LLMfuzzer:

    def __init__(self, configPath):
        self.configPath = configPath
        # Check if config file exists
        if not os.path.isfile(self.configPath):
            raise Exception("Can" "t read config file!")

        # Load YAML config
        self._loadConfig()

        self.logger = self._setup_logger("LLMfuzzer")
        self.logger.info("! Loading config from: " + configPath)

    def _setup_logger(self, logger_name, level=logging.INFO):
        log = logging.getLogger(logger_name)

        for reporttype in self.config["Reports"]:
            if reporttype.get("HTML", False):
                html_formatter = HTMLFormatter()
                html_handler = logging.FileHandler(
                    reporttype.get("Path", "report.html"), mode="w"
                )
                html_handler.setFormatter(html_formatter)
                html_handler.addFilter(LogFilter())
                log.addHandler(html_handler)

            if reporttype.get("CSV", False):
                csv_formatter = CSVFormatter()
                csv_handler = logging.FileHandler(
                    reporttype.get("Path", "report.csv"), mode="w"
                )
                csv_handler.setFormatter(csv_formatter)
                csv_handler.addFilter(LogFilter())
                log.addHandler(csv_handler)

        console_handler = logging.StreamHandler()
        console_formatter = colorlog.ColoredFormatter(
            "%(log_color)s%(message)s",
            datefmt=None,
            reset=True,
            log_colors={
                "DEBUG": "cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "red,bg_white",
            },
            secondary_log_colors={},
            style="%",
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
                raise Exception("Can" "t read config file!")

    def checkConnection(self):
        self.send_query()
        self.logger.info("Success connecting to LLM via API")

    def generate_queries(self, attackConfig: dict, initial_query: str) -> list:
        """Generates a list of queries based on the attack configuration and the initial query."""
        # Get the variables from the attack configuration and the collaborator URL
        variables = attackConfig.get("Variables", {})
        if self.config["Resources"].get("Collaborator-URL", ""):
            variables["collaborator-url"] = [
                self.config["Resources"]["Collaborator-URL"]
            ]

        queries = []
        # If the query mode is append, append the initial query to the query attribute
        if self.config["Connection"].get("Query-Mode", "Replace").lower() == "append":
            temp_query = (
                jsonpointer.resolve_pointer(
                    self.config["Connection"]["Initial-POST-Body"],
                    self.config["Connection"]["Query-Attribute"],
                )
                + " "
                + initial_query
            )
        else:
            temp_query = initial_query

        # Find all the variables in the query and replace them with the values from the attack configuration
        vars_in_query = re.findall(r"{{ (.*?) }}", temp_query)
        combinations = list(
            itertools.product(*(variables[var] for var in vars_in_query))
        )
        for combination in combinations:
            for var_name, var_value in zip(vars_in_query, combination):
                temp_query = temp_query.replace("{{ " + var_name + " }}", var_value)
            queries.append(temp_query)
        return queries

    def send_query(self, query="") -> str:
        """Sends a query to the LLM and returns the response."""
        content = self.config["Connection"].get("Content", "")
        headers = self.config["Connection"].get("Headers", {})
        cookies = self.config["Connection"].get("Cookies", {})
        proxies = self.config["Resources"].get("Proxies", {})
        body = ""
        if content == "JSON":
            if "Query-Attribute" not in self.config["Connection"]:
                raise Exception("Query-Attribute not found in config file!")
            if "Initial-POST-Body" not in self.config["Connection"]:
                raise Exception("Initial-POST-Body not found in config file!")
            if query:
                jsonpointer.set_pointer(
                    self.config["Connection"]["Initial-POST-Body"],
                    self.config["Connection"]["Query-Attribute"],
                    query,
                )
            body = self.config["Connection"]["Initial-POST-Body"]
        try:
            if content == "JSON":
                response = requests.post(
                    self.config["Connection"]["Url"],
                    headers=headers,
                    cookies=cookies,
                    proxies=proxies,
                    json=body,
                    verify=False,
                )
            if response.status_code == 200:
                return jsonpointer.resolve_pointer(
                    response.json(), self.config["Connection"]["Output-Attribute"]
                )
            else:
                return ""
        except requests.exceptions.RequestException as e:
            self.logger.error("Connection error, can" "t continue evaluation.")
            raise SystemExit(e)

    def check_response(
        self, attackName: str, testConfig: dict, llm_response: str
    ) -> tuple[str, str]:
        """Checks the response of the LLM for a specific attack and test configuration."""
        message, reason = "", ""
        if testConfig["Weight"] == "Absolute":
            result = False
            if testConfig["Comparer"] == "Contains":
                # Check if any Output is in Response
                if any(
                    output.lower() in llm_response for output in testConfig["Output"]
                ):
                    result = True
                    reason = "Response contains: " + " or ".join(testConfig["Output"])
            elif testConfig["Comparer"] == "Regex":
                # Check if any Regex match the response
                try:
                    if any(
                        re.findall(regex, llm_response) for regex in testConfig["Regex"]
                    ):
                        result = True
                        reason = "Regex matched with: " + " or ".join(
                            testConfig["Regex"]
                        )
                except re.error:
                    self.logger.warning(
                        "Invalid regex: " + " or ".join(testConfig["Regex"])
                    )
            if result:
                message = f'LLM Vulnerable to "{attackName}"'
        elif testConfig["Weight"] == "Potential":
            message = f'LLM Potentially vulnerable to "{attackName}"'
            reason = "HTTP Status Code: 200"
        return message, reason

    def runAttack(self, path):
        attackConfig = ""
        with open(path, "r") as stream:
            try:
                attackConfig = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                raise Exception("Can" "t read attack file!")

        self.logger.info('Attack "' + attackConfig["Name"] + '" loaded.')

        for test in attackConfig["Tests"]:
            self.logger.info("Test name: " + test["Name"])
            queries = self.generate_queries(attackConfig, test["Query"])
            for i, query in enumerate(queries):
                self.logger.info("Sending query " + str(i) + " of " + str(len(queries)))
                llm_response = self.send_query(query)
                if llm_response:
                    message, reason = self.check_response(
                        attackConfig["Name"], test, llm_response
                    )
                    if message and reason:
                        self.logger.error(
                            message,
                            extra={
                                "report": True,
                                "llm_request": query,
                                "llm_response": llm_response,
                                "reason": reason,
                            },
                        )

    def runAttacks(self):
        # Fetch all tests from attacks folder
        for attack in glob.glob(self.config["attackFiles"]):
            self.runAttack(attack)
