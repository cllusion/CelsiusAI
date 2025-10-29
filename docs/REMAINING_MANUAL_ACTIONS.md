Remaining manual actions and environmental steps
=================================================

This file lists things that cannot be fully automated by code edits and may require manual setup or environment-specific actions.

1) Tesseract OCR (optional)
- If you plan to use OCR features (`pytesseract` + `pdf2image`), install Tesseract separately on Windows:
  - Download and install from: https://github.com/tesseract-ocr/tesseract
  - Add the Tesseract binary folder to your PATH (e.g., C:\Program Files\Tesseract-OCR)

2) PDF rendering dependencies (optional)
- `pdf2image` requires poppler. On Windows, install Poppler and add its `bin/` folder to PATH.
  - Download: https://poppler.freedesktop.org/

3) Email provider credentials (optional)
- To enable email notifications, create `config/email_config.json` (or run the interactive setup) with SMTP credentials.
- For Gmail, use an App Password and enable the account's security settings accordingly.

4) Network & crawling limitations
- Web-learning and external crawling may be blocked by corporate VPNs, proxies, or firewalls.
- If crawls fail, try disabling VPN or whitelist the host in proxy rules.

5) Ngrok / Tunnels (optional)
- If you use `ngrok` for exposing local services, install ngrok and configure authtoken with `ngrok config add-authtoken <token>`.

6) Python environment
- Ensure the virtual environment is activated before running tests or the app:

```powershell
& "C:/Users/micro/Celsius AI/.venv/Scripts/Activate.ps1"
```

- After updating `requirements.txt`, install dependencies in the venv:

```powershell
& 'C:/Users/micro/Celsius AI/.venv/Scripts/python.exe' -m pip install -r requirements.txt
```

7) Test plugin mismatch
- If pytest fails with a plugin-related ModuleNotFoundError (e.g., anyio test helper), ensure `anyio` and `pytest-asyncio` versions are compatible with your pytest version. Installing/upgrading using the command above should resolve it.

8) External API keys & provider access
- For any provider connectors (Twilio, RedPocket, etc.), ensure API keys/secrets are stored securely in `config/` and not committed to source control.

If you want, I can try to install the updated `requirements.txt` into your venv and re-run the full test suite and linters; say "please install deps and test" and I'll proceed.