#!/bin/bash
echo "Git pull"
sudo -u broderic git pull
echo "Git pull done!"
echo "Creating new docking compose"
python3 create_docker_compose.py
echo "Created docker compose"
echo "Shutting down docker containers"
sudo docker compose down
echo "Docker containers down"
echo "Building containers"
sudo docker compose build
echo "Docker containers build"
echo "Starting up docker containers"
sudo docker compose up -d
echo "Docker containers started, script is finished!"

