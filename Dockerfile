FROM apache/airflow:2.6.3

WORKDIR /opt/airflow

# Copy requirements.txt into the container
COPY requirements.txt /opt/airflow/requirements.txt

# Install the Python dependencies
RUN pip install --no-cache-dir -r /opt/airflow/requirements.txt

# Copy other necessary files
COPY dags /opt/airflow/dags
COPY scripts /opt/airflow/scripts
COPY datasets /opt/airflow/datasets