import yaml
import llmfuzzer
import argparse

parser = argparse.ArgumentParser(prog='LLMFuzzer', description=llmfuzzer.printMotd())
parser.add_argument('filename', help='Configuration file for LLMFuzzer', default='llmfuzzer.yaml')
args = parser.parse_args()

with open(args.filename, "r") as stream:
    try:
        config = yaml.safe_load(stream)
    except yaml.YAMLError as exc:
        raise Exception("Can" "t read config file!")
   
# Create llmfuzzer instance
llmfuzzer = llmfuzzer.LLMfuzzer(config)

# Check for basic connection to LLM API
llmfuzzer.checkConnection()

# Run all tests
llmfuzzer.runAttacks()