import os

# Use a throwaway SQLite database and no external keys during tests.
os.environ["DATABASE_URL"] = "sqlite:///./test_speechapp.db"
os.environ["GROQ_API_KEY"] = ""
