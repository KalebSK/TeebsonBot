TMP_DIR := $(shell mktemp -d)
IMAGE_NAME_DEV := teebson-api-dev
IMAGE_NAME_PROD := teebson-api-prod
NGINX_IMAGE_NAME := teebson-nginx
CREDENTIALS_FILE := ${PWD}/creds.json
CONFIG_FILE := ${PWD}/src/config.py
NETWORK_NAME := teebson-network

default: all-dev
.PHONY: run, all-dev, build, clean-dev, clean-all, all-prod, rm-prod, rm-dev
all-dev: build test run
all-prod: build-prod test run-prod
clean-all: clean-dev clean-prod

build:
	chmod 755 -R ./
	cp -r src $(TMP_DIR)
	rm -rf $(TMP_DIR)/src/config.py
	cp entrypoint.sh $(TMP_DIR)
	mkdir -p $(TMP_DIR)/instance
	cp Dockerfile .dockerignore $(TMP_DIR)
	cp pyproject.toml poetry.lock $(TMP_DIR)

	cp -r ../../shared/db/ $(TMP_DIR)/db/
	cd $(TMP_DIR)
	cp -r $(TMP_DIR) ./to-docker/
	-docker build -t $(IMAGE_NAME_DEV) ./to-docker/
	rm -rf ./to-docker/
	rm -rf $(TMP_DIR)

build-prod:
	chmod 755 -R ./
	cp -r src $(TMP_DIR)
	rm -rf $(TMP_DIR)/src/config.py
	cp nginx.conf $(TMP_DIR)
	cp entrypoint.sh $(TMP_DIR)
	cp -r nginx $(TMP_DIR)
	mkdir -p $(TMP_DIR)/instance
	cp prod.Dockerfile .dockerignore $(TMP_DIR)
	cp pyproject.toml poetry.lock $(TMP_DIR)
	cp -r ../../shared/db/ $(TMP_DIR)/db/

	cd $(TMP_DIR)
	cp -r $(TMP_DIR) ./to-docker/
	-docker build -f prod.Dockerfile -t $(IMAGE_NAME_PROD) ./to-docker/
	cd $(TMP_DIR)/nginx
	-docker build -f nginx/nginx.Dockerfile -t $(NGINX_IMAGE_NAME) ./to-docker/nginx
	rm -rf ./to-docker/
	rm -rf $(TMP_DIR)

test:
	python -m pytest
run:
	docker run -it --rm -p 5001:5000 --name $(IMAGE_NAME_DEV) -v $(CREDENTIALS_FILE):/api/creds.json:ro -v $(CONFIG_FILE):/api/src/config.py:ro \
	 --mount type=volume,source=discord-bot-database,target=/api/instance $(IMAGE_NAME_DEV)

run-prod:
	docker run -d -it --rm -p 8000:8000 --name $(IMAGE_NAME_PROD) --network $(NETWORK_NAME) \
	 --mount type=volume,source=discord-bot-database-prod,destination=//api/instance -v $(CONFIG_FILE):/api/src/config.py:ro \
	 -v $(CREDENTIALS_FILE):/api/creds.json:ro $(IMAGE_NAME_PROD) && sleep 10 \
	 && docker run --name teebson-api-nginx-proxy --network $(NETWORK_NAME) -d -p 8080:80 $(NGINX_IMAGE_NAME)


rm-prod:
	docker rm -f $(IMAGE_NAME_PROD)
	docker rm -f teebson-api-nginx-proxy

rm-dev:
	docker rm -f $(IMAGE_NAME_DEV)

clean-dev: rm-dev
	docker rmi $(IMAGE_NAME_DEV)

clean-prod: rm-prod
	docker rmi $(IMAGE_NAME_PROD)
	docker rmi $(NGINX_IMAGE_NAME)
