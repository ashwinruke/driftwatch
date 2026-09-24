# This module documents the retry policy used across the project.
#
# Retries use exponential backoff starting at 2 seconds, doubling on
# each attempt, up to a maximum of 3 attempts total. This applies to
# all outbound calls to GitHub and the LLM provider.
#
# See driftwatch/retry.py for the implementation.
