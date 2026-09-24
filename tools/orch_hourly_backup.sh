#!/usr/bin/env bash
# orch_hourly_backup.sh — INDEPENDENT hourly backstop for the orchestrator loop.
# Purpose: guarantee the orchestrator wakes at least once/hour to re-assess team
# liveness + re-arm the primary watcher, EVEN IF the primary ~20min channel-watcher
# process dies (crash/kill/silent re-arm failure). Run in the BACKGROUND; on exit
# the harness re-invokes the session. Re-launch each fire to re-arm.
# This is a redundant safety net, NOT the primary event path (that's peer_watch.sh /
# the channel-watcher). Layers: [1] channel-watcher (~20min, event+timeout) +
# [2] this hourly backup + [3] headless PALocalOrchTick heartbeat.
sleep 3600
echo "HOURLY-BACKUP-FIRE — re-assess peers (list_sessions), intake channels, re-arm primary watcher + re-arm this backup"
exit 0
