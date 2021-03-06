# HDD-Testing

Here lies the code for automagically testing HDDs as they are inserted into the HDD testing machine. 
Uses python and python libraries to perform actions and compose test results.

## Building docker

The `build.sh` file builds both the *daemon* and the *client* docker images. Note that this script must be ran from the project's root folder.

## Docker usage

### hddmond

The container needs to be ran with priviledge, and a mount to the config directory. If mounts don't suit you, there is also support for environment variables, and command-line arguments which take the most precidence. However, the `blacklist.json` that is generated when HDDs are blacklisted is stored in the `/etc/hddmon/config` folder, and this is something you may want to persist.

Order of configuration load:
1. Config file              *(First to be loaded)*
2. ENV variables            *(Overwrites config file, where specified)*
3. Command-line arguments   *(Overwrites the other two, where specified)*

#### Config file

The config directory exists inside the container at `/etc/hddmon/config`. This directory should be mounted to, with a config file existing in your system directory. See `src/config/config.json.example` for an example configuration file. Additionally, VSCode and some other editors should make use of the `$schema` key to help you auto-complete the config file.

#### ENV variables

- `DB_ADDRESS`
- `DB_PORT`
- `DB_USER`
- `DB_PASS`
- `WEBSOCKET_PORT`
- `HDDMON_PORT`

#### Command-line arguments

```
-h --help          # Prints help
-v --verbose       # Verbose option output (for now)
-w --wsport=       # The port that the websocket should use
-r --rhdport=      # The remote client port that the daemon should use to host
-A --dbaddress=    # The address of the optional DB
-p --dbport=       # The port of the optional DB
-U --dbuser=       # The user of the optional DB
-P --dbpassword=   # The password of the optional DB
```

### hddmon-client

The container needs parameters specified at the end of the command. 

```
docker run -it --rm --name HddmondClientTest --privileged=true hddmon-client:latest -d /dev/sdc -a 192.168.1.2 -p 56567
```

 - `-d --device` is the device to connect with.
 - `-a --address` is the address to connect to (where hddmond is hosted).
 - `-p --port` is the port that the hddmond daemon is accepting remote HDD clients on.

## Bare metal usage

The project can be run on bare metal, but good luck. The file `src/install.sh` is tailored to an Ubuntu (Debain) system and is crappy. However, this will attempt to install the project to `/etc/hddmon` and create a service entry for `systemd`. It might be worth noting that in both the docker container and the bare metal install, only the `src` directory and its contents are copied/used for the project to run.