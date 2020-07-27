FROM python:3.7-alpine

RUN mkdir /app
WORKDIR /app
COPY . /app
RUN pip install bottle requests
EXPOSE 8080
CMD ["python", "bot.py"]