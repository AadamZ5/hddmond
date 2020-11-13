# HDD-Testing

Here lies the code for automagically testing HDDs as they are inserted into the HDD testing machine. 
Uses python and python libraries to perform actions and compose test results.

## Docker usage

The container needs to be ran with privledge, and a mount to the config directory.

The config directory exists inside the container at `/etc/hddmon/config`. This directory should be mounted to, with a config file existing in your system directory. See `src/config/config.json.example` for an example configuration file.

## Bare metal usage

The project can be run on bare metal, but good luck. The file `src/install.sh` is tailored to an Ubuntu (Debain) system and is crappy. However, this will attempt to install the project to `/etc/hddmon` and create a service entry for `systemd`. It might be worth noting that in both the docker container and the bare metal install, only the `src` directory and its contents are copied/used for the project to run.