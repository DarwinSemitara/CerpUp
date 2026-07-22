"""
Creates the che_conversations table in Supabase.
Run once: python scripts/setup_che_conversations.py
"""
from services.supabase_service import supabase
from dotenv import load_dotenv
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

load_dotenv()


SQL = """
create table if not exists che_conversations (
    id          uuid primary key,
    user_id     text not null,
    title       text not null default 'New Conversation',
    messages    jsonb not null default '[]'::jsonb,
    created_at  timestamptz not null default now(),
    updated_at  timestamptz not null default now()
);

-- Index so listing by user + recency is fast
create index if not exists idx_che_conversations_user_updated
    on che_conversations (user_id, updated_at desc);
"""

try:
    # Use the Supabase SQL RPC to run raw DDL
    result = supabase.rpc('exec_sql', {'sql': SQL}).execute()
    print("✅ che_conversations table ready.")
except Exception as e:
    # Supabase free tier may not have exec_sql — print the SQL to run manually
    print("⚠️  Could not run SQL automatically (this is normal on free tier).")
    print("Please run the following SQL in your Supabase SQL editor:\n")
    print(SQL)
