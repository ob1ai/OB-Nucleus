"""ob-nucleus CLI: thin argparse front end over the client library.

Usage: ob-nucleus <group> <command> [options]
Groups: account, projects, leads, nucleus, mirror, sweep.
Writes require --confirm and the gated AUDITY_WRITE_TOKEN. Default is a
dry run that prints the exact request and makes no call.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from .api import Audity, DryRun
from .client import AudityError


def _emit(obj: Any) -> None:
    if isinstance(obj, DryRun):
        obj = obj.to_dict()
    print(json.dumps(obj, indent=2, default=str))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ob-nucleus",
        description="OB.1 operations layer for Audity and Nucleus. Reads are free; "
                    "writes need --confirm and explicit approval.")
    sub = p.add_subparsers(dest="group", required=True)

    # account
    acct = sub.add_parser("account", help="identity, tier, credits").add_subparsers(
        dest="command", required=True)
    acct.add_parser("whoami")
    acct.add_parser("tier")
    acct.add_parser("credits")
    acct.add_parser("preflight")

    # projects
    proj = sub.add_parser("projects", help="projects and audits").add_subparsers(
        dest="command", required=True)
    proj.add_parser("list")
    for name in ("get", "opportunities", "deliverables", "analysis"):
        sp = proj.add_parser(name)
        sp.add_argument("project_id")
    sp = proj.add_parser("job")
    sp.add_argument("job_id")
    sp = proj.add_parser("patch", help="update project fields; 0 credits; requires --confirm")
    sp.add_argument("project_id")
    sp.add_argument("--name")
    sp.add_argument("--description")
    sp.add_argument("--confirm", action="store_true")
    sp = proj.add_parser("create", help="COSTS 1000 CREDITS; requires --confirm")
    sp.add_argument("--name", required=True)
    sp.add_argument("--description")
    sp.add_argument("--confirm", action="store_true")
    sp = proj.add_parser("trigger-analysis", help="costs credits; requires --confirm")
    sp.add_argument("project_id")
    sp.add_argument("--confirm", action="store_true")

    # leads
    leads = sub.add_parser("leads", help="lead generation").add_subparsers(
        dest="command", required=True)
    sp = leads.add_parser("list")
    sp.add_argument("--status")
    sp.add_argument("--sort-by", dest="sortBy")
    sp.add_argument("--limit", type=int)
    sp = leads.add_parser("get")
    sp.add_argument("lead_id")
    sp = leads.add_parser("convert", help="COSTS 1000 CREDITS; requires --confirm")
    sp.add_argument("lead_id")
    sp.add_argument("--confirm", action="store_true")

    # nucleus
    nuc = sub.add_parser("nucleus", help="memories, captures, contacts, insights").add_subparsers(
        dest="command", required=True)
    sp = nuc.add_parser("memories")
    sp.add_argument("--type", choices=["client", "pattern", "preference"])
    sp.add_argument("--project-id")
    sp = nuc.add_parser("captures")
    sp.add_argument("--channel")
    sp.add_argument("--status")
    sp.add_argument("--project-id")
    sp = nuc.add_parser("capture")
    sp.add_argument("capture_id")
    sp = nuc.add_parser("contacts")
    sp.add_argument("--search")
    sp = nuc.add_parser("insights")
    sp.add_argument("--type")
    sp.add_argument("--unread-only", action="store_true")
    sp.add_argument("--limit", type=int, default=25)
    sp = nuc.add_parser("suggestions")
    sp.add_argument("--project-id")
    sp = nuc.add_parser("memory-create", help="live Nucleus write; requires --confirm")
    sp.add_argument("--subject", required=True)
    sp.add_argument("--content", required=True)
    sp.add_argument("--type", default="client", choices=["client", "pattern", "preference"])
    sp.add_argument("--project-id")
    sp.add_argument("--confirm", action="store_true")
    sp = nuc.add_parser("capture-note", help="live Nucleus write; requires --confirm")
    sp.add_argument("--content", required=True)
    sp.add_argument("--project-id")
    sp.add_argument("--confirm", action="store_true")
    sp = nuc.add_parser("promote", help="capture to explicit memories; requires --confirm")
    sp.add_argument("capture_id")
    sp.add_argument("--client-name")
    sp.add_argument("--confirm", action="store_true")

    # mirror
    mir = sub.add_parser("mirror", help="local SQLite + Supabase BlueprintOS mirror").add_subparsers(
        dest="command", required=True)
    mir.add_parser("sync")
    mir.add_parser("status")
    mir.add_parser("drift", help="live API vs SQLite vs Supabase integrity check")

    # sweep
    sw = sub.add_parser("sweep", help="daily read-only digest").add_subparsers(
        dest="command", required=True)
    sw.add_parser("run")

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return _dispatch(args)
    except AudityError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


def _dispatch(args: argparse.Namespace) -> int:
    g, cmd = args.group, args.command

    if g == "mirror":
        from . import mirror
        if cmd == "sync":
            _emit(mirror.sync(verbose=False))
        elif cmd == "drift":
            _emit(mirror.drift_check())
        else:
            _emit(mirror.status())
        return 0
    if g == "sweep":
        from .sweep import run_sweep
        print(run_sweep())
        return 0

    with Audity() as a:
        if g == "account":
            _emit(getattr(a.account, cmd)())
        elif g == "projects":
            if cmd == "list":
                _emit(a.projects.list())
            elif cmd == "get":
                _emit(a.projects.get(args.project_id))
            elif cmd == "opportunities":
                _emit(a.projects.opportunities(args.project_id))
            elif cmd == "deliverables":
                _emit(a.projects.deliverables(args.project_id))
            elif cmd == "analysis":
                _emit(a.projects.analysis(args.project_id))
            elif cmd == "job":
                _emit(a.projects.job_status(args.job_id))
            elif cmd == "patch":
                fields = {k: v for k, v in
                          (("name", args.name), ("description", args.description)) if v}
                _emit(a.projects.patch(args.project_id, fields, confirm=args.confirm))
            elif cmd == "create":
                _emit(a.projects.create(args.name, args.description, confirm=args.confirm))
            elif cmd == "trigger-analysis":
                _emit(a.projects.trigger_analysis(args.project_id, confirm=args.confirm))
        elif g == "leads":
            if cmd == "list":
                params = {k: v for k, v in
                          (("status", args.status), ("sortBy", args.sortBy),
                           ("limit", args.limit)) if v}
                _emit(a.leads.list(**params))
            elif cmd == "get":
                _emit(a.leads.get(args.lead_id))
            elif cmd == "convert":
                _emit(a.leads.convert(args.lead_id, confirm=args.confirm))
        elif g == "nucleus":
            if cmd == "memories":
                _emit(a.nucleus.memories(args.type, args.project_id))
            elif cmd == "captures":
                _emit(a.nucleus.captures(args.channel, args.status, args.project_id))
            elif cmd == "capture":
                _emit(a.nucleus.capture(args.capture_id))
            elif cmd == "contacts":
                _emit(a.nucleus.contacts(args.search))
            elif cmd == "insights":
                _emit(a.nucleus.insights(args.type, args.unread_only, args.limit))
            elif cmd == "suggestions":
                _emit(a.nucleus.suggestions(args.project_id))
            elif cmd == "memory-create":
                _emit(a.nucleus.create_memory(args.subject, args.content, args.type,
                                              args.project_id, confirm=args.confirm))
            elif cmd == "capture-note":
                _emit(a.nucleus.create_capture_note(args.content, args.project_id,
                                                    confirm=args.confirm))
            elif cmd == "promote":
                from .promote import promote_capture
                _emit(promote_capture(args.capture_id, args.client_name,
                                      confirm=args.confirm))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
