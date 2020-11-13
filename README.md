# HDD-Testing

Here lies the code for automagically testing HDDs as they are inserted into the HDD testing machine. 
Uses python and python libraries to perform actions and compose test results.

## Building docker

The `build.sh` file builds both the *daemon* and the *client* docker images. Note that this script must be ran from the project's root folder.

## Docker usage

### hddmond

The container needs to be ran with privledge, and a mount to the config directory.

The config directory exists inside the container at `/etc/hddmon/config`. This directory should be mounted to, with a config file existing in your system directory. See `src/config/config.json.example` for an example configuration file.

### hddmon-client

The container needs parameters specified at the end of the command. 

```
docker run -it --rm  --name HddmondClientTest --privileged=true hddmon-client:latest -d /dev/sdc -a 192.168.1.2 -p 56567
```

 - `-d --device` is the device to connect with.
 - `-a --address` is the address to connect to (where hddmond is hosted).
 - `-p --port` is the port that the hddmond daemon is accepting remote HDD clients on.

## Bare metal usage

The project can be run on bare metal, but good luck. The file `src/install.sh` is tailored to an Ubuntu (Debain) system and is crappy. However, this will attempt to install the project to `/etc/hddmon` and create a service entry for `systemd`. It might be worth noting that in both the docker container and the bare metal install, only the `src` directory and its contents are copied/used for the project to run.