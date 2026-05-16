import json
import os

files = ['songs.json', 'favorites.json', 'users.json']
for f in files:
    if os.path.exists(f):
        with open(f, 'r') as file:
            try:
                data = json.load(file)
            except:
                data = {}
        
        # If it's a dict and doesn't have 'default' as a key (and is not empty), 
        # assume it's the old structure and wrap it.
        if isinstance(data, dict) and 'default' not in data and len(data) > 0:
            print(f"Migrating {f}...")
            new_data = {'default': data}
            with open(f, 'w') as file:
                json.dump(new_data, file)
        elif not isinstance(data, dict):
             with open(f, 'w') as file:
                json.dump({'default': {}}, file)
