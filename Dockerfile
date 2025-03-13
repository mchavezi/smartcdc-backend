# Base Image
FROM public.ecr.aws/ubuntu/ubuntu:20.04

ENV FLASK_ENV=development \
    PYTHONPATH=/ \
    AWS_DEFAULT_REGION=us-east-2

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc g++ python3-dev python3-pip python3-setuptools \
    default-libmysqlclient-dev pkg-config sqlite3 awscli \
    git openssh-client curl vim nano bash-completion mysql-client && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/*

# Upgrade pip
ENV APP_HOME=/app
RUN mkdir $APP_HOME

# COPY docker-entrypoint-app.sh $APP_HOME/docker-entrypoint-app.sh

# Setup directories
COPY ./ $APP_HOME/
# COPY app.py $APP_HOME/app.py
# COPY wsgi.py $APP_HOME/wsgi.py

# COPY requirements.txt /app/requirements.txt
RUN pip install -r $APP_HOME/requirements.txt

RUN addgroup --system app && adduser --system --group app
RUN chown -R app:app $APP_HOME
WORKDIR $APP_HOME
USER app

# Expose the required port
EXPOSE 5000

# Start the application
ENTRYPOINT ["bash","docker-entrypoint-app.sh"]