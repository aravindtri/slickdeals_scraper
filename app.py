from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
import requests
import re
import json
import os
from dotenv import load_dotenv
import google.generativeai as genai
from urllib.parse import urlparse, parse_qs
from datetime import datetime
from typing import List

# Load environment variables from .env file
load_dotenv()

app = FastAPI()

# Configure Gemini
# NOTE: You must set the GOOGLE_API_KEY environment variable or in a .env file
if "GOOGLE_API_KEY" in os.environ:
    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])

@app.get("/")
async def read_index():
    file_path = os.path.join(os.path.dirname(__file__), "index.html")
    return FileResponse(file_path)

class ScrapeRequest(BaseModel):
    url: str
    max_pages: int = 10
    force_refresh: bool = False

class ChatRequest(BaseModel):
    filename: str
    message: str
    history: list = []
    use_summary: bool = False

class DeleteRequest(BaseModel):
    filenames: List[str]

@app.get("/files")
async def list_files():
    output_dir = os.path.join(os.path.dirname(__file__), "scraped_data")
    if not os.path.exists(output_dir):
        return []
    
    files = []
    for f in os.listdir(output_dir):
        if f.endswith(".json"):
            path = os.path.join(output_dir, f)
            try:
                # Get metadata
                stats = os.stat(path)
                mod_time = datetime.fromtimestamp(stats.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                
                # Read title (optional, might be slow if many files, but let's try)
                title = f
                try:
                    with open(path, 'r', encoding='utf-8') as json_file:
                        data = json.load(json_file)
                        title = data.get('deal_title', f)
                        # If title is empty or None, fallback to filename
                        if not title:
                            title = f
                except:
                    pass

                files.append({
                    "filename": f,
                    "title": title,
                    "modified": mod_time,
                    "size": stats.st_size
                })
            except Exception as e:
                print(f"Error reading {f}: {e}")
    
    # Sort by modified date desc
    files.sort(key=lambda x: x['modified'], reverse=True)
    return files

@app.post("/delete_files")
async def delete_files(request: DeleteRequest):
    output_dir = os.path.join(os.path.dirname(__file__), "scraped_data")
    deleted = []
    errors = []
    
    for filename in request.filenames:
        # Security check: prevent directory traversal
        if ".." in filename or "/" in filename or "\\" in filename:
            errors.append(f"Invalid filename: {filename}")
            continue
            
        path = os.path.join(output_dir, filename)
        try:
            if os.path.exists(path):
                os.remove(path)
                deleted.append(filename)
            else:
                errors.append(f"File not found: {filename}")
        except Exception as e:
            errors.append(f"Error deleting {filename}: {str(e)}")
            
    return {"deleted": deleted, "errors": errors}

@app.post("/delete_all_files")
async def delete_all_files():
    output_dir = os.path.join(os.path.dirname(__file__), "scraped_data")
    if not os.path.exists(output_dir):
        return {"deleted": 0}
        
    count = 0
    for f in os.listdir(output_dir):
        if f.endswith(".json"):
            try:
                os.remove(os.path.join(output_dir, f))
                count += 1
            except:
                pass
    return {"deleted": count}

@app.post("/chat")
async def chat_with_data(request: ChatRequest):
    if "GOOGLE_API_KEY" not in os.environ:
        raise HTTPException(status_code=500, detail="GOOGLE_API_KEY environment variable not set")

    file_path = os.path.join(os.path.dirname(__file__), "scraped_data", request.filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Data file not found")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to read data file")

    deal_title = data.get('deal_title', 'Unknown Deal')
    deal_description = data.get('deal_description', '')
    
    # Handle Summary Logic
    context_text = ""
    if request.use_summary:
        # Check if summary exists
        if "deal_summary" in data and data["deal_summary"]:
            context_text = f"SUMMARY OF COMMENTS:\n{data['deal_summary']}"
        else:
            # Generate summary on the fly (first time cost)
            comments_full = "\n".join([f"{c['author']}: {c['text']}" for c in data.get('comments', [])])
            if len(comments_full) > 30000:
                comments_full = comments_full[:30000] + "..."
                
            summary_prompt = f"""Summarize the following Slickdeals thread. 
            Focus on the general sentiment, key questions asked, answers given, and any important warnings or tips from users.
            
            Comments:
            {comments_full}
            """
            try:
                model = genai.GenerativeModel('gemini-2.0-flash')
                summary_resp = model.generate_content(summary_prompt)
                summary_text = summary_resp.text
                
                # Save summary to file for future use
                data["deal_summary"] = summary_text
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                
                context_text = f"SUMMARY OF COMMENTS:\n{summary_text}"
            except Exception as e:
                # Fallback if summary fails
                context_text = "Error generating summary. Using raw comments.\n" + comments_full
    else:
        # Use full comments
        comments_text = "\n".join([f"{c['author']} ({c['date']}): {c['text']}" for c in data.get('comments', [])])
        if len(comments_text) > 30000:
            comments_text = comments_text[:30000] + "...(truncated)"
        context_text = f"COMMENTS FROM USERS:\n{comments_text}"

    system_prompt = f"""You are a helpful assistant analyzing a Slickdeals thread.
    
    DEAL TITLE: {deal_title}
    
    DEAL DESCRIPTION:
    {deal_description}
    
    {context_text}
    
    Answer the user's questions based on the deal details and the user comments.
    """

    model = genai.GenerativeModel('gemini-2.0-flash')
    
    # Construct chat history for the model
    gemini_history = []
    for msg in request.history:
        role = "user" if msg.get("role") == "user" else "model"
        gemini_history.append({
            "role": role,
            "parts": [msg.get("content", "")]
        })
    
    # Optimization: Only send context in the first message of the history
    # If history is empty, we prepend context to the current message.
    # If history exists, we inject context into the first message of the history.
    
    if not gemini_history:
        # First message in the chat
        full_message = f"{system_prompt}\n\nUser Question: {request.message}"
        chat = model.start_chat(history=[])
        try:
            response = chat.send_message(full_message)
            return {"response": response.text}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Gemini API Error: {str(e)}")
    else:
        # Subsequent messages
        # Inject context into the first message of the history if it's not already there?
        # Since we are stateless, the 'history' passed from frontend is just Q/A pairs.
        # The frontend does NOT store the massive context block.
        # So we must inject it here so the model knows what we are talking about.
        
        # Modify the first user message in history to include context
        if gemini_history[0]["role"] == "user":
            original_first_msg = gemini_history[0]["parts"][0]
            # Check if context is already there (simple check)
            if "DEAL TITLE:" not in original_first_msg:
                gemini_history[0]["parts"][0] = f"{system_prompt}\n\nUser Question: {original_first_msg}"
        
        chat = model.start_chat(history=gemini_history)
        
        try:
            # Send ONLY the new question, as context is now in history
            response = chat.send_message(request.message)
            return {"response": response.text}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Gemini API Error: {str(e)}")

def resolve_ref(data, index):
    if isinstance(index, int) and 0 <= index < len(data):
        return data[index]
    return None

@app.post("/scrape")
async def scrape_comments(request: ScrapeRequest):
    base_url = request.url
    max_pages = request.max_pages
    force_refresh = request.force_refresh
    all_comments = []
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    # Clean base URL (remove existing query params if any, or handle them)
    if "?" in base_url:
        base_url = base_url.split("?")[0]

    # Generate unique filename based on URL
    # Extract ID from URL like .../f/123456-...
    deal_id_match = re.search(r'/f/(\d+)', base_url)
    if deal_id_match:
        filename = f"deal_{deal_id_match.group(1)}.json"
    else:
        # Fallback: sanitize the last part of the URL
        slug = base_url.split('/')[-1] if base_url.split('/')[-1] else base_url.split('/')[-2]
        # Keep only alphanumeric and dashes
        safe_slug = re.sub(r'[^a-zA-Z0-9\-]', '', slug)
        filename = f"scrape_{safe_slug[:50]}.json"

    # Ensure directory exists
    output_dir = os.path.join(os.path.dirname(__file__), "scraped_data")
    os.makedirs(output_dir, exist_ok=True)
    file_path = os.path.join(output_dir, filename)

    # Check cache
    if not force_refresh and os.path.exists(file_path):
        print(f"Returning cached data for {filename}")
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                cached_data = json.load(f)
                
                # Check if we need to re-scrape based on max_pages
                cached_max_pages = cached_data.get("max_pages_request", 0)
                if max_pages > cached_max_pages:
                    print(f"Requested max_pages ({max_pages}) > Cached max_pages ({cached_max_pages}). Force refreshing.")
                else:
                    cached_data["source"] = "cache"
                    return cached_data
        except Exception as e:
            print(f"Failed to read cache: {e}")
            # Continue to scrape if cache read fails

    seen_comments_hashes = set()
    deal_description = ""
    deal_title = ""

    for page in range(1, max_pages + 1):
        # Construct URL for pagination
        # Page 1 is usually just the base URL, but adding params works too.
        # Slickdeals uses ?sort=oldest&page=X
        current_url = f"{base_url}?sort=oldest&page={page}"
        print(f"Scraping page {page}: {current_url}")

        try:
            response = requests.get(current_url, headers=headers)
            response.raise_for_status()
            html_content = response.text
            
            # Check for redirects (e.g. requesting page 100 redirects to page 8)
            if page > 1:
                final_url = response.url
                parsed_final = urlparse(final_url)
                query_params = parse_qs(parsed_final.query)
                final_page_list = query_params.get('page')
                
                if final_page_list:
                    final_page = int(final_page_list[0])
                    if final_page != page:
                        print(f"Redirected to page {final_page} instead of {page}. Stopping.")
                        break
                else:
                    # If page param is missing but we asked for page > 1, we probably got redirected to page 1.
                    print(f"Redirected to page 1 (no page param) instead of {page}. Stopping.")
                    break

        except Exception as e:
            print(f"Failed to fetch page {page}: {e}")
            break

        # Regex to find the Nuxt data
        pattern = r'<script type="application/json" data-nuxt-data="nuxt-app" data-ssr="true" id="__NUXT_DATA__">(.+?)</script>'
        match = re.search(pattern, html_content)

        if not match:
            print(f"No NUXT data on page {page}")
            break

        try:
            json_string = match.group(1)
            data = json.loads(json_string)
        except json.JSONDecodeError:
            print(f"Failed to parse JSON on page {page}")
            break

        # Extract Deal Description and Title from Page 1
        if page == 1:
            try:
                # Find the object that has 'mainDesktopBlock'
                # Usually it's near the beginning, e.g. data[4]
                main_block_idx = -1
                for i, item in enumerate(data):
                    if isinstance(item, dict) and 'mainDesktopBlock' in item:
                        main_block_idx = item['mainDesktopBlock']
                        break
                
                if main_block_idx != -1:
                    main_block = resolve_ref(data, main_block_idx)
                    if isinstance(main_block, dict):
                        # Extract Title
                        if 'dealTitle' in main_block:
                            title_val = resolve_ref(data, main_block['dealTitle'])
                            if isinstance(title_val, str):
                                deal_title = title_val
                        
                        # Extract Body HTML
                        if 'bodyHtml' in main_block:
                            body_html = resolve_ref(data, main_block['bodyHtml'])
                            if isinstance(body_html, str):
                                # Simple HTML strip
                                clean_text = re.sub(r'<[^>]+>', ' ', body_html)
                                clean_text = re.sub(r'\s+', ' ', clean_text).strip()
                                deal_description = clean_text
                                print(f"Extracted Deal Title: {deal_title}")
                                print(f"Extracted Deal Description Length: {len(deal_description)}")
            except Exception as e:
                print(f"Error extracting description: {e}")

        page_comments = []
        new_comments_on_this_page = 0

        for item in data:
            if isinstance(item, dict):
                # Type A: Featured/Top comments
                if 'commentText' in item and 'author' in item:
                    author_idx = item.get('author')
                    text_idx = item.get('commentText')
                    
                    author = resolve_ref(data, author_idx) or ""
                    
                    # Resolve Text (Handle nested object)
                    raw_text_obj = resolve_ref(data, text_idx)
                    if isinstance(raw_text_obj, dict) and 'htmlContent' in raw_text_obj:
                        html_content_idx = raw_text_obj.get('htmlContent')
                        text = resolve_ref(data, html_content_idx) or ""
                    else:
                        text = raw_text_obj or ""
                        
                    date = ""

                    if 'timestampFormatted' in item:
                        date_idx = item.get('timestampFormatted')
                        date = resolve_ref(data, date_idx) or ""

                    # Create a unique hash for the comment
                    comment_hash = hash(f"{author}|{date}|{text}")
                    
                    if comment_hash not in seen_comments_hashes:
                        seen_comments_hashes.add(comment_hash)
                        new_comments_on_this_page += 1
                        page_comments.append({
                            "type": "Featured",
                            "author": author,
                            "text": text,
                            "date": date
                        })

                # Type B: Main comments
                # Changed elif to if to match PowerShell logic (capture both if present)
                if 'commentContent' in item and 'commentAuthor' in item:
                    author_obj_idx = item.get('commentAuthor')
                    text_idx = item.get('commentContent')
                    
                    author = ""
                    text = ""
                    date = ""

                    # Resolve Author
                    author_obj = resolve_ref(data, author_obj_idx)
                    if isinstance(author_obj, dict) and 'username' in author_obj:
                        username_idx = author_obj.get('username')
                        author = resolve_ref(data, username_idx) or ""
                    
                    # Resolve Text
                    # text_idx might point to a string OR an object containing htmlContent
                    raw_text_obj = resolve_ref(data, text_idx)
                    if isinstance(raw_text_obj, dict) and 'htmlContent' in raw_text_obj:
                        html_content_idx = raw_text_obj.get('htmlContent')
                        text = resolve_ref(data, html_content_idx) or ""
                    else:
                        text = raw_text_obj or ""

                    # Resolve Date
                    if 'commentSectionCommentFooter' in item:
                        footer_idx = item.get('commentSectionCommentFooter')
                        footer_obj = resolve_ref(data, footer_idx)
                        if isinstance(footer_obj, dict) and 'timestampFormatted' in footer_obj:
                            date_idx = footer_obj.get('timestampFormatted')
                            date = resolve_ref(data, date_idx) or ""

                    # Create a unique hash for the comment
                    comment_hash = hash(f"{author}|{date}|{text}")
                    
                    if comment_hash not in seen_comments_hashes:
                        seen_comments_hashes.add(comment_hash)
                        new_comments_on_this_page += 1
                        page_comments.append({
                            "type": "Main",
                            "author": author,
                            "text": text,
                            "date": date
                        })
        
        if new_comments_on_this_page == 0:
            print(f"No NEW comments found on page {page}. Stopping (Duplicate page detected).")
            break
            
        all_comments.extend(page_comments)

    result = {
        "deal_title": deal_title,
        "deal_description": deal_description,
        "count": len(all_comments),
        "comments": all_comments,
        "saved_to": filename,
        "source": "scrape",
        "max_pages_request": max_pages
    }
    
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
