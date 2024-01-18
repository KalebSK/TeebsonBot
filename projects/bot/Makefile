TMP_DIR := $(shell mktemp -d)
include .env
export
ENV_FILE := --env-file .env
IMAGE_NAME := teebson-bot
API_PREFIX_DEV := http://localhost:5000/
API_PREFIX_PROD := http://localhost:8080/
NETWORK_NAME := teebson-network
default: build
.PHONY: run, build, clean, run-prod, all
all: build run
all-prod: build run-prod

build:
	chmod 755 -R ./
	cp -r src $(TMP_DIR)/src
	cp Dockerfile .dockerignore $(TMP_DIR)
	cp pyproject.toml poetry.lock $(TMP_DIR)

	cp -r ../../shared/googleauth/ $(TMP_DIR)/googleauth/
	cd $(TMP_DIR)
	cp -r $(TMP_DIR) ./to-docker/
	-docker build -t $(IMAGE_NAME) ./to-docker/
	rm -rf ./to-docker/
	rm -rf $(TMP_DIR)

run:
	docker run -it --rm --name dev-teebson-bot --network $(NETWORK_NAME) $(ENV_FILE) --env API_PREFIX=$(API_PREFIX_DEV) \
	 --mount type=volume,source=discord-bot-database,target=/bot/ $(IMAGE_NAME)

run-prod:
	docker run -it --rm --name prod-teebson-bot --network $(NETWORK_NAME) $(ENV_FILE) --env API_PREFIX=$(API_PREFIX_PROD) \
	 --mount type=volume,source=discord-bot-database-prod,target=/bot/database $(IMAGE_NAME) -d

clean:
	docker rmi $(IMAGE_NAME)
