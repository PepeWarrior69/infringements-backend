#Deriving the latest base image
FROM python:latest

WORKDIR /infringements

COPY . /infringements

RUN apt-get update 

RUN pip install -r requirements.txt

# CMD [ "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
CMD [ "fastapi", "run", "main.py", "--port", "8000" ]
