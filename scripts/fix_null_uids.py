"""
Fix null UIDs in Supabase users table
This script updates all users records where uid is NULL to set uid = id
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
from services.supabase_service import supabase

load_dotenv()

def fix_null_uids():
    print("="*70)
    print("🔧 FIX NULL UIDs IN SUPABASE USERS TABLE")
    print("="*70)
    print()
    
    try:
        # Step 1: Find all users with null uid
        print("1️⃣ Finding users with null uid...")
        result = supabase.table('users').select('id, uid, email').is_('uid', 'null').execute()
        
        if not result.data:
            print("   ✅ No users with null uid found!")
            print()
            return
        
        null_uid_count = len(result.data)
        print(f"   ⚠️  Found {null_uid_count} user(s) with null uid:")
        
        for user in result.data:
            print(f"      - ID: {user['id']}, Email: {user.get('email', 'N/A')}")
        
        print()
        
        # Step 2: Fix each user
        print("2️⃣ Fixing null uids...")
        fixed_count = 0
        failed_count = 0
        
        for user in result.data:
            user_id = user['id']
            try:
                # Update uid to match id
                supabase.table('users').update({
                    'uid': user_id
                }).eq('id', user_id).execute()
                
                print(f"   ✅ Fixed user {user_id}")
                fixed_count += 1
            except Exception as e:
                print(f"   ❌ Failed to fix user {user_id}: {e}")
                failed_count += 1
        
        print()
        print("="*70)
        print(f"✅ Fixed: {fixed_count}")
        print(f"❌ Failed: {failed_count}")
        print("="*70)
        print()
        
        # Step 3: Verify
        print("3️⃣ Verifying fix...")
        verify_result = supabase.table('users').select('id, uid').is_('uid', 'null').execute()
        
        if not verify_result.data:
            print("   ✅ All users now have uid set!")
        else:
            print(f"   ⚠️  Still {len(verify_result.data)} user(s) with null uid")
        
        print()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return

if __name__ == '__main__':
    fix_null_uids()
