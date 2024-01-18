# OVERVIEW
This is the 2nd layer of the reverse proxy setup for the API. It forwards requests to the first nginx proxy layer that is ran at api startup. 
This layer must be ran after the api startup script.

## CONFIGURATION
This container and the api container must be on the same docker network. The makefile handles running each container and configures the docker network. Inside the 'nginx.conf' file, this server references the api container by name and port and any requests made to this server will send them to the first proxy in the api container.
