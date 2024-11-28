FROM python:3.11-slim
RUN apt-get update && apt-get install -y curl apt-transport-https
RUN curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add -
RUN curl https://packages.microsoft.com/mssql-server/debian/mssql-server-2019.list > /etc/apt/sources.list.d/mssql-server-2019.list
RUN apt-get update && apt-get install -y msodbcsql17
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt
CMD ["python", "app.py"]
