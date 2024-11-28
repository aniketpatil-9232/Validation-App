import os
import re
import pyodbc
import pandas as pd
from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# Create the static directory if it doesn't exist
os.makedirs("static", exist_ok=True)

# Initialize FastAPI app
app = FastAPI()

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Allowed headers for validation
ALLOWED_HEADERS = ["CUSTOMER", "ADDRESS", "PRODUCT", "PRODUCT_TYPE", "PRICE"]

# SQL Server connection string (Windows Authentication)
connection_string = (
    r'DRIVER={ODBC Driver 17 for SQL Server};'
    r'SERVER=ANIKET\SQLEXPRESS;'
    r'DATABASE=file_validation_db;'
    r'Trusted_Connection=yes;'
)

# Database connection using pyodbc
def connect_to_db():
    conn = pyodbc.connect(connection_string)
    return conn.cursor()

# Validate file name
def validate_file_name(file_name: str) -> str:
    base_name = os.path.splitext(file_name)[0]
    if re.match(r"^[a-zA-Z0-9 ]+$", base_name):
        return "File name is valid. ✅"
    return "File name is invalid. ❌"

# Validate file size
def validate_file_size(uploaded_file: UploadFile) -> str:
    uploaded_file.file.seek(0, os.SEEK_END)
    file_size_kb = uploaded_file.file.tell() / 1024
    uploaded_file.file.seek(0)  # Reset file pointer
    if file_size_kb <= 10:
        return "File size is valid. ✅"
    return "File size must be under 10 KB. ❌"

# Validate headers
def validate_headers(data: pd.DataFrame) -> str:
    if list(data.columns) == ALLOWED_HEADERS:
        return "Headers matched. ✅"
    return "Headers are not matching. ❌"

# Check for null values
def check_null_values(data: pd.DataFrame) -> str:
    if data.isnull().values.any():
        return "Uploaded file contains null values. ❌"
    return "Uploaded file does not contain null values. ✅"

# Check for empty rows
def check_empty_rows(data: pd.DataFrame) -> str:
    data_cleaned = data.replace(r'^\s*$', pd.NA, regex=True).dropna(how='all')
    if len(data_cleaned) < len(data):
        return "Uploaded file contains empty rows. ❌"
    return "Uploaded file does not contain empty rows. ✅"

# Read .txt file with possible delimiters
def read_txt_file(file, delimiters=['\t', ',', ' ']) -> pd.DataFrame:
    for delimiter in delimiters:
        try:
            file.seek(0)
            df = pd.read_csv(file, delimiter=delimiter, skip_blank_lines=False)
            if list(df.columns) == ALLOWED_HEADERS:
                return df
        except Exception:
            continue
    raise ValueError("Failed to parse the .txt file with common delimiters (tab, comma, space).")

# Insert validation result into the database
def insert_validation_result(file_name: str, validation_rule: str, result: str):
    cursor = connect_to_db()
    cursor.execute("""
        INSERT INTO ValidationResults (file_name, validation_rule, result)
        VALUES (?, ?, ?)
    """, (file_name, validation_rule, result))
    cursor.connection.commit()

@app.post("/process-files/")
async def process_files(file_type: str, report_file: UploadFile):
    try:
        # File extension validation
        file_extension = os.path.splitext(report_file.filename)[1][1:].lower()
        if file_extension != file_type:
            validation_message = f"File type mismatch. Expected {file_type} file. ❌"
            insert_validation_result(report_file.filename, "File Type", validation_message)
            return JSONResponse(content={"error": validation_message})

        validation_results = []

        # Validate file name
        file_name_validation = validate_file_name(report_file.filename)
        insert_validation_result(report_file.filename, "File Name", file_name_validation)
        validation_results.append(file_name_validation)

        # Validate file size
        file_size_validation = validate_file_size(report_file)
        insert_validation_result(report_file.filename, "File Size", file_size_validation)
        validation_results.append(file_size_validation)

        # Read file content based on type
        if file_extension == "csv":
            data = pd.read_csv(report_file.file, skip_blank_lines=False)
        elif file_extension == "txt":
            data = read_txt_file(report_file.file)

        # Validate headers
        headers_validation = validate_headers(data)
        insert_validation_result(report_file.filename, "Headers", headers_validation)
        validation_results.append(headers_validation)

        # Check for null values
        null_values_check = check_null_values(data)
        insert_validation_result(report_file.filename, "Null Values", null_values_check)
        validation_results.append(null_values_check)

        # Check for empty rows
        empty_rows_check = check_empty_rows(data)
        insert_validation_result(report_file.filename, "Empty Rows", empty_rows_check)
        validation_results.append(empty_rows_check)

        # If any validation fails, return early
        if any("❌" in result for result in validation_results):
            message = f"""
            <h3 style="color: red;">File Rejected:</h3>
            <ul>
                {''.join(f'<li>{result}</li>' for result in validation_results if '❌' in result)}
            </ul>
            """
            return JSONResponse(content={"error": message})

        # If file passes all validations, insert all validation results into the database
        for result in validation_results:
            insert_validation_result(report_file.filename, "Validation", result)

        # Generate success response
        message = f"""
        <h3 style="color: #4CAF50;">File Validation Results:</h3>
        <ul>
            {''.join(f'<li>{result}</li>' for result in validation_results)}
        </ul>
        """
        return JSONResponse(content={"message": message})

    except ValueError as ve:
        return JSONResponse(content={"error": f"{str(ve)} ❌"})
    except Exception as e:
        return JSONResponse(content={"error": f"An unexpected error occurred: {str(e)} ❌"})

@app.get("/", response_class=HTMLResponse)
async def index():
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>File Validation App</title>
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background-color: #f2f7fb;
                margin: 0;
                padding: 0;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
            }
            .container {
                background-color: white;
                padding: 30px;
                border-radius: 12px;
                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
                width: 100%;
                max-width: 600px;
                text-align: center;
            }
            h2 {
                color: #4CAF50;
                font-size: 24px;
                margin-bottom: 20px;
                font-weight: 600;
            }
            label {
                font-weight: 500;
                display: block;
                margin-top: 20px;
                margin-bottom: 10px;
                font-size: 16px;
            }
            select, input[type="file"] {
                padding: 12px 20px;
                font-size: 16px;
                border: 1px solid #ddd;
                border-radius: 8px;
                width: 100%;
                box-sizing: border-box;
                margin-bottom: 20px;
            }
            button {
                margin-top: 20px;
                padding: 12px 20px;
                border: none;
                border-radius: 8px;
                background-color: #007BFF;
                color: white;
                font-size: 16px;
                cursor: pointer;
                width: 100%;
            }
            button:hover {
                background-color: #0056b3;
            }
            #output {
                margin-top: 30px;
                text-align: left;
            }
            #output p {
                font-size: 18px;
                font-weight: 500;
            }
        </style>
        <script>
            function updateFileAccept() {
                const fileType = document.getElementById("file_type").value;
                const fileInput = document.getElementById("report_file");
                fileInput.accept = fileType === "txt" ? ".txt" : ".csv";
            }

            async function handleFormSubmit(event) {
                event.preventDefault();
                const formData = new FormData(event.target);

                document.getElementById("output").innerHTML = "<p>Processing file...</p>";

                const response = await fetch(`/process-files/?file_type=${formData.get("file_type")}`, {
                    method: "POST",
                    body: formData
                });

                const result = await response.json();
                document.getElementById("output").innerHTML = result.error || result.message;
            }
        </script>
    </head>
    <body>
        <div class="container">
            <h2>File Validation</h2>
            <form onsubmit="handleFormSubmit(event)">
                <label for="file_type">Select file type:</label>
                <select id="file_type" name="file_type" onchange="updateFileAccept()">
                    <option value="csv">CSV</option>
                    <option value="txt">TXT</option>
                </select>
                <label for="report_file">Choose file:</label>
                <input type="file" id="report_file" name="report_file" accept=".csv,.txt" required>
                <button type="submit">Upload and Validate</button>
            </form>
            <div id="output"></div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)



# Run the app (for development/testing)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001)
