FROM python:3.11-slim

# Install required packages including ODBC Driver for SQL Server
RUN apt-get update && apt-get install -y \
    curl \
    apt-transport-https \
    gnupg2 \
    ca-certificates

RUN curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add -
RUN curl https://packages.microsoft.com/mssql-server/debian/mssql-server-2019.list > /etc/apt/sources.list.d/mssql-server-2019.list
RUN apt-get update && apt-get install -y msodbcsql17

# Set up the app
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt

# Set the command to run your app
CMD ["python", "app.py"]
