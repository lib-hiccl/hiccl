"""Hiccl CLI — command-line interface for development and execution."""

from __future__ import annotations

import argparse
import os
import sys
import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Hiccl CLI — Clojure-inspired reactive web framework for Python."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # 'dev' command
    dev_parser = subparsers.add_parser(
        "dev", help="Start the Hiccl application in development mode."
    )
    dev_parser.add_argument(
        "app", help="App import string, e.g. 'examples.combined_app:app'"
    )
    dev_parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Bind socket to this host (default: 127.0.0.1)",
    )
    dev_parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Bind socket to this port (default: 8000)",
    )
    dev_parser.add_argument(
        "--live-reload",
        action="store_true",
        help="Enable state-preserving Hot Module Replacement (HMR)",
    )
    dev_parser.add_argument(
        "--hrepl", action="store_true", help="Enable hREPL network server"
    )
    dev_parser.add_argument(
        "--hrepl-port",
        type=int,
        default=8998,
        help="hREPL TCP port (default: 8998)",
    )
    dev_parser.add_argument(
        "--hrepl-host",
        default="127.0.0.1",
        help="hREPL TCP host (default: 127.0.0.1)",
    )

    # 'run' command
    run_parser = subparsers.add_parser(
        "run", help="Start the Hiccl application in production mode."
    )
    run_parser.add_argument(
        "app", help="App import string, e.g. 'examples.combined_app:app'"
    )
    run_parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Bind socket to this host (default: 127.0.0.1)",
    )
    run_parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Bind socket to this port (default: 8000)",
    )

    args = parser.parse_args()

    # Split import string
    if ":" not in args.app:
        print(
            f"Error: Application path must be in format 'module:app', got '{args.app}'",
            file=sys.stderr,
        )
        sys.exit(1)

    if args.command == "dev":
        # Add current working directory to sys.path
        sys.path.insert(0, os.getcwd())

        # Set environment variables so the imported app configuration gets the settings!
        if args.live_reload:
            os.environ["HICCL_LIVE_RELOAD"] = "1"
        if args.hrepl:
            os.environ["HREPL_ENABLED"] = "1"
            os.environ["HREPL_PORT"] = str(args.hrepl_port)
            os.environ["HREPL_HOST"] = args.hrepl_host

        print(f"Starting Hiccl dev server for '{args.app}'...")
        # Run uvicorn without reloading to allow HMR in-process reload
        uvicorn.run(
            args.app,
            host=args.host,
            port=args.port,
            reload=False,  # Essential: uvicorn reload=False is required for HMR!
            log_level="info",
        )
    elif args.command == "run":
        # Production mode
        sys.path.insert(0, os.getcwd())
        print(f"Starting Hiccl production server for '{args.app}'...")
        uvicorn.run(
            args.app,
            host=args.host,
            port=args.port,
            reload=False,
            log_level="warning",
        )


if __name__ == "__main__":
    main()
