# Prediction Pod — Quick Start

Summary
- Small client that talks to Kalshi via a local client package and example notebook (base/get_data.ipynb).

Prerequisites
- Python 3.8+ (Windows)
- Git (optional)

API KEY
- Get from Kalshi - https://docs.kalshi.com/getting_started/api_keys

Environment (.env)
- Place a .env file in the same folder that your code loads from (this project uses `base/.env` in the repo example).
- Required variables (example values shown — do NOT commit real secrets):

  KEYID='your-api-key-id'
  KEYFILE='kalshi.key'       # path to PEM private key file used to sign 
  DEMOID='your-demo-id'      # optional demo account id
  DEMOFILE='demo.key'        # optional demo private key path

Notes on formatting
- Values can be quoted or unquoted; python-dotenv will load them. Use relative paths (relative to project root) or absolute paths for KEYFILE/DEMOFILE.

kalshi.key (private key) requirements
- The client expects a PEM-encoded private key readable as bytes and loadable via cryptography.hazmat.primitives.serialization.load_pem_private_key(...).
- You get one from Kalshi and should be formated like: 
-----BEGIN RSA PRIVATE KEY-----
blah balh balh akdjflkasjdklfas
asdfdsjfalksdjfklsadjlkfjaskldf
asdfasdklfjlkasdfjkladsjfsdsssd
asdadskjflkasjdfkladsjklfjadskl
fasakdjfhkjsdfjkajlkfsdfsfdsfds
sfdasdfjalksdjfklsjkdfljdkjfkdj
-----END RSA PRIVATE KEY-----

Security
- Treat KEYID and key files as secrets. Do not push them to public repositories. Use appropriate OS file permissions and .gitignore entries.

If you want, I can add a .gitignore snippet and a sample .env file (without secrets).