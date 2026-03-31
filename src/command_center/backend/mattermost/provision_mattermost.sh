#!/bin/bash

# Configuration
CONFIG_FILE="$(dirname "$0")/provisioning_config.json"

if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: Configuration file $CONFIG_FILE not found."
    exit 1
fi

TEAM_NAME=$(jq -r '.team.name' "$CONFIG_FILE")
TEAM_DISPLAY=$(jq -r '.team.display_name' "$CONFIG_FILE")
CHANNELS=($(jq -r '.channels[].name' "$CONFIG_FILE"))
USERS_TO_ADD=($(jq -r '.users[]' "$CONFIG_FILE"))

echo "Provisioning Mattermost via mmctl --local..."

# 1. Ensure Team Exists
if ! /opt/mattermost/bin/mmctl team show $TEAM_NAME --local > /dev/null 2>&1; then
    echo "Creating team $TEAM_DISPLAY ($TEAM_NAME)..."
    /opt/mattermost/bin/mmctl team create --name $TEAM_NAME --display-name "$TEAM_DISPLAY" --type O --local
else
    echo "Team $TEAM_NAME already exists."
fi

# Add users to team
for user in "${USERS_TO_ADD[@]}"; do
    echo "Adding user $user to team $TEAM_NAME..."
    /opt/mattermost/bin/mmctl team users add --team $TEAM_NAME --users $user --local > /dev/null 2>&1
done

# 2. Ensure Channels Exist
for channel in "${CHANNELS[@]}"; do
    display_name=$(jq -r ".channels[] | select(.name==\"$channel\") | .display_name" "$CONFIG_FILE")
    
    if ! /opt/mattermost/bin/mmctl channel search $TEAM_NAME $channel --local > /dev/null 2>&1; then
        echo "Creating channel $channel ($display_name) in team $TEAM_NAME..."
        /opt/mattermost/bin/mmctl channel create --team $TEAM_NAME --name $channel --display-name "$display_name" --local
    else
        echo "Channel $channel already exists in team $TEAM_NAME."
    fi
    
    # Add users to channel
    for user in "${USERS_TO_ADD[@]}"; do
        echo "Adding user $user to channel $channel..."
        /opt/mattermost/bin/mmctl channel users add $TEAM_NAME:$channel $user --local > /dev/null 2>&1
    done
done

# 4. Cleanup: Archive channels not in config
echo "Cleaning up deprecated channels..."
CONFIG_SLUGS=$(jq -r '.channels[].name' "$CONFIG_FILE")
ALLOWED_SLUGS=$(printf "%s\ntown-square\noff-topic" "$CONFIG_SLUGS")

# List all public channels and archive extras
EXISTING_CHANNELS=$(/opt/mattermost/bin/mmctl channel list "$TEAM_NAME" --local --json | jq -r '.[].name')

for channel in $EXISTING_CHANNELS; do
    if ! echo "$ALLOWED_SLUGS" | grep -qFx "$channel"; then
        echo "Archiving deprecated channel: $channel"
        /opt/mattermost/bin/mmctl channel archive "$TEAM_NAME:$channel" --local
    fi
done

echo "Mattermost channel provisioning and cleanup completed."

# 5. Bot Enrichment (incl. Profile Pictures & Tokens)
echo "Enriching bots (profile pictures, descriptions, tokens)..."
if command -v python3 &> /dev/null; then
    python3 "$(dirname "$0")/provision_mattermost.py"
elif command -v python &> /dev/null; then
    python "$(dirname "$0")/provision_mattermost.py"
else
    echo "Warning: Python not found. Skipping bot enrichment (profile pictures/tokens)."
fi

echo "Provisioning process finished."
