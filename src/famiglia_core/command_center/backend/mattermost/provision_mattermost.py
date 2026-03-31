import os
import sys
import json
import requests
from dotenv import load_dotenv
from mattermostdriver import Driver

def setup_mattermost():
    load_dotenv()
    
    # Strip protocol and port from URL to avoid duplication
    url_raw = os.getenv("MATTERMOST_URL", "http://mattermost:8065")
    url = url_raw.replace("http://", "").replace("https://", "").split(":")[0]
    scheme = os.getenv("MATTERMOST_SCHEME", "http")
    port = int(os.getenv("MATTERMOST_PORT", "8065"))
    token = os.getenv("MATTERMOST_BOT_TOKEN_SYSTEM")
    base_url_full = f"{scheme}://{url}:{port}"
    
    if not token or token == "your-system-token":
        print("\n" + "!"*60)
        print("ERROR: MATTERMOST_BOT_TOKEN_SYSTEM is missing or still set to a placeholder.")
        print("Please generate a token in the Mattermost container using:")
        print("docker exec -it la-passione-inc-mattermost-1 mmctl token generate <username> <token_name> --local")
        print("!"*60 + "\n")
        sys.exit(1)
        
    mm = Driver({
        'url': url,
        'token': token,
        'scheme': scheme,
        'port': port,
        'verify': False
    })
    
    try:
        mm.login()
        print("Authenticated with Mattermost as System Bot.")
    except Exception as e:
        print(f"Failed to authenticate: {e}")
        print("Note: Ensure the token belongs to a System Admin and is not expired.")
        sys.exit(1)
        
    # Load config
    config_path = os.path.join(os.path.dirname(__file__), "provisioning_config.json")
    with open(config_path, 'r') as f:
        config = json.load(f)
        
    team_cfg = config["team"]
    channels_cfg = config["channels"]
    users_cfg = config.get("users", [])
    sidebar_cfg = config.get("sidebar_categories", []) # Moved this up

    try:
        # 1. Ensure Team Exists
        try:
            team = mm.teams.get_team_by_name(team_cfg["name"])
            print(f"Team '{team_cfg['display_name']}' already exists (ID: {team['id']})")
        except Exception:
            print(f"Creating team '{team_cfg['display_name']}'...")
            team = mm.teams.create_team({
                "name": team_cfg["name"],
                "display_name": team_cfg["display_name"],
                "type": "O" # Open
            })
            print(f"Created team '{team_cfg['display_name']}' (ID: {team['id']})")
            
        team_id = team['id']
        
        # Add users to team
        for username in users_cfg:
            try:
                user = mm.users.get_user_by_username(username)
                mm.teams.add_user_to_team(team_id, {"team_id": team_id, "user_id": user["id"]})
                print(f"Added user '{username}' to team '{team_cfg['name']}'")
            except Exception as e:
                print(f"User '{username}' already in team or error: {e}")
                
        # Promote admins
        admins_cfg = config.get("admins", [])
        for username in admins_cfg:
            try:
                user = mm.users.get_user_by_username(username)
                if 'system_admin' not in user.get('roles', ''):
                    mm.client.make_request('put', f'/users/{user["id"]}/roles', options={"roles": "system_user system_admin"})
                    print(f"Promoted user '{username}' to system_admin")
            except Exception as e:
                print(f"User '{username}' admin promotion error: {e}")
        
        # 2. Ensure Channels Exist
        channel_map = {}
        for chan_cfg in channels_cfg:
            channel = None
            try:
                channel = mm.channels.get_channel_by_name(team_id, chan_cfg["name"])
                print(f"Channel '{chan_cfg['display_name']}' already exists (ID: {channel['id']})")
            except Exception:
                try:
                    print(f"Creating channel '{chan_cfg['display_name']}'...")
                    channel = mm.channels.create_channel({
                        "team_id": team_id,
                        "name": chan_cfg["name"],
                        "display_name": chan_cfg["display_name"],
                        "purpose": chan_cfg.get("purpose", ""),
                        "type": "O" # Public
                    })
                    print(f"Created channel '{chan_cfg['display_name']}' (ID: {channel['id']})")
                except Exception as e:
                    print(f"Error handling channel '{chan_cfg['name']}': {e}")
                    continue
            
            if channel:
                channel_map[chan_cfg["name"]] = channel["id"]
                
                # Add users to channel
                for username in users_cfg:
                    try:
                        user = mm.users.get_user_by_username(username)
                        mm.channels.add_user(channel["id"], {"user_id": user["id"]})
                        print(f"Added user '{username}' to channel '{chan_cfg['name']}'")
                    except Exception as e:
                        print(f"User '{username}' already in channel or error: {e}")

        # 2b. Provision Bots
        bots_cfg = config.get("bots", [])
        bot_tokens = {}
        if bots_cfg:
            print("\nProvisioning Bot Accounts...")
            for b_cfg in bots_cfg:
                username = b_cfg["username"]
                display_name = b_cfg["display_name"]
                description = b_cfg.get("description", "")
                
                try:
                    # Check if user/bot exists
                    bot_user = None
                    try:
                        bot_user = mm.users.get_user_by_username(username)
                    except Exception:
                        pass
                    
                    if not bot_user:
                        print(f"Creating bot '{username}'...")
                        payload = {"username": username, "display_name": display_name, "description": description}
                        resp = mm.client.make_request('post', '/bots', options=payload)
                        bot_res = resp.json() if hasattr(resp, 'json') else resp
                        bot_id = bot_res.get("user_id")
                    else:
                        print(f"Bot/User '{username}' already exists.")
                        bot_id = bot_user["id"]
                    
                    if not bot_id:
                        print(f"Warning: Could not determine user_id for {username}")
                        continue
                    
                    # 1. Profile Picture Upload
                    profile_pic_rel = b_cfg.get("profile_pic")
                    if profile_pic_rel:
                        # Find the absolute path - assuming it's relative to the repo root
                        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
                        pic_path = os.path.join(repo_root, profile_pic_rel)
                        
                        # Docker fallback
                        if not os.path.exists(pic_path) and os.path.exists(f"/app/{profile_pic_rel}"):
                            pic_path = f"/app/{profile_pic_rel}"
                            
                        if os.path.exists(pic_path):
                            print(f"Uploading profile picture for {username} from {pic_path}...")
                            api_url = f"{base_url_full}/api/v4/users/{bot_id}/image"
                            try:
                                with open(pic_path, 'rb') as f:
                                    files = {'image': (os.path.basename(pic_path), f, 'image/png')}
                                    r_pic = requests.post(api_url, files=files, headers={"Authorization": f"Bearer {token}"})
                                    if r_pic.status_code == 200:
                                        print(f"Successfully uploaded profile picture for {username}.")
                                    else:
                                        print(f"Warning: Failed to upload profile pic for {username}: {r_pic.status_code} - {r_pic.text}")
                            except Exception as e:
                                print(f"Error uploading image for {username}: {e}")
                        else:
                            print(f"Warning: Profile picture not found at {pic_path}")

                    # 2. Channel Assignments
                    # Add bot to team
                    try:
                        mm.teams.add_user_to_team(team_id, {'team_id': team_id, 'user_id': bot_id})
                    except Exception as e:
                        pass
                    
                    bot_channels = b_cfg.get("channels", [])
                    for c_name in bot_channels:
                        cid = channel_map.get(c_name)
                        if cid:
                            try:
                                mm.channels.add_user_to_channel(cid, {'user_id': bot_id})
                            except Exception:
                                pass # Already in channel
                        else:
                            print(f"Warning: Channel '{c_name}' not found for bot '{username}'")
                    
                    # 3. Personal Access Token
                    print(f"Generating personal access token for {username}...")
                    token_payload = {"description": f"Token for {username}"}
                    token_resp = mm.client.make_request('post', f'/users/{bot_id}/tokens', options=token_payload)
                    token_data = token_resp.json() if hasattr(token_resp, 'json') else token_resp
                    
                    if "token" in token_data:
                        bot_tokens[username] = token_data["token"]
                        print(f"Successfully generated token for {username}.")
                    else:
                        print(f"Warning: Could not generate token for {username}: {token_data}")

                except Exception as e:
                    print(f"Error provisioning bot '{username}': {e}")

        # 3. Sidebar Categories (Custom organization)
        if sidebar_cfg and users_cfg:
            print("\nConfiguring sidebar categories...")
            # Ensure default channels are in the map too
            try:
                ts = mm.channels.get_channel_by_name(team_id, "town-square")
                channel_map["town-square"] = ts["id"]
                ot = mm.channels.get_channel_by_name(team_id, "off-topic")
                channel_map["off-topic"] = ot["id"]
            except Exception:
                pass

            headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

            for username in users_cfg:
                try:
                    user = mm.users.get_user_by_username(username)
                    user_id = user["id"]
                    
                    # Fetch current categories for this user/team
                    existing_cats = []
                    try:
                        api_url = f"{base_url_full}/api/v4/users/{user_id}/teams/{team_id}/channels/categories"
                        resp = requests.get(api_url, headers=headers)
                        if resp.status_code == 200:
                            data = resp.json()
                            existing_cats = data.get('categories', [])
                        else:
                            print(f"Warning: Could not fetch categories for {username}: {resp.status_code}")
                    except Exception as e:
                        print(f"Warning: Could not fetch existing categories for {username}: {e}")

                    # Map of display_name -> category_id for custom categories
                    cat_name_to_id = {c['display_name']: c['id'] for c in existing_cats if c.get('type') == 'custom'}
                    
                    for cat_cfg in sidebar_cfg:
                        cat_display_name = cat_cfg["display_name"]
                        cat_channel_ids = []
                        for c_name in cat_cfg.get("channel_names", []):
                            cid = channel_map.get(c_name)
                            if cid:
                                cat_channel_ids.append(cid)
                            else:
                                print(f"Warning: Channel '{c_name}' not found for category '{cat_display_name}' for user '{username}'")
                        
                        if not cat_channel_ids:
                            continue

                        # Prepare category payload
                        payload = {
                            "user_id": user_id,
                            "team_id": team_id,
                            "display_name": cat_display_name,
                            "type": "custom",
                            "channel_ids": cat_channel_ids
                        }

                        existing_id = cat_name_to_id.get(cat_display_name)
                        if existing_id:
                            print(f"Updating existing sidebar category '{cat_display_name}' for {username}...")
                            api_url = f"{base_url_full}/api/v4/users/{user_id}/teams/{team_id}/channels/categories/{existing_id}"
                            r = requests.put(api_url, json=payload, headers=headers)
                        else:
                            print(f"Creating new sidebar category '{cat_display_name}' for {username}...")
                            api_url = f"{base_url_full}/api/v4/users/{user_id}/teams/{team_id}/channels/categories"
                            r = requests.post(api_url, json=payload, headers=headers)

                        if r.status_code in [200, 201]:
                            # Category synced
                            pass
                        else:
                            print(f"Info: Could not synchronize category '{cat_display_name}' for {username}: {r.status_code}")

                    # 4. Final Sorting Update
                    try:
                        resp = requests.get(f"{base_url_full}/api/v4/users/{user_id}/teams/{team_id}/channels/categories", headers=headers)
                        if resp.status_code == 200:
                            updated_cats = resp.json().get('categories', [])
                            final_id_map = {c['display_name']: c['id'] for c in updated_cats if c.get('type') == 'custom'}
                            
                            new_order = []
                            for cat_name in ["PRIO", "Business", "Intel", "General"]:
                                cid = final_id_map.get(cat_name)
                                if cid: new_order.append(cid)
                            
                            current_order = resp.json().get('order', [])
                            for cid in current_order:
                                if cid not in new_order: new_order.append(cid)
                            
                            order_url = f"{base_url_full}/api/v4/users/{user_id}/teams/{team_id}/channels/categories/order"
                            requests.put(order_url, json=new_order, headers=headers)
                    except Exception:
                        pass
                except Exception as e:
                    print(f"Failed to configure categories for '{username}': {e}")
                
        print("\nMattermost provisioning completed successfully.")
        
        if bot_tokens:
            print("\n" + "="*40)
            print("BOT ACCESS TOKENS GENERATED:")
            print("="*40)
            for bot_user, b_token in bot_tokens.items():
                print(f"{bot_user.upper()}: {b_token}")
            print("="*40)
            print("Action Required: Please update your .env file with these tokens.")

    except Exception as e:
        print(f"Critical error during provisioning: {e}")
    finally:
        mm.logout()

if __name__ == "__main__":
    setup_mattermost()
