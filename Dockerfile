FROM apache/airflow:2.6.3

# Install additional Python dependencies
COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt

# Copy DAGs
COPY dags /opt/airflow/dags

WORKDIR /opt/airflow

CMD ["airflow", "webserver"]



