FROM python:3.9-slim

WORKDIR /opt/app/

# Copy files
COPY logger.py /opt/app
COPY requirements.txt /opt/app
COPY app.py /opt/app

# Install project python dependencies
RUN pip install -r requirements.txt

# Run app.py
CMD python app.py -b $MQTT_BROKER