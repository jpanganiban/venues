FROM infoshift/python

RUN apt-get update && \
  apt-get install -y git-core

WORKDIR /opt/app

# Install dependencies
ADD requirements.txt /opt/app/requirements.txt
RUN pip install -r /opt/app/requirements.txt

VOLUME ["/opt/app"]
