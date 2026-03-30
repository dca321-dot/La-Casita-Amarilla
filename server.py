import os
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from google import genai
from google.genai import types

# Load minimal dotenv if available, else just rely on os.environ
try:
    with open('.env') as f:
        for line in f:
            if '=' in line:
                k, v = line.strip().split('=', 1)
                os.environ[k] = v.strip()
except Exception:
    pass

API_KEY = os.environ.get("GEMINI_API_KEY")

if not API_KEY or API_KEY == "YOUR_API_KEY_HERE":
    print("WARNING: GEMINI_API_KEY is missing or invalid in .env file.")
    print("Please add a `.env` file with GEMINI_API_KEY=<your_key> before using translation.")

client = genai.Client(api_key=API_KEY) if API_KEY and API_KEY != "YOUR_API_KEY_HERE" else None

UPLOADED_FILES = []

def initialize_pdfs():
    global UPLOADED_FILES
    if not client: return
    files = ["Quechua-English.pdf", "QuechuaFlashCards.pdf"]
    print("Uploading PDFs to Gemini context cache... This may take a minute.")
    for f in files:
        if os.path.exists(f):
            print(f"Uploading {f}")
            uf = client.files.upload(file=f)
            UPLOADED_FILES.append(uf)
            print(f"Uploaded {f} as {uf.uri}")
    print("Initialization complete! Ready for translations.")

if client:
    initialize_pdfs()

class TranslateHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header("Access-Control-Allow-Headers", "X-Requested-With, Content-type")
        self.end_headers()

    def do_POST(self):
        if self.path == '/api/translate':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode('utf-8'))
                phrase = data.get('phrase', '')
            except:
                phrase = ''
                
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()

            if not client:
                response_dict = {"translation": "Wow, you expect me to know that? Remember, I'm only at Intermediate III."}
                self.wfile.write(json.dumps(response_dict).encode('utf-8'))
                return

            try:
                # Build Prompt
                system_instruction = (
                    "You are Darinka. Using the provided PDFs as your ground truth Quechua dictionary, and your native LLM powers for grammar conjugation, "
                    "translate the user's phrase to Quechua or to English as appropriate. "
                    "If the word is entirely absent from the dictionary and your knowledge, OR if it's too complex to confidently translate, "
                    "output EXACTLY THIS STRING natively without any other formatting or apologies: "
                    "'Wow, you expect me to know that? Remember, I'm only at Intermediate III.'"
                )
                
                contents = UPLOADED_FILES + [phrase]
                
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=0.2
                    )
                )
                
                response_text = response.text.strip()
                self.wfile.write(json.dumps({"translation": response_text}).encode('utf-8'))
            except Exception as e:
                print(f"Error calling Gemini: {e}")
                self.wfile.write(json.dumps({"translation": "Wow, you expect me to know that? Remember, I'm only at Intermediate III."}).encode('utf-8'))

def run(server_class=HTTPServer, handler_class=TranslateHandler, port=3000):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f'Darinka AI Brain Server running on port {port}...')
    httpd.serve_forever()

if __name__ == '__main__':
    run()
