import os
import json
import urllib.request
import urllib.error
import time
import random
import logging
import re
from typing import Optional, Dict, Any, List
from famiglia_core.command_center.backend.comms.slack.client import slack_queue, PRIORITY_HIGH
from famiglia_core.db.tools.user_connections_store import user_connections_store

logger = logging.getLogger("notion_client")

class NotionIntegration:
    """Manages connections and transactions with the Notion API using standard library."""
    def __init__(self):
        self.base_url = "https://api.notion.com/v1"

    def _get_headers(self, agent_name: Optional[str] = None) -> Dict[str, str]:
        # 1. Priority: Check if the human user has connected their Notion account via OAuth
        connection = user_connections_store.get_connection("notion")
        if connection and connection.get("access_token"):
            print(f"[Notion] Using human user OAuth connection (workspace: {connection.get('username')})")
            token = connection["access_token"]
        else:
            # 2. Secondary: Fallback to agent-specific or default bot tokens
            token = None
            if agent_name:
                env_var = f"NOTION_API_KEY_{agent_name.upper()}"
                token = os.getenv(env_var)
                if token:
                    print(f"[Notion] Using agent-specific key for {agent_name} ({env_var})")
            
            if not token:
                token = os.getenv("NOTION_API_KEY_ROSSINI")
                if token:
                    print(f"[Notion] Falling back to default NOTION_API_KEY_ROSSINI")
            
        if not token:
            raise ValueError("No Notion API Key found (no user connection and no bot tokens).")
            
        return {
            "Authorization": f"Bearer {token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"
        }

    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None, max_retries: int = 3, agent_name: Optional[str] = None) -> Dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers(agent_name=agent_name)
        
        req_data = None
        if data is not None:
            req_data = json.dumps(data).encode("utf-8")
            
        timeout = 30 # 30 seconds timeout
        for attempt in range(max_retries + 1):
            req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
            try:
                with urllib.request.urlopen(req, timeout=timeout) as response:
                    return json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                error_body = e.read().decode("utf-8")
                
                # Handle Rate Limit (HTTP 429)
                if e.code == 429:
                    if attempt < max_retries:
                        # Extract Retry-After if present, else exponential backoff
                        retry_after = e.headers.get("Retry-After")
                        wait_time = int(retry_after) if retry_after and retry_after.isdigit() else (2 ** attempt) + random.random()
                        
                        error_msg = f"⚠️ Notion API rate limit hit. Throttling for {wait_time:.1f}s before retrying... (Attempt {attempt + 1}/{max_retries})"
                        print(f"[Notion] {error_msg}")
                        
                        # Notify user via Slack to manage expectations
                        # We use a system-level high priority message
                        slack_queue.enqueue_message(
                            agent="rossini", 
                            channel=os.getenv("DEV_CHANNEL_ID", "system"), # Fallback to system logs if no channel
                            message=error_msg,
                            priority=PRIORITY_HIGH
                        )
                        
                        time.sleep(wait_time)
                        continue
                    else:
                        raise Exception(f"Notion API Rate Limit Exceeded after {max_retries} retries. Please wait before trying again.")
                
                raise Exception(f"Notion API HTTP Error {e.code}: {error_body}")
            except urllib.error.URLError as e:
                 raise Exception(f"Notion API Network Error: {e.reason}")
        
        return {} # Should not reach here

    def read_page(self, page_id: str, agent_name: str = "Unknown Bot") -> Dict[str, Any]:
        """Reads properties and content blocks of a given Notion page."""
        print(f"[{agent_name}] Reading Notion page: {page_id}")
        result = {"page_properties": {}, "blocks": []}
        
        try:
            # 1. Page Properties
            page = self._make_request("GET", f"/pages/{page_id}", agent_name=agent_name)
            for prop_name, prop_data in page.get("properties", {}).items():
                val = self._extract_property_value(prop_data)
                result["page_properties"][prop_name] = val
                
            # 2. Page Content Blocks
            blocks_resp = self._make_request("GET", f"/blocks/{page_id}/children", agent_name=agent_name)
            for block in blocks_resp.get("results", []):
                bid = block.get("id")
                text_content = self._extract_block_text(block)
                if text_content:
                    result["blocks"].append({
                        "id": bid,
                        "text": text_content,
                        "type": block.get("type")
                    })
                    
            result["url"] = page.get("url")
            return result
        except Exception as e:
            raise Exception(f"Notion API Error: {str(e)}")

    def list_comments(self, block_id: str, agent_name: str = "Unknown Bot", deep_scan: bool = False) -> List[Dict[str, Any]]:
        """
        Retrieves comments for a given block or page ID.
        If deep_scan is True, it performs a BFS to fetch comments for all nested blocks.
        """
        print(f"[{agent_name}] [notion.py v2.6] Listing comments for block/page: {block_id} (deep_scan={deep_scan})")
        all_comments = []
        
        def get_block_comments(bid):
            try:
                response = self._make_request("GET", f"/comments?block_id={bid}", agent_name=agent_name)
                results = response.get("results", [])
                found = []
                for comment in results:
                    rich_text = comment.get("rich_text", [])
                    text = "".join([t.get("plain_text", "") for t in rich_text])
                    found.append({
                        "id": comment.get("id"),
                        "discussion_id": comment.get("discussion_id"),
                        "text": text,
                        "created_at": comment.get("created_time"),
                        "author": comment.get("created_by", {}).get("object"),
                        "author_type": comment.get("created_by", {}).get("type", "unknown"),
                        "parent_block_id": bid
                    })
                return found
            except Exception as e:
                print(f"[{agent_name}] Error fetching comments for block {bid}: {e}")
                return []

        # 1. Get starting comments
        all_comments.extend(get_block_comments(block_id))
        
        # 2. Recursive/Queue-based scanning
        if deep_scan:
            # Use a queue for BFS to avoid recursion depth issues
            queue = [block_id]
            scanned_blocks = 0
            max_blocks = 200 # Safety limit
            
            while queue and scanned_blocks < max_blocks:
                current_id = queue.pop(0)
                try:
                    children_resp = self._make_request("GET", f"/blocks/{current_id}/children?page_size=100", agent_name=agent_name)
                    for block in children_resp.get("results", []):
                        bid = block["id"]
                        scanned_blocks += 1
                        
                        # Fetch comments for this block
                        all_comments.extend(get_block_comments(bid))
                        
                        # If block has children, add to queue for further scanning
                        if block.get("has_children"):
                            queue.append(bid)
                            
                except Exception as e:
                    print(f"[{agent_name}] Scan error for block {current_id}: {e}")

        # deduplicate by ID just in case
        unique = []
        seen = set()
        for c in all_comments:
            if c["id"] not in seen:
                unique.append(c)
                seen.add(c["id"])
                
        return unique

    def search(self, query: str = "", agent_name: str = "Unknown Bot") -> List[Dict[str, Any]]:
        """General search across all accessible pages and databases."""
        print(f"[{agent_name}] Searching Notion for '{query}'")
        try:
            payload = {"query": query, "page_size": 20}
            response = self._make_request("POST", "/search", data=payload, agent_name=agent_name)
            results = []
            for item in response.get("results", []):
                obj_type = item.get("object", "unknown")
                item_data = {"id": item["id"], "url": item.get("url"), "type": obj_type}
                
                # Extract title - try multiple common patterns
                title = ""
                if obj_type == "page":
                    props = item.get("properties", {})
                    # Try standard "title" property
                    title_list = props.get("title", {}).get("title", [])
                    title = "".join([t.get("plain_text", "") for t in title_list])
                    
                    # If still empty, scan all properties for type=title
                    if not title:
                        for prop_name, prop_data in props.items():
                            if prop_data.get("type") == "title":
                                rich_texts = prop_data.get("title", [])
                                title = "".join([t.get("plain_text", "") for t in rich_texts])
                                if title:
                                    break
                    
                    # Also check parent for database entries
                    if not title:
                        # Fall back to checking "Name" property
                        title_list = props.get("Name", {}).get("title", [])
                        title = "".join([t.get("plain_text", "") for t in title_list])
                        
                elif obj_type == "database":
                    title_list = item.get("title", [])
                    title = "".join([t.get("plain_text", "") for t in title_list])
                
                item_data["title"] = title
                if title:
                    print(f"[{agent_name}] Notion search result: '{title}' ({item['id']})")
                results.append(item_data)
            return results
        except Exception as e:
            raise Exception(f"Notion API Error: {str(e)}")

    def search_database(self, database_id: str, query: str = "", agent_name: str = "Unknown Bot") -> List[Dict[str, Any]]:
        """Queries a database."""
        print(f"[{agent_name}] Searching Notion database: {database_id} with query '{query}'")
        try:
            payload = {}
            # If query is a generic string search (not a specific Notion filter) we let the script do it. 
            # In Notion API, plain text search across database rows is complex, so we fetch all and filter locally for simplicity.
            response = self._make_request("POST", f"/databases/{database_id}/query", data=payload, agent_name=agent_name)
            results = []
            
            for page in response.get("results", []):
                page_data = {"id": page["id"], "url": page["url"], "properties": {}}
                for prop_name, prop_data in page.get("properties", {}).items():
                    page_data["properties"][prop_name] = self._extract_property_value(prop_data)
                
                # Simple text search fallback
                if not query or query.lower() in str(page_data).lower():
                    results.append(page_data)
                    
            return results
        except Exception as e:
            raise Exception(f"Notion API Error: {str(e)}")

    def list_spaces(self, agent_name: str = "Unknown Bot") -> str:
        """List all top-level Notion pages and databases accessible to the integration."""
        print(f"[{agent_name}] Listing accessible Notion spaces")
        try:
            # Search with no filter returns all accessible objects
            payload = {"page_size": 20}
            response = self._make_request("POST", "/search", data=payload, agent_name=agent_name)
            results = response.get("results", [])
            if not results:
                return "No accessible Notion pages or databases found. Ensure the Notion integration has access to your workspace."

            lines = []
            for item in results:
                obj_type = item.get("object", "unknown")  # 'page' or 'database'
                item_id = item.get("id", "unknown")
                # Extract title from properties
                if obj_type == "page":
                    title_list = item.get("properties", {}).get("title", {}).get("title", [])
                    title = "".join([t.get("plain_text", "") for t in title_list]) or "(Untitled)"
                elif obj_type == "database":
                    title_list = item.get("title", [])
                    title = "".join([t.get("plain_text", "") for t in title_list]) or "(Untitled Database)"
                else:
                    title = "(Unknown)"
                lines.append(f"- [{obj_type}] {title} (id: {item_id})")
            return "Accessible Notion spaces:\n" + "\n".join(lines)
        except Exception as e:
            raise Exception(f"Notion API Error: {str(e)}")

    def _markdown_to_blocks(self, markdown_text: str) -> List[Dict[str, Any]]:
        """Parses Markdown text into Notion blocks, respecting character limits and inline bolding."""
        blocks = []
        limit = 2000

        def parse_rich_text(text: str) -> List[Dict[str, Any]]:
            """Parses **bold** and `code` text into a list of rich_text objects for Notion."""
            import re
            # Split by either **bold** or `code` markers
            parts = re.split(r'(\*\*.*?\*\*|`.*?`)', text)
            rich_text = []
            
            for part in parts:
                if not part:
                    continue
                
                is_bold = part.startswith('**') and part.endswith('**')
                is_code = part.startswith('`') and part.endswith('`')
                
                if is_bold:
                    content = part[2:-2]
                elif is_code:
                    content = part[1:-1]
                else:
                    content = part
                
                if not content:
                    continue
                
                # Further safety: truncate if a single segment is somehow huge
                content = content[:limit]
                
                annotations = {}
                if is_bold:
                    annotations["bold"] = True
                if is_code:
                    annotations["code"] = True
                
                block_data = {
                    "type": "text",
                    "text": {"content": content}
                }
                if annotations:
                    block_data["annotations"] = annotations
                    
                rich_text.append(block_data)
            return rich_text

        def create_block(btype: str, content: str) -> Dict[str, Any]:
            return {
                "object": "block",
                "type": btype,
                btype: {
                    "rich_text": parse_rich_text(content)
                }
            }

        def parse_table(rows: List[str]) -> Dict[str, Any]:
            """Converts Markdown table rows into a Notion table block."""
            table_rows = []
            max_cols = 0
            
            # Clean and filter rows (ignore separators like |---|---|)
            cleaned_rows = []
            for row in rows:
                if re.match(r'^\s*\|?\s*:?-+:?\s*(\|?\s*:?-+:?\s*)*\|?\s*$', row):
                    continue
                cleaned_rows.append(row)

            for row in cleaned_rows:
                # Split by | and filter out empty strings from the ends
                cells = [c.strip() for c in row.split('|')]
                if row.strip().startswith('|'):
                    cells = cells[1:]
                if row.strip().endswith('|'):
                    cells = cells[:-1]
                
                if not cells:
                    continue
                
                max_cols = max(max_cols, len(cells))
                table_row = {
                    "type": "table_row",
                    "table_row": {
                        "cells": [parse_rich_text(cell) for cell in cells]
                    }
                }
                table_rows.append(table_row)

            if not table_rows:
                return None

            return {
                "object": "block",
                "type": "table",
                "table": {
                    "table_width": max_cols,
                    "has_column_header": True,
                    "has_row_header": False,
                    "children": table_rows
                }
            }

        lines = markdown_text.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            
            if not stripped:
                i += 1
                continue

            # Code Block Detection
            if stripped.startswith("```"):
                language = stripped[3:].strip() or "plain text"
                code_content = []
                i += 1
                while i < len(lines) and not lines[i].strip().startswith("```"):
                    code_content.append(lines[i])
                    i += 1
                
                # Close the code block
                if i < len(lines):
                    i += 1
                
                blocks.append({
                    "object": "block",
                    "type": "code",
                    "code": {
                        "rich_text": [{"type": "text", "text": {"content": "\n".join(code_content)}}],
                        "language": language if language != "sql" else "sql" # ensure sql is supported
                    }
                })
                continue

            # Table Detection
            if stripped.startswith('|'):
                table_lines = []
                # Keep collecting lines that look like table rows, allowing for 1 blank line in between
                while i < len(lines):
                    current_line = lines[i]
                    if current_line.strip().startswith('|'):
                        table_lines.append(current_line)
                    elif not current_line.strip() and i + 1 < len(lines) and lines[i+1].strip().startswith('|'):
                        # Skip single blank line if followed by a table row
                        pass
                    else:
                        break
                    i += 1
                
                table_block = parse_table(table_lines)
                if table_block:
                    blocks.append(table_block)
                continue

            # Headers
            if stripped.startswith("#### "):
                # Notion doesn't support heading_4, fallback to heading_3
                blocks.append(create_block("heading_3", stripped[5:]))
            elif stripped.startswith("### "):
                blocks.append(create_block("heading_3", stripped[4:]))
            elif stripped.startswith("## "):
                blocks.append(create_block("heading_2", stripped[3:]))
            elif stripped.startswith("# "):
                blocks.append(create_block("heading_1", stripped[2:]))
            
            # Bullet points
            elif stripped.startswith("- ") or stripped.startswith("* "):
                blocks.append(create_block("bulleted_list_item", stripped[2:]))
            
            # Regular paragraph
            else:
                # If too long, chunk it
                if len(line) > limit:
                    for j in range(0, len(line), limit):
                        blocks.append(create_block("paragraph", line[j:j+limit]))
                else:
                    blocks.append(create_block("paragraph", line))
            i += 1
        
        return blocks

    def _text_to_blocks(self, text: str, agent_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Backwards compatibility wrapper that now uses the markdown parser."""
        prefix = f"[{agent_name}] " if agent_name else ""
        return self._markdown_to_blocks(prefix + text)

    def append_text_to_page(self, page_id: str, text: str, agent_name: str = "Unknown Bot") -> str:
        """Appends text blocks to a page, handling length and block count limits."""
        print(f"[{agent_name}] [notion.py v2.5] Appending text to Notion page: {page_id}")
        try:
            blocks = self._text_to_blocks(text, agent_name)
            print(f"[{agent_name}] [notion.py v2.5] Generated {len(blocks)} blocks total.")
            
            # Notion API has a limit of 100 blocks per request
            chunk_size = 100
            for i in range(0, len(blocks), chunk_size):
                chunk = blocks[i:i + chunk_size]
                payload = {"children": chunk}
                print(f"[{agent_name}] Sending chunk {i//chunk_size + 1} ({len(chunk)} blocks) to Notion...")
                self._make_request("PATCH", f"/blocks/{page_id}/children", data=payload, agent_name=agent_name)
                
            return f"Successfully appended {len(blocks)} blocks to Notion page {page_id}."
        except Exception as e:
            raise Exception(f"Notion API Error: {str(e)}")

    def archive_block(self, block_id: str, agent_name: str = "Unknown Bot") -> bool:
        """Archives (deletes) a specific block."""
        try:
            self._make_request("DELETE", f"/blocks/{block_id}", agent_name=agent_name)
            return True
        except Exception as e:
            print(f"[{agent_name}] Failed to archive block {block_id}: {e}")
            return False

    def update_block(self, block_id: str, markdown_text: str, agent_name: str = "Unknown Bot", expected_type: Optional[str] = None) -> bool:
        """
        Updates a specific block's content using markdown.
        Note: Notion block updates only change the block's own properties (e.g. text),
        it doesn't change the block type easily unless we reconstruct.
        For simplicity, we assume text blocks and force the payload to match the original block type.
        """
        print(f"[{agent_name}] [notion.py v2.5] Updating block: {block_id}")
        try:
            # We use the first block generated from markdown (usually a paragraph or header)
            dummy_blocks = self._markdown_to_blocks(markdown_text)
            if not dummy_blocks:
                return False
            
            target_block = dummy_blocks[0]
            btype = target_block["type"]
            
            if not expected_type:
                try:
                    current_block = self._make_request("GET", f"/blocks/{block_id}", agent_name=agent_name)
                    expected_type = current_block.get("type", btype)
                except Exception as e:
                    print(f"[{agent_name}] Could not fetch current block type for {block_id}: {e}")
                    expected_type = btype
            
            if expected_type != btype:
                print(f"[{agent_name}] Block type mismatch (got {btype}, expected {expected_type}). Forcing {expected_type}.")
                rich_text = target_block.get(btype, {}).get("rich_text", [])
                payload = {
                    expected_type: {
                        "rich_text": rich_text
                    }
                }
            else:
                payload = {
                    expected_type: target_block[btype]
                }
            
            self._make_request("PATCH", f"/blocks/{block_id}", data=payload, agent_name=agent_name)
            return True
        except Exception as e:
            print(f"[{agent_name}] Failed to update block {block_id}: {e}")
            return False

    def replace_page_content(self, page_id: str, text: str, agent_name: str = "Unknown Bot") -> str:
        """
        Replaces all content on a page by archiving old blocks and appending new ones.
        """
        print(f"[{agent_name}] [notion.py v2.5] Replacing content on page: {page_id}")
        try:
            # 1. Get current children
            resp = self._make_request("GET", f"/blocks/{page_id}/children?page_size=100", agent_name=agent_name)
            children = resp.get("results", [])
            
            # 2. Archive all children
            if children:
                print(f"[{agent_name}] [notion.py v2.3] Archiving {len(children)} existing blocks...")
                for block in children:
                    self.archive_block(block["id"], agent_name=agent_name)
            
            # 3. Append new content
            return self.append_text_to_page(page_id, text, agent_name=agent_name)
        except Exception as e:
            raise Exception(f"Notion API Error (replace_page_content): {str(e)}")

    def create_page(self, parent_page_id: str, title: str, text: str = "", agent_name: str = "Unknown Bot", properties: Optional[Dict[str, Any]] = None) -> str:
        """Creates a new Notion page with potentially long content and custom properties."""
        print(f"[{agent_name}] Creating new Notion page '{title}' under parent {parent_page_id}")
        try:
            # Default properties with title
            page_properties = {
                "title": {
                    "title": [
                        {"type": "text", "text": {"content": title}}
                    ]
                }
            }
            
            # Merge extra properties if provided
            if properties:
                page_properties.update(properties)

            payload = {
                "parent": {"type": "page_id", "page_id": parent_page_id},
                "properties": page_properties
            }
            
            if text:
                all_blocks = self._text_to_blocks(text, agent_name)
                # Max 100 children in create_page request
                payload["children"] = all_blocks[:100]
                remaining_blocks = all_blocks[100:]
            else:
                remaining_blocks = []
                
            response = self._make_request("POST", "/pages", data=payload, agent_name=agent_name)
            new_page_id = response.get("id", "Unknown")
            new_page_url = response.get("url", "Unknown")
            
            # Append remaining blocks if any
            if remaining_blocks:
                print(f"[{agent_name}] Page created. Appending remaining {len(remaining_blocks)} blocks...")
                chunk_size = 100
                for i in range(0, len(remaining_blocks), chunk_size):
                    chunk = remaining_blocks[i:i + chunk_size]
                    append_payload = {"children": chunk}
                    self._make_request("PATCH", f"/blocks/{new_page_id}/children", data=append_payload, agent_name=agent_name)
            
            return f"Successfully created Notion page '{title}' with ID: {new_page_id}. URL: {new_page_url}"
        except Exception as e:
            # Fallback if page_id fails but it might be a database_id
            if "parent" in str(e):
                 try:
                     payload["parent"] = {"type": "database_id", "database_id": parent_page_id}
                     response = self._make_request("POST", "/pages", data=payload, agent_name=agent_name)
                     new_page_id = response.get("id", "Unknown")
                     new_page_url = response.get("url", "Unknown")
                     return f"Successfully created Notion page '{title}' with ID: {new_page_id} (Database). URL: {new_page_url}"
                 except:
                     pass
            raise Exception(f"Notion API Error: {str(e)}")

    def update_page_properties(self, page_id: str, properties: Dict[str, Any], agent_name: str = "Unknown Bot") -> Dict[str, Any]:
        """
        Updates properties of a given page.
        Properties should be formatted for the Notion API.
        """
        print(f"[{agent_name}] [notion.py v2.6] Updating properties for page: {page_id}")
        payload = {"properties": properties}
        try:
            return self._make_request("PATCH", f"/pages/{page_id}", data=payload, agent_name=agent_name)
        except Exception as e:
            print(f"[{agent_name}] Failed to update properties for page {page_id}: {e}")
            raise Exception(f"Notion API Error (update_page_properties): {str(e)}")

    def create_comment(self, text: str, page_id: Optional[str] = None, discussion_id: Optional[str] = None, agent_name: str = "Unknown Bot") -> Dict[str, Any]:
        """
        Creates a new comment. 
        - If page_id is provided, it creates a new page-level comment.
        - If discussion_id is provided, it creates a reply in that discussion thread.
        """
        print(f"[{agent_name}] Creating comment (page_id={page_id}, discussion_id={discussion_id})")
        
        if not page_id and not discussion_id:
            raise ValueError("Either page_id or discussion_id must be provided to create a comment.")

        # Construct payload
        payload = {
            "rich_text": [
                {
                    "type": "text",
                    "text": {"content": text}
                }
            ]
        }

        if discussion_id:
            payload["discussion_id"] = discussion_id
        else:
            payload["parent"] = {"page_id": page_id}
        
        try:
            return self._make_request("POST", "/comments", data=payload, agent_name=agent_name)
        except Exception as e:
            raise Exception(f"Notion API Error (create_comment): {str(e)}")

    def _extract_property_value(self, prop_data: dict) -> Any:
        prop_type = prop_data.get("type", "")
        if prop_type == "title":
            return "".join([t["plain_text"] for t in prop_data.get("title", [])])
        elif prop_type == "rich_text":
            return "".join([t["plain_text"] for t in prop_data.get("rich_text", [])])
        elif prop_type == "number":
            return prop_data.get("number")
        elif prop_type == "select":
            return prop_data.get("select", {}).get("name") if prop_data.get("select") else None
        elif prop_type == "multi_select":
            return [ms["name"] for ms in prop_data.get("multi_select", [])]
        elif prop_type == "date":
            date_dict = prop_data.get("date")
            return date_dict.get("start") if date_dict else None
        elif prop_type == "url":
            return prop_data.get("url")
        return str(prop_data)

    def _extract_block_text(self, block: dict) -> Optional[str]:
        block_type = block.get("type")
        if not block_type or block_type not in block:
            return None
            
        type_data = block[block_type]
        if "rich_text" in type_data:
            return "".join([t.get("plain_text", "") for t in type_data.get("rich_text", [])])
        return None

notion_client = NotionIntegration()
