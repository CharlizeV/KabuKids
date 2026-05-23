"""
MainSession package initialization.
Configure noisy third-party loggers (pymongo, urllib3) to reduce console spam.
"""
import logging

# Suppress overly-verbose debug logs coming from pymongo/urllib3 (heartbeats, traces)
# Keep these at WARNING so real issues still surface.
logging.getLogger("pymongo").setLevel(logging.WARNING)
logging.getLogger("pymongo.cluster").setLevel(logging.WARNING)
logging.getLogger("pymongo.server_selection").setLevel(logging.WARNING)
logging.getLogger("pymongo.pool").setLevel(logging.WARNING)
logging.getLogger("pymongo.monitoring").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)




