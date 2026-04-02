"""Evolving Trader — A self-evolving multi-agent trading system for A-share markets."""

import argparse
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="evolving-trader",
        description="A self-evolving multi-agent trading system for A-share markets",
    )
    parser.add_argument(
        "--config",
        default="config/settings.yaml",
        help="Path to settings YAML file (default: config/settings.yaml)",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # run: execute one trading cycle
    run_parser = subparsers.add_parser("run", help="Execute a trading cycle")
    run_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate without placing real orders",
    )

    # backtest: run historical backtest
    bt_parser = subparsers.add_parser("backtest", help="Run a historical backtest")
    bt_parser.add_argument("--start", required=True, help="Start date YYYYMMDD")
    bt_parser.add_argument("--end", required=True, help="End date YYYYMMDD")

    # server: start FastAPI + scheduler + PriceMonitor
    srv_parser = subparsers.add_parser("server", help="Start FastAPI server")
    srv_parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to listen on (default: 8000)",
    )

    # digest: ingest external knowledge
    digest_parser = subparsers.add_parser("digest", help="Run the knowledge digester")
    digest_parser.add_argument(
        "--file",
        dest="file_path",
        help="Path to a file (PDF, TXT, MD, or image)",
    )
    digest_parser.add_argument(
        "--url",
        help="URL to fetch and parse",
    )

    # review: run daily review for a specific date
    review_parser = subparsers.add_parser("review", help="Run daily review for a specific date")
    review_parser.add_argument(
        "--date",
        default=None,
        help="Date to review in YYYYMMDD format (default: yesterday)",
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

    # evolve: run the evolution engine
    evolve_parser = subparsers.add_parser("evolve", help="Run the evolution engine")
    evolve_parser.add_argument(
        "--period",
        choices=["weekly", "monthly"],
        default="weekly",
        help="Evolution period (default: weekly)",
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

    if args.command == "run":
        print(f"Starting trading cycle (dry_run={args.dry_run}) …")
        # TODO: invoke LangGraph orchestration chain
    elif args.command == "backtest":
        print(f"Backtesting from {args.start} to {args.end} …")
        # TODO: invoke backtest engine
    elif args.command == "digest":
        from src.digester.parser import ContentParser
        from src.digester.agent import DigestAgent
        from src.digester.confirm import collect_approvals
        from src.memory.strategy_store import StrategyStore
        from src.memory.knowledge_memory import KnowledgeMemory
        from src.memory.retriever import KnowledgeRetriever
        from src.digester.models import KnowledgeType

        if not args.file_path and not args.url:
            print("Error: must provide --file or --url", file=sys.stderr)
            sys.exit(1)

        print("Running knowledge digester …")
        llm_cfg = LLMConfig(
            model=config.llm.model,
            temperature=config.llm.temperature,
            max_tokens=config.llm.max_tokens,
            api_key=config.llm.api_key,
        )

        parser = ContentParser()
        agent = DigestAgent(config=llm_cfg)
        strategy_store = StrategyStore()
        knowledge_memory = KnowledgeMemory()

        # Parse content
        if args.file_path:
            parsed = parser.parse(args.file_path)
        else:
            assert args.url
            parsed = parser.parse_url(args.url)

        print(f"已解析: {parsed.source_ref}")

        # Extract knowledge
        items = agent.digest(parsed)
        if not items:
            print("未提取到任何知识条目。")
            sys.exit(0)

        # Collect confirmations
        approvals = collect_approvals(items)

        # Persist approved items
        retriever = KnowledgeRetriever(
            strategy_store=strategy_store,
            knowledge_memory=knowledge_memory,
        )
        for item, approved in zip(items, approvals):
            if not approved:
                continue
            item.confirmed = True
            if item.knowledge_type == KnowledgeType.STRATEGY:
                import json
                from src.digester.models import StrategyRule
                strat_data = json.loads(item.content)
                strat_data["source_ref"] = item.source_ref
                rule = StrategyRule.model_validate(strat_data)
                strategy_store.save(rule)
            else:
                knowledge_memory.save(item)

        confirmed_count = sum(approvals)
        print(f"\n[ Digest ] 完成: {confirmed_count}/{len(approvals)} 条知识已采纳")

    elif args.command == "review":
        from datetime import datetime, timedelta
        from src.agents.reviewer import ReviewerAgent
        from src.memory.trade_record import TradeStore
        from src.config import LLMConfig

        review_date = args.date
        if review_date is None:
            review_date = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")

        print(f"Running daily review for {review_date} …")
        llm_cfg = LLMConfig(
            model=config.llm.model,
            temperature=config.llm.temperature,
            max_tokens=config.llm.max_tokens,
            api_key=config.llm.api_key,
        )
        tc = None
        try:
            from src.data.tushare_client import TushareClient
            tc = TushareClient(config.tushare)
        except Exception as e:
            print(f"Warning: TushareClient init failed: {e}")

        reviewer = ReviewerAgent(
            config=llm_cfg,
            tushare_client=tc,
            trade_store=TradeStore(),
        )
        report = reviewer.run(review_date)

        # Present qualitative findings and collect confirmations
        if report.pending_qualitative_items:
            approvals = reviewer.present_qualitative_findings(report.pending_qualitative_items)
            reviewer.persist_approved_findings(report.pending_qualitative_items, approvals)

        print(f"\n[Review] 完成: {report.trades_summary['total_trades']} 笔交易, 胜率 {report.trades_summary.get('win_rate', 0):.1%}")

    elif args.command == "evolve":
        from datetime import datetime
        from src.agents.evolver import EvolverAgent, EvolutionReport
        from src.agents.evolver import EvolverMemoryStore
        from src.config import LLMConfig

        print(f"Running {args.period} evolution analysis …")
        llm_cfg = LLMConfig(
            model=config.llm.model,
            temperature=config.llm.temperature,
            max_tokens=config.llm.max_tokens,
            api_key=config.llm.api_key,
        )
        evolver = EvolverAgent(
            config=llm_cfg,
            memory_store=EvolverMemoryStore(),
        )
        report = evolver.run(period=args.period)

        # Present and confirm proposals
        evolver.present_report(report)
        sorted_proposals = sorted(
            report.proposals,
            key=lambda p: (
                0 if p.confidence.value == "high" else
                1 if p.confidence.value == "medium" else 2
            ),
        )
        approvals = evolver.confirm_proposals(sorted_proposals)

        # Execute confirmed proposals
        memory_updates = evolver.record_outcomes(sorted_proposals, approvals)

        print(f"\n[Evolver] 完成: {sum(approvals)}/{len(approvals)} 建议已确认")

    elif args.command == "server":
        print(f"Starting server on port {args.port} …")
        import uvicorn
        from src.server.app import app
        from src.server.scheduler.scheduler import TradingScheduler
        from src.server.price_monitor import PriceMonitor
        from src.server.chat_store import ChatStore

        # Initialize chat store (creates data/chat.db)
        ChatStore()

        # Initialize scheduler and price monitor
        scheduler = TradingScheduler()
        tc = None
        try:
            from src.data.tushare_client import TushareClient
            tc = TushareClient(config.tushare)
            scheduler.set_tushare_client(tc)
        except Exception as e:
            print(f"Warning: TushareClient init failed: {e}")

        price_monitor = PriceMonitor(tc, config) if tc else None

        # Start scheduler and price monitor
        scheduler.start()
        if price_monitor:
            price_monitor.start()

        try:
            uvicorn.run(app, host="0.0.0.0", port=args.port, log_level="info")
        finally:
            scheduler.shutdown()
            if price_monitor:
                price_monitor.stop()


if __name__ == "__main__":
    main()
