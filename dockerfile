FROM python:3.8.6

#Link python executable to where I've hardcoded it, for now, for convenience, until I fix my horrible ways.
#This is purely for the shebang at the beginning of the "runnable" python files, so this is probably unnecessary here.
RUN ln /usr/local/bin/python /usr/bin/python3.8

#Me, I am the maintainer
LABEL maintainer="azocolo@velocitymsc.com"

#Install smartmontools and pciutils.
RUN apt-get update
RUN apt-get install -y smartmontools pciutils scrub
RUN rm -rf /var/lib/apt/lists/*

#Copy the files for our project.
RUN mkdir /etc/hddmon
COPY ./src/ /etc/hddmon/

#Move to our python proj dir.
WORKDIR /etc/hddmon
#Install python libraries.
RUN pip install -r requirements.txt

#The run point.
ENTRYPOINT [ "python", "hddmond.py" ]