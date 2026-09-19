"""Orchestrator. Should read like the README: extract -> transform -> load.

Write:
    main() -> int   # 0 on success, 1 on failure (Cloud Run reads the exit code)
        - configure logging, log a run summary (fetched/loaded/skipped/duration)
        - catch at the top level, log with traceback, return 1
"""
