import os
import sys

# Aggiunge la cartella principale al path per permettere i corretti import
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app

app = create_app()

# Vercel invoca "app" per gestire le richieste HTTP in ambiente serverless Python.
