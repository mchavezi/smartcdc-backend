# ===================================================
# NOTICE: This file is part of a private repository.
# Provided for demonstration purposes only.
# Not suitable for production use.
# ===================================================

from app import create_app

# Initialize the Flask app using the factory function
app = create_app()

if __name__ == "__main__":
    app.run()
