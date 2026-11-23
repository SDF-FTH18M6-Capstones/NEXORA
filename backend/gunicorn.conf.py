"""Gunicorn settings. Start from backend/:  gunicorn "app:create_app()"

`app` is the package (backend/app/), not backend/app.py, so the factory is
`app:create_app()`. Render sets PORT.
"""

import os

bind = f"0.0.0.0:{os.environ.get('PORT', '5000')}"
workers = 2
timeout = 30
accesslog = "-"
