FROM python:3.8-slim

WORKDIR /app

COPY . /app
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install gitpython
RUN mkdir repo
RUN apt-get update && apt-get install -y git

ENV GIT_PYTHON_GIT_EXECUTABLE /usr/bin/git

CMD ["python", "./pullrequest-hook.py"]
