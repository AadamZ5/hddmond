FROM python:3.8.6-alpine3.12

#Link python executable to where I've hardcoded it, for now, for convenience, until I fix my horrible ways.
RUN ln /usr/local/bin/python /usr/bin/python3.8

#Me, I am the maintainer
LABEL maintainer="azocolo@velocitymsc.com"

#Install smartmontools and pciutils
RUN apt-get update
RUN apt-get install -y smartmontools pciutils
RUN rm -rf /var/lib/apt/lists/*

#Move to our python proj dir.
WORKDIR /etc/hddmon
#Install python libraries
RUN pip install -r requirements.txt

#The run point
CMD [ "python", "./hddmond.py" ]