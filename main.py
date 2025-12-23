import sys
from pathlib import Path

# Add current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

import pipeline

print('''Boot sequence initiated...
Arc reactor stable.
All systems online.
Initializing combat-ready systems.
Power levels rising.
Preparing for deployment...
System check complete...
Deployment successfully.
''')
print('Hello sir! I am Stark Assistant, your personal AI assistant powered by Stark Technologies.')
print('How can I assist you today?')
while True:
    command = input('What would you like me to do? (type "exit" to shut down)> ')

    if command == 'exit':
        print('Shutting down, sir.')
        break

    response = pipeline.process_command(command)

    print(response)

