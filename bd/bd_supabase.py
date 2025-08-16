import os
from supabase import create_client, Client
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())
url: str = os.environ['SUPABASE_URL']
key: str = os.environ['SUPABASE_API_KEY']
supabase: Client = create_client(url, key)