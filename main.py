from pathlib import Path
import json
import time
import uuid
import re
from datetime import datetime
import shutil
import os
from urllib.parse import unquote

planet_path = Path("~/Library/Containers/xyz.planetable.Planet/Data/Documents/Planet").expanduser()
if not planet_path.exists():
    raise FileNotFoundError(f"Could not find Planet files at {str(planet_path)}.")

my_path = planet_path / "My"
public_path = planet_path / "Public"

# List the user's planets
planet_uuids = {}
for idx, file in enumerate(my_path.iterdir()):
    planet_uuids[idx] = file.name
    planet_json = file / "planet.json"
    with planet_json.open(mode="r") as f:
        planet_data = json.load(f)
        print(f"{idx+1}: {planet_data['name']}")

# Find the planet the user wants to write to
while True:
    idx = input("Which Planet would you like to write to?\n> ") # pyright: ignore
    if int(idx)-1 in planet_uuids.keys():
        break
    print("Invalid selection. Please try again.")

planet_uuid = planet_uuids[int(idx)-1]
planet_my = my_path / planet_uuid
planet_public = public_path / planet_uuid

# Get the path to the notion export
while True:
    p = input("Enter the path to your Notion export:\n> ")
    notion_export = Path(p).expanduser()
    if notion_export.exists() and notion_export.is_dir():
        break
    print("Invalid path (either does not exist or isn't a directory). Please try again.")

# Find the media dir
for path in notion_export.iterdir():
    if path.is_dir():
        notion_media = path
        break

# Make sure we found the media dir
if not notion_media:
    raise FileNotFoundError("Could not find the Notion media directory.")

for item in notion_media.iterdir():
    if item.suffix != ".md":
        continue

    item_id = str(uuid.uuid4()).upper() # Generate a random UUID
    planet_item = {
        "articleType": 0, # blog post
        "id": item_id,
        "link": "/" + item_id + "/",
    }
    
    itemstr = item.open(mode="r").read() # read file

    # Get the title
    title_search = re.search("^# (.+)$", itemstr, re.MULTILINE)
    planet_item["title"] = title_search.group(0)[2:] if title_search else ""
    
    # Get the audio attached to the post
    file_search = re.search("^File: (.+)$", itemstr, re.MULTILINE)
    file = file_search.group(0)[6:] if file_search else ""
    file = unquote(file) # unquote for %20 -> spaces

    # Copy the audio file to this planet's public directory
    file_path = notion_media / file
    if file and file_path.exists():
        destination_dir = planet_public / item_id
        os.makedirs(destination_dir, exist_ok=True)
        destination_path = destination_dir / file
        shutil.copyfile(file_path, destination_path)
        planet_item["attachments"] = [file]
    else:
        print(f"Could not find file {file} for item {str(item)}. Skipping.")
    
    # Get the date of the post
    date_search = re.search("^Date: (.+)$", itemstr, re.MULTILINE)
    if date_search:
        date_string = date_search.group(0)[6:]
        date_object = datetime.strptime(date_string, "%B %d, %Y")
    
    timestamp = datetime.timestamp(date_object) if date_object else time.time() # Use current time if no date found
    planet_item["created"] = int(timestamp) - 978307200 # Time since 2001-01-01 (swift epoch)
    
    # Get the post content
    split_item = itemstr.split("\n\n")
    planet_item["content"] = "\n\n".join(split_item[2:]) if len(split_item) > 2 else ""
    
    # Write the planet item
    with open(str(planet_my / "Articles" / item_id) +".json", "w") as f:
        json.dump(planet_item, f)
        
print("Done!")