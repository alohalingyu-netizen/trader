"""Evolving Trader — A-share market data service."""

import argparse
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="evolving-trader",
        description="A-share market data sync and query service",
    )
    parser.add_argument(
        "--config",
        default="config/settings.yaml",
        help="Path to settings YAML file (default: config/settings.yaml)",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # server: start FastAPI server
    srv_parser = subparsers.add_parser("server", help="Start FastAPI server")
    srv_parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to listen on (default: 8000)",
    )

    # sync: sync Tushare historical data to MySQL
    sync_parser = subparsers.add_parser("sync", help="Sync Tushare data to MySQL")
    sync_parser.add_argument(
        "--table",
        dest="table",
        action="append",
        metavar="TABLE",
        help="Table(s) to sync (can be repeated). Omit to sync all 11 tables.",
    )
    sync_parser.add_argument(
        "--start-date",
        default=None,
        metavar="YYYYMMDD",
        help="Sync start date (default: 20240101)",
    )
    sync_parser.add_argument(
        "--end-date",
        default=None,
        metavar="YYYYMMDD",
        help="Sync end date (default: today)",
    )
    sync_parser.add_argument(
        "--force",
        action="store_true",
        help="Ignore sync_log and re-run all batches in the date range",
    )

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Error: config file not found: {config_path}", file=sys.stderr)
        sys.exit(1)

    from src.config import Config  # noqa: PLC0415

    config = Config.load(str(config_path))

    if args.command == "sync":
        import logging
        from datetime import date as _date

        import tushare as ts

        from src.data.mysql_client import MySQLClient
        from src.data.rate_limiter import RateLimiter
        from src.data.sync import SYNCER_MAP

        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

        start_date = args.start_date or "20240101"
        end_date = args.end_date or _date.today().strftime("%Y%m%d")

        # Validate --table values
        selected_tables = args.table or list(SYNCER_MAP.keys())
        unknown = [t for t in selected_tables if t not in SYNCER_MAP]
        if unknown:
            print(f"Error: unknown table(s): {', '.join(unknown)}", file=sys.stderr)
            print(f"Available tables: {', '.join(SYNCER_MAP.keys())}", file=sys.stderr)
            sys.exit(1)

        # Init MySQL
        try:
            db = MySQLClient(config.mysql)
            db.init_schema()
        except Exception as exc:
            print(f"Error: MySQL connection failed: {exc}", file=sys.stderr)
            sys.exit(1)

        pro = ts.pro_api(config.tushare.token)
        rate_limiter = RateLimiter(max_calls=config.tushare.rate_limit_per_min)

        for table_name in selected_tables:
            syncer = SYNCER_MAP[table_name](pro, db, rate_limiter)
            print(f"[sync] {table_name}  {start_date} ~ {end_date} (force={args.force})")
            try:
                syncer.sync(start_date, end_date, force=args.force)
                print(f"[sync] {table_name} done.")
            except Exception as exc:
                print(f"[sync] {table_name} failed: {exc}", file=sys.stderr)
                sys.exit(1)

        sys.exit(0)

    elif args.command == "server":
        import logging
        import uvicorn
        from src.data.mysql_client import MySQLClient

        logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

        # Ensure schema is up to date before starting
        try:
            db = MySQLClient(config.mysql)
            db.init_schema()
        except Exception as exc:
            print(f"Error: MySQL connection failed: {exc}", file=sys.stderr)
            sys.exit(1)

        from src.server.app import app

        print(f"Starting server on port {args.port} …")
        uvicorn.run(app, host="0.0.0.0", port=args.port, log_level="info")


if __name__ == "__main__":
    main()
