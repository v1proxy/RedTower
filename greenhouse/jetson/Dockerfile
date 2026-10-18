# One image for the core services and the pure-Python modules.
# Drivers that need CUDA or ROS 2 get their own image later and use the same gh package.
FROM python:3.12-slim
RUN pip install --no-cache-dir paho-mqtt==2.1.0 PyYAML==6.0.2 docker==7.1.0 pyserial==3.5 pymycobot==4.0.7
WORKDIR /app
COPY gh /app/gh
COPY modules /app/modules
COPY config /app/config
ENV PYTHONPATH=/app PYTHONUNBUFFERED=1 GH_MODULES_DIR=/app/modules GH_CONFIG_DIR=/app/config GH_DATA_DIR=/data
