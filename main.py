import llmfuzzer

# Print MOTD
llmfuzzer.printMotd()
   
# Create llmfuzzer instance
llmfuzzer = llmfuzzer.LLMfuzzer("llmfuzzer.yaml")

# Check for basic connection to LLM API
llmfuzzer.checkConnection()

# Run all tests
llmfuzzer.runAttacks()