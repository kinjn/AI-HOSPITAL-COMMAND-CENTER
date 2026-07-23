"""Streamlit command center UI."""

from hospital_command_center.core.logging import configure_logging

# This package is imported by every page under ui/pages/ (each imports
# something from ui.components or ui.db_helper, which live under this
# package). configure_logging() was previously only called in api/app.py,
# so the Streamlit process (hcc-ui) never had any log handlers configured —
# logger.warning/error calls fell through to Python's silent "handler of
# last resort", which prints only the bare message and drops all `extra`
# context (error detail, tracebacks). Configuring it here, at package import
# time, means it's applied regardless of which Streamlit page is actually
# the entry point for a given session (Streamlit's multipage routing can
# execute a sub-page script directly without ever running app.py first).
configure_logging()
