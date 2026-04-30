#!/usr/bin/env bash

docker compose build
docker compose up -d

S=sim_session
tmux kill-session -t $S 2>/dev/null
tmux new -d -s $S \; \
  split-window -h \; \
  split-window -h \; \
  select-layout tiled \; \
  send-keys -t 0 "docker attach ee419p2sim-1" C-m \; \
  send-keys -t 1 "docker attach ee419p2sim-2" C-m \; \
  send-keys -t 2 "docker attach ee419p2sim-3" C-m \; \
  attach

docker compose down
