FROM python:3.7

# install requirements
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# prepare script
COPY . .
