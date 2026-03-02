import os
import uuid
import time
import json
import base64
import csv
#import fitz
import re
import pandas as pd

# Handle imports for both local and Render deployment
try:
    from app import config
    from app import configure
except ImportError:
    import config
    import configure
#from PIL import Image
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Request
from fastapi.responses import FileResponse, JSONResponse

from google import genai
from google.genai import types

from typing import List, Dict


class PDFParser:
    def __init__(self):
        pass
    @staticmethod
    def pdf_to_img(pdf_files:list) :
        pass 


class Parser:
    @staticmethod
    def sanitize(content, imp=False):
        if content is None:
            return ""
        if isinstance(content, list):
            #find if null is present
            cont = []
            for value in content:
                if value is None:
                    if imp: cont.append("0")
                elif "-" in str(value) :
                    cont.append("0")
                else:
                    cont.append(str(value))
            return "|".join(cont)
        
        elif isinstance(content, str):
            if imp and ("-" in content or "_" in content): return "0"
            else: return content
        else: return str(content)

    @staticmethod
    def json_to_csv(json_content:list, csv_file_name=""):
        headers = ['id', 'name', 'father_name', 'opening_arrear', 'arv', 'total_demand', 'payment_date', 'payment_id', 'paid_opening', 'paid_arv', 'total_paid', 'closing_arrear']
        content_rows = []
        if isinstance(json_content, list):
            
            #sorted_content = sorted(json_content, key=lambda itm : int(itm.get("serial_number", "-1")))
            file_exists = os.path.isfile(csv_file_name)
            for rows in json_content:
                row_content = [
                    Parser.sanitize(rows.get("serial_number", "")),
                    Parser.sanitize(rows.get("name", "")),
                    Parser.sanitize(rows.get("father_name", "")),
                    Parser.sanitize(rows.get("outstanding", ""), imp=True),
                    Parser.sanitize(rows.get("annual_rental_value", ""), imp=True),
                    Parser.sanitize(rows.get("total_amount", ""), imp=True),
                    Parser.sanitize(rows.get("payment_deposit_date", ""), imp=True),
                    Parser.sanitize(rows.get("receipt_number", "")),
                    Parser.sanitize(rows.get("outstanding_deposited", ""), imp=True),
                    Parser.sanitize(rows.get("annual_rental_value_deposited", ""), imp=True),
                    Parser.sanitize(rows.get("total_amount_deposited", ""), imp=True),
                    Parser.sanitize(rows.get("total", ""), imp=True)
                ]
                
                content_rows.append(row_content)

            with open(csv_file_name, mode="a", newline='', encoding='utf-8') as file:
                writer = csv.writer(file, quoting=csv.QUOTE_MINIMAL)
                if not file_exists:
                    writer.writerow(headers)
                writer.writerows(content_rows)
            
            print("[DONE]  :)  ")

    @staticmethod
    def json_to_csv_2(json_content:list, csv_file_name=""):
        headers = ['id', 'name', 'father_name', 'house_type', 'area', 'arv_house', 'arv_water', 'opening_arrear_duration_house', 'opening_arrear_house', 'opening_arrear_duration_water', 'opening_arrear_water', 'total_opening_arrear', 'remarks']
        content_rows = []
        if isinstance(json_content, list):
            
            #sorted_content = sorted(json_content, key=lambda itm : int(itm.get("serial_number", "-1")))
            file_exists = os.path.isfile(csv_file_name)
            for rows in json_content:
                row_content = [
                    Parser.sanitize(rows.get("serial_number", "")),
                    Parser.sanitize(rows.get("name", "")),
                    Parser.sanitize(rows.get("father_name", "")),
                    Parser.sanitize(rows.get("house_type", ""), imp=True),
                    Parser.sanitize(rows.get("area", ""), imp=True),
                    Parser.sanitize(rows.get("arv_house", ""), imp=True),
                    Parser.sanitize(rows.get("arv_water", ""), imp=True),
                    Parser.sanitize(rows.get("opening_arrear_duration_house", ""), imp=True),
                    Parser.sanitize(rows.get("opening_arrear_house", ""), imp=True),
                    Parser.sanitize(rows.get("opening_arrear_duration_water", ""), imp=True),
                    Parser.sanitize(rows.get("opening_arrear_water", ""), imp=True),
                    Parser.sanitize(rows.get("total_opening_arrear", ""), imp=True),
                    Parser.sanitize(rows.get("remarks", ""), imp=True)
                ]
                
                content_rows.append(row_content)

            # with open(csv_file_name, mode="a", newline='', encoding='utf-8-sig') as file:
            #     writer = csv.writer(file, quoting=csv.QUOTE_MINIMAL)
            #     if not file_exists:
            #         writer.writerow(headers)
            #     writer.writerows(content_rows)

            
            df = pd.DataFrame(content_rows, columns=headers)
            df.to_excel(csv_file_name, index=False, engine='xlsxwriter')
   
            
            print("[DONE]  :)  ")


app = FastAPI(openapi_url=None, docs_url=None, redoc_url=None)
jobs: Dict[str, dict] = {}
client = None
config_params = None

ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png'}
DELAY_LLM_CALL = int(os.getenv("DELAY_LLM_CALL", "15"))
BASE_PATH = Path(__file__).resolve().parent
OUTPUT_FOLDER = BASE_PATH / "outputs"
OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)

API_KEY = os.getenv("CYCLOPS_API_KEY", "")
configure.configure_()

# Health check endpoint for Render
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "document-extractor"}




# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
SYSTEM_INSTRUCTION1 = (
    "You are a highly accurate document data extraction engine specialized in extracting structured data from tabular images, including handwritten tables."
    "You must strictly return machine-readable structured output."
    "Output Rules (MANDATORY):"
    "1. Do not transliterate any value, just keep the language of the values natively present in the document."
    "2. Output must be a valid JSON array."
    "3. Each element in the array must represent exactly one row of the table."
    "4. Each row must be a JSON object."
    "5. Keys must EXACTLY match the field names provided in the user prompt."
    "6. If multiple values exist within a single cell, return them as an array."
    "7. If a value is missing, unclear, or unreadable, return null."
    "8. Preserve the row order exactly as it appears (top to bottom)."
    "9. Do NOT include the header row as data."
    "10. Do NOT hallucinate or infer missing values."
    "11. Do NOT add extra keys."
    "12. Do NOT return explanations, markdown, comments, or any text outside the JSON."
    "13. Normalize numeric values by removing thousands separators unless they are part of decimal formatting."
    "14. Trim unnecessary whitespace."
    "15. Ignore decorative elements such as logos, footnotes, page numbers, or summary totals unless they belong to a data row."
    "Your response must contain ONLY valid JSON."
    )
    
USER_TEMPLATE1 = (
    "Extract structured tabular data from the provided image."
    "The image contains handwritten tabular data."
    "Remember there could be more than one value per field so capture it in array"
    "The JSON output must use EXACTLY the following field names:"
    "<FIELD_NAMES>['serial_number', 'name', 'father_name', 'house_type', 'area', 'arv_house', 'arv_water', 'opening_arrear_duration_house', 'opening_arrear_house', 'opening_arrear_duration_water, 'opening_arrear_water', 'total_opening_water', 'remarks']</FIELD_NAMES>"
    "Important:"
    "- Map table columns semantically to the above field names."
    "- In column 6, the subcolumn 1 is arv_house, subcolumn 2 is arv_water."
    "- In column 7, the subcolumn 1 contains two rows, 1st row(containing years) maps to opening_arrear_duration_house, seconds row(constaining amount) maps to opening_arrear_house."
    " - In column 7, the subcolumn 2 contains two rows, 1st row(contains years) maps to opening_arrear_duration_water, 2nd row(containing amount) maps to opening_arrear_water ."
    "- Column 8 contains total_opening_arrear."
    "- Column 9 maps to remarks."
    "- If multiple values exist in a column for a given row, return them as an array."
    "- Preserve row order from top to bottom."
    "- Make sure the serial_number should be a string only."
    "- There are hyphens present in certain columns, you need to replace these hyphens(-) or dashes(-) with integer '0'."
    "Return ONLY valid JSON."
    )
# ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
system_instruction = SYSTEM_INSTRUCTION1
user_template = USER_TEMPLATE1
# ==============================================================
def get_base64_string(image:bytes):
    encoded_data = base64.b64encode(image).decode('utf-8')
    return encoded_data

def parse_to_json(content:str) :
    try:
        content = json.loads(content)
        return content
    except Exception as e:
        print("[Error Parsing the JSON]")
        return [{}]

# ---------------------- call to LLM ---------------
def process_image(image_content_bytes: bytes, max_retries: int = 3):
    global user_template
    global config_params
    global client

    base64_data = get_base64_string(image_content_bytes)
    print("------------- Offloaded to LLM -------------------")

    if client:
        print("[CLIENT] : OK")

    for attempt in range(max_retries):
        try:
            strt_time = time.time()
            response = client.models.generate_content(
                model=config.MODEL_NAME,
                contents=[
                    types.Content(
                        role='user',
                        parts=[
                            types.Part(text=user_template),
                            types.Part(
                                inline_data=types.Blob(
                                    mime_type="image/png",
                                    data=base64_data,
                                ),
                                media_resolution={"level": "media_resolution_medium"}
                            )
                        ]
                    )
                ],
                config=config_params
            )
            end_time = time.time()
            print(f"[Inference Time] : {(end_time-strt_time):.2f}s")
            return response.text

        except Exception as e:
            print(f"[LLM Error] Attempt {attempt + 1}/{max_retries}: {e}")
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 5  # Exponential backoff: 5s, 10s, 15s
                print(f"[Retry] Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
            else:
                print("[LLM Error] All retries exhausted")
                raise

# --------------------- Helpers -------------------------
def process_job(job_id: str, filepaths: list):
    global jobs
    total = len(filepaths)
    jobs[job_id].update({'status': 'processing', 'total': total, 'done': 0, 'progress': 0})

    results = []

    for i, files in enumerate(filepaths):
        try :
            file_bytes = files['file_bytes']
            if file_bytes:
                result = process_image(file_bytes)
                parsed_result = parse_to_json(result)
                if isinstance(parsed_result, list):
                    results += parsed_result
        except Exception as e:
            # Add logger here to log the error
            print(e)
            results.append({})

        done = i + 1
        jobs[job_id]['done'] = done
        jobs[job_id]['progress'] = round((done/total) * 100)

        time.sleep(DELAY_LLM_CALL)

        # ------------ Handle file creation here ---------
    output_filename = f"results_{job_id}.xlsx"
    Parser.json_to_csv_2(results, csv_file_name=os.path.join(OUTPUT_FOLDER, output_filename))
    jobs[job_id].update(
        {
        'status': 'done',
        'progress': 100,
        'filename': output_filename,
        'download_url': f"/download/{output_filename}"
        })



def is_allowed(file_name : str) -> bool:
    global ALLOWED_EXTENSIONS
    return '.' in file_name and file_name.rsplit('.', maxsplit=1)[-1].lower() in ALLOWED_EXTENSIONS
    
# ------------------------- App Routes -----------------------

def conf():
    global client
    global config_params
    configure.configure_()
    client = genai.Client(vertexai=True, project=config.GEM_PROJECT_ID, location=config.GEM_LOCATION)
    config_params = types.GenerateContentConfig(system_instruction=system_instruction, response_mime_type="application/json")
    print("[CONFIGURATION] : OK")

conf()

@app.middleware('http')
async def handle_api_key(request : Request, call_next):
    global API_KEY
    api_key = request.headers.get("X-API-KEY", None)
    if request.url.path in ["/docs", "/openapi.json"]:
        return await call_next(request)
    
    if str(api_key) == str(API_KEY):
        response = await call_next(request)
        return response
    
    return JSONResponse(status_code=401, content={"detail":"Invalid or misssing API KEY"})
    
    
@app.post("/upload")
async def handle_file_upload(background_tasks:BackgroundTasks, files : List[UploadFile] = File(...)) :
    if not files:
        raise HTTPException(status_code=400, detail="No File Selected")

    file_list = []
    for file in files:
        filename = file.filename
        if is_allowed(filename):
            content_bytes = await file.read()
            file_stem = filename.rsplit('.', maxsplit=1)[0]

            file_list.append({'file_name' : file_stem, 'file_bytes' : content_bytes})
        
    if len(file_list) <= 0:
        raise HTTPException(status_code=400, detail="No valid files")
    
    try:
        file_list.sort(key=lambda fname : int(re.sub(r'\D', '', fname['file_name'])))
    except ValueError:
        file_list.sort(key=lambda fname : fname['file_name'])
    # ------------------ Offload to background thread ------------
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "status" : "queued",
        "total" : len(file_list),
        "done" : 0,
        "progress" : 0,
        "filename" : None,
        "download_url" : None
    }

    background_tasks.add_task(process_job, job_id, file_list)
    return {"job_id" : job_id}

@app.get("/status/{job_id}")
async def get_status(job_id:str) :
    job = jobs.get(job_id, None)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job    

@app.get("/download/{filename}")
async def download(filename:str):
    file_path = OUTPUT_FOLDER / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail='File not found')
    return FileResponse(path=str(file_path), filename=filename)
    



