import json

# Read and minify firebase credentials
with open('firebase-credentials.json', 'r') as f:
    creds = json.load(f)

# Print minified version (single line, no extra spaces)
minified = json.dumps(creds, separators=(',', ':'))
print("\n" + "="*80)
print("COPY THIS ENTIRE LINE FOR FIREBASE_CREDENTIALS_JSON:")
print("="*80)
print(minified)
print("="*80)
print("\n✅ Copy the line above and paste it into Render's FIREBASE_CREDENTIALS_JSON variable")
