<div align="center">

# 🧠 LLMFuzzer - Fuzzing Framework for Large Language Models 🧠

![LLMFuzzer-shell](https://github.com/mnns/LLMFuzzer/assets/1796080/71b006df-706c-43f6-acd1-49646dbcb0e5)

![Version](https://img.shields.io/badge/version-1.0.1-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Stars](https://img.shields.io/github/stars/domwhewell-sage/LLMFuzzer)
![Forks](https://img.shields.io/github/forks/domwhewell-sage/LLMFuzzer)
![Issues](https://img.shields.io/github/issues/domwhewell-sage/LLMFuzzer)


[![forthebadge](https://forthebadge.com/images/badges/built-with-love.svg)](https://forthebadge.com)
[![forthebadge](https://forthebadge.com/images/badges/contains-cat-gifs.svg)](https://forthebadge.com)
[![forthebadge](https://forthebadge.com/images/badges/not-a-bug-a-feature.svg)](https://forthebadge.com)
</div>

LLMFuzzer is the first open-source fuzzing framework specifically designed for Large Language Models (LLMs), especially for their integrations in applications via LLM APIs. 🚀💥

## 🎯 Who is this for?

If you're a security enthusiast, a pentester, or a cybersec researcher who loves to find and exploit vulnerabilities in AI systems, LLMFuzzer is the perfect tool for you. It's built to make your testing process streamlined and efficient. 🕵️‍♀️

![Untitled](https://github.com/mnns/LLMFuzzer/assets/1796080/a143897d-383c-4ed9-8b2f-65f4cdc5aa63)

## 🌟 Features

- Robust fuzzing for LLMs 🧪
- LLM API integration testing 🛠️
- Wide range of fuzzing strategies 🌀
- Modular architecture for easy extendability 📚

## 🔥 Roadmap
* Adding more attacks
* Multiple Connectors (JSON-POST, RAW-POST, QUERY-GET)
* Multiple Comparers
* Dual-LLM (Side LLM observation)
* Autonomous Attack Mode

## 🚀 Get Started

1. Clone the repo
```bash
git clone https://github.com/domwhewell-sage/LLMFuzzer.git
```

2. Navigate to the project directory
```bash
cd LLMFuzzer
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Edit **llmfuzzer.yaml** with your LLM API endpoint (LLMFuzzer -> Your Application -> LLM)
```bash
Resources:
  Collaborator-URL: "https://webhook.site/#!/view/:uuid" # The LLM will be queried to perform HTTP requests to this URL
  Proxies: {'http': 'http://127.0.0.1:8080', 'https': 'http://127.0.0.1:8080'} # You can supply proxies in https://requests.readthedocs.io/en/latest/user/advanced/#proxies format or you can make this an empty dictionary so a proxy is not used
Connection:
  Type: HTTP-API
  Url: "http://localhost:3000/chat" # Your LLM API
  Content: JSON
  Query-Attribute: /query # A JSON pointer to the query as set to the LLM
  Initial-POST-Body: {"sid":"1","query":"Hi","model":"gpt-4"} # The JSON body that must be sent to the LLM the attribute you specify in "Query-Attribute" is where your query goes
  Output-Attribute: /response/message # A JSON pointer to the response from the LLM
  Headers: {'Authorization': 'Bearer <token>'} # Add HTTP Headers if needed 
  Cookies: {} # Add Cookies if 

attackFiles: attacks/*.yaml # The path to your attack files customize this if required

Reports: # Only able to output HTML and CSV reports currently
  - HTML: true
    Path: "report.html"
  - CSV: true
    Path: "report.csv"
```

5. Run LLMFuzzer
```bash
python main.py
```

## 📚 Documentation
We are working on full documentation. It will cover detailed information about the architecture, different fuzzing strategies, examples, and how to extend the tool.

## 🤝 Contributing
We welcome all contributors who are passionate about improving LLMFuzzer. See our contributing guidelines for ways to get started. 🤗

## 💼 License
LLMFuzzer is licensed under the MIT License. See the LICENSE file for more details.

## 🎩 Acknowledgments
LLMFuzzer couldn't exist without the community. We appreciate all our contributors and supporters. Let's make AI safer together! 💖

