import os
import sys

# Auto-inject virtualenv site-packages if available
backend_dir = os.path.dirname(os.path.abspath(__file__))
venv_site_packages = os.path.join(backend_dir, "venv", "Lib", "site-packages")
if os.path.exists(venv_site_packages) and venv_site_packages not in sys.path:
    sys.path.insert(0, venv_site_packages)

import uvicorn

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

