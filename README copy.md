# Thymio Swarm Platform

This repository allows you to run a swarm of thymios with raspberry pis attached to them.

## Features
 - execute swarm experiments on 1 to n Raspberry Pi + Thymio II Wireless sets
 - collect logs from every agent and collate them into a single csv file
 - use most of the thymios features with an abstraction so you don't have to worry about aseba or the tdmclient: motion, leds, sensors, communication
 - optional: optitrack tracking

## Architecture
The architecture of this platform assumes the following: 
- a computer that manages the experiments, i.e. sets up the config, sends commands to start, pause, stop etc. We call this the controller. The code for this is in swarm_platform/controller
- a Raspberry Pi that collects the IP addresses of the pis on the thymios and makes them available to the controller. We call this the coordinator and it should always remain on so that the IP address remains constant. The code for this is in swarm_platform/coordinator
- 1 to n Raspberry Pis mounted on a Thymio II Wireless each, connected with a cable.

All of the components need to be on the same network. When the pis are turned on, they advertise themselves to the coordinator, which registers them and keeps updating its register based on a heartbeat. When you send a command to your swarm, the controller retrieves a list of active robots from the coordinator. This contains their hostnames, IP addresses and ports. Thereby, the controller knows where to send messages.

Project code is contained in a separate repository and only the run configuration should be placed in this repository. The project code is cloned both to the directory of where this repository is cloned to and to the pis. Different experiments can be contained in the same project repository and run by specifying the experiment name (see Examples below). 

The communication with the thymios is handled by the systemd service on the pi via tdmclient. Whenever the pi is powered on or the code is updated on the pi, the service is restarted to have the newest version running.


## Requirements

## Getting started

### Using the optitrack functionality

## Examples

## Utils
### Logging
### 

## How to cite

