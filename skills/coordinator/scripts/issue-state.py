#!/usr/bin/env python3
"""Persist and gate one autonomous issue's execution state.

State lives in `.smart-delegate/issues/<id>.json` (or `--state-dir`). The coordinator uses this
script for mechanical state changes; judgement stays with delegated roles. `gate` is the mechanical
completion check: it refuses success when criteria are unmet, evidence is stale, the reviewer is the
implementer, blocking findings remain, required CI is not green, or a criterion was edited without
a recorded amendment.

Run `issue-state.py <command> --help` for options. Exit codes:
  0  success / gate satisfied
  1  not complete (reasons printed)
  2  usage, unreadable state, or refused mutation
  3  issue blocked by a recorded blocker
  4  execution budget exhausted

Standard library only. One writer per issue.
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import sys
import tempfile

SCHEMA = 2
PHASES = (
    "intake", "discovery", "criteria", "implement", "review", "verify",
    "pr", "ci", "done", "blocked",
)
PROFILES = ("lightweight", "standard", "enhanced")
VERDICTS = ("PASS", "FAIL", "NOT VERIFIED", "PENDING")
CI_STATES = ("green", "failing", "pending", "unknown")
PR_STATES = ("draft", "open", "ready", "merged", "closed")
BLOCKER_KINDS = (
    "credentials", "ambiguity", "authorization", "external", "budget", "no-progress",
)


def fail(message, code=2):
    print(f"issue-state: {message}", file=sys.stderr)
    return code


def now():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()


def state_path(args):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", args.issue or ""):
        raise SystemExit(fail("issue id must match [A-Za-z0-9][A-Za-z0-9._-]*"))
    state_dir = args.state_dir or os.path.join(os.getcwd(), ".smart-delegate", "issues")
    return os.path.join(state_dir, f"{args.issue}.json")


def normalize_name(value):
    """Comparison key for actor identity: collapse whitespace and casefold."""
    if not isinstance(value, str):
        return ""
    return " ".join(value.split()).casefold()


def display_name(value):
    return " ".join(value.split())


def read(args):
    path = state_path(args)
    try:
        with open(path, encoding="utf-8") as handle:
            state = json.load(handle)
    except FileNotFoundError:
        raise SystemExit(fail(f"no state at {path}; run init first"))
    except (OSError, ValueError) as error:
        raise SystemExit(fail(f"unreadable state at {path}: {error}"))
    if not isinstance(state, dict):
        raise SystemExit(fail(f"invalid state at {path}: top level is not a mapping"))
    if state.get("schema") != SCHEMA:
        if state.get("schema") == 1:
            raise SystemExit(fail(
                f"state at {path} uses schema 1; re-init the issue or migrate content_sha fields"))
        raise SystemExit(fail(f"unsupported state schema at {path}: {state.get('schema')!r}"))
    required = ("id", "objective", "phase", "criteria", "review", "ci", "pr", "budget")
    missing = [key for key in required if key not in state]
    if missing:
        raise SystemExit(fail(f"incomplete state at {path}: missing {', '.join(missing)}"))
    for key in ("review", "ci", "pr", "budget"):
        if not isinstance(state[key], dict):
            raise SystemExit(fail(f"invalid state at {path}: {key} is not a mapping"))
    if not isinstance(state["criteria"], list):
        raise SystemExit(fail(f"invalid state at {path}: criteria is not a list"))
    for index, item in enumerate(state["criteria"]):
        if not isinstance(item, dict) or not isinstance(item.get("id"), str) \
                or not isinstance(item.get("text"), str) or not isinstance(item.get("verdict"), str) \
                or not isinstance(item.get("check", ""), str):
            raise SystemExit(fail(f"invalid state at {path}: criteria[{index}] is malformed"))
        for key in ("evidence", "revision", "verified_by", "content_sha"):
            if key in item and not isinstance(item[key], str):
                raise SystemExit(fail(f"invalid state at {path}: criteria[{index}].{key} is not a string"))
        if "amendments" in item and not isinstance(item["amendments"], list):
            raise SystemExit(fail(f"invalid state at {path}: criteria[{index}].amendments is not a list"))
        for amendment in item.get("amendments", []):
            if not isinstance(amendment, dict):
                raise SystemExit(fail(f"invalid state at {path}: amendment is not a mapping"))
            if not isinstance(amendment.get("justification", ""), str):
                raise SystemExit(fail(f"invalid state at {path}: amendment justification is not a string"))
            approved = amendment.get("approved_by", [])
            if not isinstance(approved, (list, str)) or (
                    isinstance(approved, list) and not all(isinstance(name, str) for name in approved)):
                raise SystemExit(fail(f"invalid state at {path}: amendment approved_by is malformed"))
    for key in ("blocking", "nonblocking", "questions"):
        if key in state["review"] and not isinstance(state["review"][key], list):
            raise SystemExit(fail(f"invalid state at {path}: review.{key} is not a list"))
    for key in ("verdict", "revision", "reviewer"):
        if key in state["review"] and not isinstance(state["review"][key], str):
            raise SystemExit(fail(f"invalid state at {path}: review.{key} is not a string"))
    if "required" in state["ci"] and not isinstance(state["ci"]["required"], bool):
        raise SystemExit(fail(f"invalid state at {path}: ci.required is not a boolean"))
    for key in ("status", "revision", "detail", "required_reason"):
        if key in state["ci"] and not isinstance(state["ci"][key], str):
            raise SystemExit(fail(f"invalid state at {path}: ci.{key} is not a string"))
    if "required" in state["pr"] and not isinstance(state["pr"]["required"], bool):
        raise SystemExit(fail(f"invalid state at {path}: pr.required is not a boolean"))
    if "merge_authorized" in state["pr"] and not isinstance(state["pr"]["merge_authorized"], bool):
        raise SystemExit(fail(f"invalid state at {path}: pr.merge_authorized is not a boolean"))
    for key in ("url", "state", "delivery", "required_reason", "merge_authorized_by"):
        if key in state["pr"] and not isinstance(state["pr"][key], str):
            raise SystemExit(fail(f"invalid state at {path}: pr.{key} is not a string"))
    for key in ("max_correction_cycles", "correction_cycles", "max_delegates", "delegates"):
        value = state["budget"].get(key)
        if value is not None and (not isinstance(value, int) or isinstance(value, bool)):
            raise SystemExit(fail(f"invalid state at {path}: budget.{key} is not an integer"))
    if "deadline" in state["budget"] and not isinstance(state["budget"]["deadline"], str):
        raise SystemExit(fail(f"invalid state at {path}: budget.deadline is not a string"))
    for key in ("model_cost_usd", "max_model_cost_usd"):
        value = state["budget"].get(key)
        if value is not None and (not isinstance(value, (int, float)) or isinstance(value, bool)):
            raise SystemExit(fail(f"invalid state at {path}: budget.{key} is not a number"))
    if not isinstance(state.get("implementers", []), list) or not all(
            isinstance(name, str) for name in state.get("implementers", [])):
        raise SystemExit(fail(f"invalid state at {path}: implementers is not a list of names"))
    if state.get("blocker") is not None and not isinstance(state["blocker"], dict):
        raise SystemExit(fail(f"invalid state at {path}: blocker is not a mapping"))
    for key in ("id", "objective", "phase", "revision"):
        if key in state and not isinstance(state[key], str):
            raise SystemExit(fail(f"invalid state at {path}: {key} is not a string"))
    return path, state


def write(path, state):
    state["updated_at"] = now()
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    handle, tmp = tempfile.mkstemp(dir=directory, prefix=".issue-", suffix=".json")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as out:
            json.dump(state, out, indent=2, sort_keys=False)
            out.write("\n")
            out.flush()
            os.fsync(out.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def event(state, kind, detail=""):
    state.setdefault("events", []).append({"at": now(), "kind": kind, "detail": detail})


def content_hash(text, check=""):
    payload = json.dumps([text, check], ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def find_criterion(state, criterion_id):
    for item in state.get("criteria", []):
        if item["id"] == criterion_id:
            return item
    raise SystemExit(fail(f"unknown criterion {criterion_id}"))


def parse_criteria(path):
    try:
        with open(path, encoding="utf-8") as handle:
            body = handle.read()
    except OSError as error:
        raise SystemExit(fail(f"cannot read criteria file {path}: {error}"))
    if path.endswith(".json"):
        try:
            data = json.loads(body)
        except ValueError as error:
            raise SystemExit(fail(f"invalid criteria JSON: {error}"))
        if not isinstance(data, list):
            raise SystemExit(fail("criteria JSON must be a list of strings or {text, check} objects"))
        items = []
        for entry in data:
            if isinstance(entry, str):
                items.append({"text": entry, "check": ""})
            elif isinstance(entry, dict) and entry.get("text"):
                items.append({"text": str(entry["text"]), "check": str(entry.get("check", ""))})
            else:
                raise SystemExit(fail("criteria JSON entries need text (and optional check)"))
        return items
    items = []
    for line in body.splitlines():
        match = re.match(r"^\s*(?:\d+[.)]|[-*])\s+(.+?)\s*$", line)
        if not match:
            continue
        text = match.group(1)
        check = ""
        split = re.split(r"\s+(?:—|--)\s+check:\s*", text, maxsplit=1)
        if len(split) == 2:
            text, check = split[0].rstrip(), split[1].strip()
        items.append({"text": text, "check": check})
    return items


def add_criteria(state, entries, by):
    existing = {item["id"] for item in state["criteria"]}
    for entry in entries:
        index = 1
        while f"C{index}" in existing:
            index += 1
        criterion_id = f"C{index}"
        existing.add(criterion_id)
        state["criteria"].append({
            "id": criterion_id,
            "text": entry["text"].strip(),
            "check": entry["check"].strip(),
            "content_sha": content_hash(entry["text"].strip(), entry["check"].strip()),
            "verdict": "PENDING",
            "evidence": "",
            "revision": "",
            "verified_by": "",
            "amendments": [],
        })
        event(state, "criterion-added", f"{criterion_id}: {entry['text'].strip()} (by {by})")


def check_deadline(value):
    try:
        datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        raise SystemExit(fail("deadline must be ISO 8601, for example 2026-11-26T18:00:00Z"))


def cmd_init(args):
    path = state_path(args)
    if os.path.exists(path) and not args.force:
        raise SystemExit(fail(f"state already exists at {path}; resume it or pass --force"))
    if args.deadline:
        check_deadline(args.deadline)
    implementers = [display_name(name) for name in args.implementer.split(",")]
    implementers = [name for name in implementers if name]
    if not implementers:
        raise SystemExit(fail("--implementer needs at least one non-empty name"))
    state = {
        "schema": SCHEMA,
        "id": args.issue,
        "objective": args.objective,
        "repo": os.path.abspath(args.repo or os.getcwd()),
        "profile": args.profile,
        "phase": "intake",
        "revision": args.revision or "",
        "implementers": implementers,
        "criteria": [],
        "review": {"verdict": "none", "revision": "", "reviewer": "",
                   "blocking": [], "nonblocking": [], "questions": []},
        "ci": {"required": args.ci_required, "status": "unknown", "revision": "",
               "detail": "", "required_reason": ""},
        "pr": {"required": args.pr_required, "url": "", "state": "",
               "delivery": args.delivery, "required_reason": "",
               "merge_authorized": False, "merge_authorized_by": ""},
        "budget": {
            "max_correction_cycles": args.max_correction_cycles,
            "max_delegates": args.max_delegates,
            "deadline": args.deadline or "",
            "max_model_cost_usd": args.max_model_cost_usd,
            "correction_cycles": 0,
            "delegates": 0,
            "model_cost_usd": None,
        },
        "blocker": None,
        "outcome": None,
        "events": [],
        "created_at": now(),
    }
    if args.criteria:
        add_criteria(state, parse_criteria(args.criteria), "criteria-engineer")
    event(state, "init", f"objective: {args.objective}")
    write(path, state)
    print(f"created {path}")
    return 0


def cmd_phase(args):
    path, state = read(args)
    if args.phase == "done" and state.get("phase") != "done":
        ok, reasons, _ = evaluate(state)
        if not ok:
            raise SystemExit(fail("cannot mark done; gate fails: " + "; ".join(reasons)))
    state["phase"] = args.phase
    if args.phase == "done":
        state["outcome"] = "success"
    event(state, "phase", args.phase)
    write(path, state)
    print(f"phase: {args.phase}")
    return 0


def invalidate_stale(state, revision):
    """Evidence tied to another revision no longer certifies the delivered code."""
    for item in state.get("criteria", []):
        if item.get("revision") and item["revision"] != revision and item["verdict"] == "PASS":
            item["verdict"] = "PENDING"
            item["evidence"] = ""
            item["verified_by"] = ""
            item["revision"] = ""
    review = state.get("review", {})
    if review.get("revision") and review["revision"] != revision:
        review["verdict"] = "none"
        review["revision"] = ""
    ci = state.get("ci", {})
    if ci.get("revision") and ci["revision"] != revision:
        ci["status"] = "unknown"
        ci["revision"] = ""


def cmd_revision(args):
    path, state = read(args)
    previous = state.get("revision", "")
    state["revision"] = args.revision
    invalidate_stale(state, args.revision)
    if state.get("phase") == "done":
        state["phase"] = "implement"
        state["outcome"] = None
    event(state, "revision", f"{previous or '(none)'} -> {args.revision}; stale evidence invalidated")
    write(path, state)
    print(f"revision: {args.revision}")
    return 0


def cmd_criteria_list(args):
    _, state = read(args)
    for item in state.get("criteria", []):
        print(f"{item['id']}\t{item['verdict']}\t{item['text']}")
    return 0


def cmd_criteria_add(args):
    path, state = read(args)
    add_criteria(state, [{"text": args.text, "check": args.check or ""}], args.by)
    write(path, state)
    print(f"added {state['criteria'][-1]['id']}")
    return 0


def cmd_criteria_verdict(args):
    path, state = read(args)
    item = find_criterion(state, args.id)
    verdict = "NOT VERIFIED" if args.verdict == "not-verified" else args.verdict.upper()
    if verdict not in VERDICTS:
        raise SystemExit(fail("verdict must be pass, fail, or not-verified"))
    revision = args.revision or state.get("revision", "")
    if verdict in ("PASS", "FAIL") and not args.evidence:
        raise SystemExit(fail("PASS and FAIL require --evidence"))
    if verdict == "PASS" and not revision:
        raise SystemExit(fail("PASS requires an implementation revision"))
    verifier = display_name(args.by or "")
    if verdict in ("PASS", "FAIL") and not verifier:
        raise SystemExit(fail("PASS and FAIL require a verifier name with --by"))
    if verdict in ("PASS", "FAIL") and normalize_name(verifier) in {
            normalize_name(name) for name in state.get("implementers", [])}:
        raise SystemExit(fail("verifier is the implementer; verification must be independent"))
    item["verdict"] = verdict
    item["evidence"] = args.evidence or ""
    item["revision"] = revision if verdict in ("PASS", "FAIL") else ""
    item["verified_by"] = verifier
    event(state, "criterion-verdict", f"{item['id']} {verdict} at {revision or '(no revision)'}")
    write(path, state)
    print(f"{item['id']}: {verdict}")
    return 0


def cmd_criteria_amend(args):
    path, state = read(args)
    if not args.justification.strip() or not display_name(args.approved_by):
        raise SystemExit(fail("amend requires --justification and --approved-by"))
    approved = [display_name(name) for name in args.approved_by.split(",")]
    approved = [name for name in approved if name]
    implementer_keys = {normalize_name(name) for name in state.get("implementers", [])}
    overlap = [name for name in approved if normalize_name(name) in implementer_keys]
    if overlap:
        raise SystemExit(fail(f"amendment needs independent approval; also implementer: {', '.join(overlap)}"))
    item = find_criterion(state, args.id)
    before_text = item["text"]
    before_check = item["check"]
    if args.text:
        item["text"] = args.text.strip()
    if args.check:
        item["check"] = args.check.strip()
    if item["text"] == before_text and item["check"] == before_check:
        raise SystemExit(fail("amendment changes nothing"))
    item["content_sha"] = content_hash(item["text"], item["check"])
    item.setdefault("amendments", []).append({
        "at": now(),
        "from_text": before_text,
        "to_text": item["text"],
        "from_check": before_check,
        "to_check": item["check"],
        "justification": args.justification.strip(),
        "approved_by": approved,
    })
    item["verdict"] = "PENDING"
    item["evidence"] = ""
    item["revision"] = ""
    event(state, "criterion-amended", f"{item['id']} approved by {', '.join(approved)}")
    write(path, state)
    print(f"{item['id']}: amended")
    return 0


def cmd_review(args):
    path, state = read(args)
    reviewer = display_name(args.reviewer or "")
    if not reviewer:
        raise SystemExit(fail("review requires a non-empty --reviewer"))
    revision = args.revision or state.get("revision", "")
    if not revision:
        raise SystemExit(fail("review requires a revision"))
    reviewer_key = normalize_name(reviewer)
    if reviewer_key in {normalize_name(name) for name in state.get("implementers", [])}:
        raise SystemExit(fail("reviewer is the implementer; review must be independent"))
    state["review"] = {
        "verdict": args.verdict,
        "revision": revision,
        "reviewer": reviewer,
        "blocking": args.blocking or [],
        "nonblocking": args.nonblocking or [],
        "questions": args.question or [],
    }
    event(state, "review", f"{args.verdict} at {revision} by {reviewer}")
    write(path, state)
    print(f"review: {args.verdict}")
    return 0


def cmd_ci(args):
    path, state = read(args)
    status = args.status
    if status == "pass":
        status = "green"
    if status == "fail":
        status = "failing"
    if status not in CI_STATES:
        raise SystemExit(fail("status must be green, failing, pending, or unknown"))
    required = state["ci"].get("required", True)
    if args.required is not None:
        if args.required is False and required is True and not (args.reason or "").strip():
            raise SystemExit(fail("disabling required CI needs --reason"))
        required = args.required
    state["ci"] = {
        "required": required,
        "status": status,
        "revision": args.revision or state.get("revision", ""),
        "detail": args.detail or "",
        "required_reason": (args.reason or state["ci"].get("required_reason", ""))
        if not required else "",
    }
    event(state, "ci", f"{status} at {state['ci']['revision'] or '(no revision)'}"
                       + (f"; required={required} reason={args.reason}" if args.reason else ""))
    write(path, state)
    print(f"ci: {status}")
    return 0


def cmd_pr(args):
    path, state = read(args)
    if args.state not in PR_STATES:
        raise SystemExit(fail(f"state must be one of {', '.join(PR_STATES)}"))
    required = state["pr"].get("required", True)
    if args.required is not None:
        if args.required is False and required is True and not (args.reason or "").strip():
            raise SystemExit(fail("disabling the required PR needs --reason"))
        required = args.required
    state["pr"].update({
        "url": args.url or state["pr"].get("url", ""),
        "state": args.state,
        "delivery": args.delivery or state["pr"].get("delivery", "merge-ready"),
        "required": required,
        "required_reason": (args.reason or state["pr"].get("required_reason", ""))
        if not required else "",
    })
    event(state, "pr", f"{args.state} {state['pr']['url']}".strip())
    write(path, state)
    print(f"pr: {args.state}")
    return 0


def cmd_authorize_merge(args):
    path, state = read(args)
    source = display_name(args.by or "")
    if not source:
        raise SystemExit(fail("authorize-merge needs --by"))
    if normalize_name(source) in {normalize_name(name) for name in state.get("implementers", [])}:
        raise SystemExit(fail("merge authorization cannot come from an implementer"))
    state["pr"]["merge_authorized"] = True
    state["pr"]["merge_authorized_by"] = source
    event(state, "merge-authorized", source)
    write(path, state)
    print(f"merge authorized by {source}")
    return 0


def cmd_budget(args):
    path, state = read(args)
    budget = state["budget"]
    if args.max_correction_cycles is not None:
        budget["max_correction_cycles"] = args.max_correction_cycles
    if args.max_delegates is not None:
        budget["max_delegates"] = args.max_delegates
    if args.deadline is not None:
        if args.deadline:
            check_deadline(args.deadline)
        budget["deadline"] = args.deadline
    if args.max_model_cost_usd is not None:
        previous = budget.get("max_model_cost_usd")
        if previous is not None and args.max_model_cost_usd > previous \
                and budget.get("model_cost_usd") is not None and not (args.reason or "").strip():
            raise SystemExit(fail("raising the cost ceiling after spend needs --reason"))
        budget["max_model_cost_usd"] = args.max_model_cost_usd
        if args.reason:
            budget["max_model_cost_reason"] = args.reason.strip()
    if args.model_cost_usd is not None:
        budget["model_cost_usd"] = args.model_cost_usd
    event(state, "budget", json.dumps(budget, sort_keys=True))
    write(path, state)
    print("budget updated")
    return 0


def cmd_record(args):
    path, state = read(args)
    budget = state["budget"]
    if args.kind == "delegate":
        budget["delegates"] = int(budget.get("delegates", 0)) + 1
        detail = f"{args.name or 'delegate'} profile={args.profile or '?'} model={args.model or '?'}"
    elif args.kind == "correction":
        budget["correction_cycles"] = int(budget.get("correction_cycles", 0)) + 1
        detail = args.summary or ""
    else:
        detail = args.summary or ""
    state.setdefault("attempts", []).append({
        "at": now(), "kind": args.kind, "detail": detail, "result": args.result or "",
    })
    event(state, f"record-{args.kind}", detail)
    write(path, state)
    print(f"recorded {args.kind}")
    return 0


def cmd_block(args):
    path, state = read(args)
    if not args.problem.strip() or not args.next_action.strip():
        raise SystemExit(fail("block requires --problem and --next-action"))
    state["blocker"] = {
        "kind": args.kind,
        "problem": args.problem.strip(),
        "attempted": args.attempted or [],
        "options": args.options or [],
        "next_action": args.next_action.strip(),
        "at": now(),
    }
    state["phase"] = "blocked"
    state["outcome"] = "blocked"
    event(state, "blocked", f"{args.kind}: {args.problem.strip()}")
    write(path, state)
    print("blocked")
    return 3


def cmd_unblock(args):
    path, state = read(args)
    state["blocker"] = None
    state["outcome"] = None
    state["phase"] = args.phase
    event(state, "unblocked", f"resume at {args.phase}")
    write(path, state)
    print(f"unblocked at {args.phase}")
    return 0


def budget_exhausted(state):
    budget = state.get("budget", {})
    deadline = budget.get("deadline")
    if deadline:
        try:
            due = datetime.datetime.fromisoformat(deadline.replace("Z", "+00:00"))
        except ValueError:
            return "invalid deadline recorded"
        if due.tzinfo is None:
            due = due.replace(tzinfo=datetime.timezone.utc)
        if datetime.datetime.now(datetime.timezone.utc) > due:
            return f"deadline {deadline} passed"
    cycles = int(budget.get("correction_cycles", 0))
    maximum = int(budget.get("max_correction_cycles", 3))
    if cycles > maximum:
        return f"correction cycles {cycles} exceed maximum {maximum}"
    cost = budget.get("model_cost_usd")
    ceiling = budget.get("max_model_cost_usd")
    if cost is not None and ceiling is not None and float(cost) > float(ceiling):
        return f"model cost ${cost} exceeds ceiling ${ceiling}"
    return ""


def evaluate(state):
    """Return (complete, reasons, warnings). Deterministic completion gate."""
    reasons = []
    warnings = []
    criteria = state.get("criteria", [])
    revision = state.get("revision", "")
    implementer_keys = {normalize_name(name) for name in state.get("implementers", [])}

    if not criteria:
        reasons.append("no acceptance criteria recorded")
    if not implementer_keys:
        reasons.append("implementer not recorded; independence unproven")
    for item in criteria:
        if content_hash(item.get("text", ""), item.get("check", "")) != item.get("content_sha"):
            reasons.append(f"{item['id']} content changed without a recorded amendment")
        if not item.get("check"):
            reasons.append(f"{item['id']} has no deciding check")
        if item.get("verdict") != "PASS":
            reasons.append(f"{item['id']} is {item.get('verdict', 'PENDING')}")
        elif not item.get("evidence"):
            reasons.append(f"{item['id']} PASS has no evidence")
        elif not item.get("revision") or item["revision"] != revision:
            reasons.append(f"{item['id']} evidence is not for revision {revision or '(none)'}")
        elif not normalize_name(item.get("verified_by", "")):
            reasons.append(f"{item['id']} PASS has no verifier")
        elif normalize_name(item["verified_by"]) in implementer_keys:
            reasons.append(f"{item['id']} was verified by its implementer")
        for amendment in item.get("amendments", []):
            approved = amendment.get("approved_by") or []
            if isinstance(approved, str):
                approved = [approved]
            approved = [name for name in approved if isinstance(name, str) and normalize_name(name)]
            if not amendment.get("justification") or not approved:
                reasons.append(f"{item['id']} has an unjustified amendment")
            elif not [name for name in approved if normalize_name(name) not in implementer_keys]:
                reasons.append(f"{item['id']} amendment lacks independent approval")

    review = state.get("review", {})
    if review.get("verdict") != "approve":
        reasons.append(f"review verdict is {review.get('verdict', 'none')}")
    if review.get("verdict") == "approve" and review.get("revision") != revision:
        reasons.append("review is not for the delivered revision")
    if review.get("blocking"):
        reasons.append(f"{len(review['blocking'])} blocking review finding(s) remain")
    if review.get("verdict") == "approve" and review.get("reviewer"):
        if normalize_name(review["reviewer"]) in implementer_keys:
            reasons.append("reviewer is the implementer")
    elif review.get("verdict") == "approve":
        reasons.append("reviewer identity missing; independence unproven")

    ci = state.get("ci", {})
    if ci.get("required", True):
        if ci.get("status") != "green":
            reasons.append(f"required CI is {ci.get('status', 'unknown')}")
        elif ci.get("revision") != revision:
            reasons.append("CI result is not for the delivered revision")

    pr = state.get("pr", {})
    if pr.get("required", True):
        if not pr.get("url"):
            reasons.append("PR url missing")
        if pr.get("state") not in ("ready", "merged"):
            reasons.append(f"PR state is {pr.get('state') or 'none'}; must be ready or merged")
    if pr.get("state") == "merged" and not pr.get("merge_authorized"):
        reasons.append("PR merged without recorded merge authorization")

    exhausted = budget_exhausted(state)
    if exhausted:
        reasons.append(exhausted)

    if state.get("blocker"):
        reasons.append(f"blocker recorded: {state['blocker'].get('problem', '')}")
    if not revision:
        reasons.append("no implementation revision recorded")
    return not reasons, reasons, warnings


def cmd_gate(args):
    _, state = read(args)
    complete, reasons, warnings = evaluate(state)
    exhausted = budget_exhausted(state)
    if complete:
        print(f"PASS {state['id']}: verified complete at revision {state.get('revision')}")
        for warning in warnings:
            print(f"WARN {warning}")
        return 0
    if state.get("blocker"):
        print(f"BLOCKED {state['id']}: {state['blocker'].get('problem', '')}")
    else:
        print(f"INCOMPLETE {state['id']}")
    for reason in reasons:
        print(f"FAIL {reason}")
    for warning in warnings:
        print(f"WARN {warning}")
    return 4 if exhausted and not any("blocker recorded" in r for r in reasons) else (3 if state.get("blocker") else 1)


def cmd_status(args):
    _, state = read(args)
    if args.json:
        print(json.dumps(state, indent=2))
        return 0
    budget = state.get("budget", {})
    print(f"issue: {state['id']}")
    print(f"objective: {state['objective']}")
    print(f"phase: {state['phase']}  profile: {state.get('profile')}  revision: {state.get('revision') or '(none)'}")
    for item in state.get("criteria", []):
        print(f"  {item['id']} {item['verdict']:<12} {item['text'][:70]}")
    review = state.get("review", {})
    print(f"review: {review.get('verdict')} by {review.get('reviewer') or '?'} at {review.get('revision') or '-'}")
    ci = state.get("ci", {})
    print(f"ci: {ci.get('status')} required={ci.get('required')} at {ci.get('revision') or '-'}")
    print(f"pr: {state['pr'].get('state') or '-'} {state['pr'].get('url') or ''}".rstrip())
    print(f"budget: cycles {budget.get('correction_cycles', 0)}/{budget.get('max_correction_cycles')} "
          f"delegates {budget.get('delegates', 0)}/{budget.get('max_delegates')} deadline {budget.get('deadline') or '-'}")
    if state.get("blocker"):
        print(f"blocker: {state['blocker'].get('kind')}: {state['blocker'].get('problem')}")
    return 0


def render_report(state):
    complete, reasons, warnings = evaluate(state)
    outcome = state.get("outcome")
    if complete:
        status = "Verified complete" if state["pr"].get("state") != "merged" else "Verified, merged"
        if state["pr"].get("state") == "ready":
            status = "Verified, merge ready"
    elif state.get("blocker"):
        status = "Blocked"
    else:
        status = "Incomplete"
    lines = [
        f"# {state['id']}",
        "",
        f"Status: {status}",
        f"Objective: {state['objective']}",
        f"Revision: {state.get('revision') or '(none)'}",
        f"Profile: {state.get('profile')}",
        "",
        "## Acceptance criteria",
    ]
    for item in state.get("criteria", []):
        evidence = f" — {item['evidence']}" if item.get("evidence") else ""
        lines.append(f"- {item['id']} {item['verdict']}: {item['text']}{evidence}")
    lines += ["", "## Independent review"]
    review = state.get("review", {})
    lines.append(f"{review.get('verdict', 'none')} by {review.get('reviewer') or '?'} at {review.get('revision') or '-'}")
    for finding in review.get("blocking", []):
        lines.append(f"- Blocking: {finding}")
    lines += ["", "## CI and delivery"]
    ci = state.get("ci", {})
    lines.append(f"CI: {ci.get('status')} at {ci.get('revision') or '-'} (required={ci.get('required')})")
    lines.append(f"PR: {state['pr'].get('state') or '-'} {state['pr'].get('url') or ''}".rstrip())
    budget = state.get("budget", {})
    lines += [
        "",
        "## Resources",
        f"Correction cycles: {budget.get('correction_cycles', 0)}/{budget.get('max_correction_cycles')}",
        f"Delegates: {budget.get('delegates', 0)}/{budget.get('max_delegates')}",
        f"Deadline: {budget.get('deadline') or 'none'}",
        f"Model cost: {budget.get('model_cost_usd') if budget.get('model_cost_usd') is not None else 'not reported'}",
    ]
    if state.get("blocker"):
        blocker = state["blocker"]
        lines += ["", "## Blocker", f"{blocker.get('kind')}: {blocker.get('problem')}"]
        for item in blocker.get("attempted", []):
            lines.append(f"- Attempted: {item}")
        for item in blocker.get("options", []):
            lines.append(f"- Option: {item}")
        lines.append(f"Required human action: {blocker.get('next_action')}")
    if state.get("blocker") and complete:
        lines += ["", "WARN: a blocker is recorded; this issue is not complete."]
    elif reasons and not state.get("blocker"):
        lines += ["", "## Open gates"]
        lines += [f"- {reason}" for reason in reasons]
    for warning in warnings:
        lines.append(f"WARN: {warning}")
    return "\n".join(lines) + "\n"


def atomic_write_text(path, body):
    directory = os.path.dirname(os.path.abspath(path))
    try:
        os.makedirs(directory, exist_ok=True)
        handle, tmp = tempfile.mkstemp(dir=directory, prefix=".report-", suffix=".md")
        try:
            with os.fdopen(handle, "w", encoding="utf-8") as out:
                out.write(body)
                out.flush()
                os.fsync(out.fileno())
            os.chmod(tmp, 0o600)
            os.replace(tmp, path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)
    except OSError as error:
        raise SystemExit(fail(f"cannot write report {path}: {error}"))


def cmd_report(args):
    path, state = read(args)
    body = render_report(state)
    print(body, end="")
    if args.write:
        report_path = path[: -len(".json")] + ".md"
        atomic_write_text(report_path, body)
        print(f"wrote {report_path}", file=sys.stderr)
    return 0


def build_parser():
    parser = argparse.ArgumentParser(description="Persist and gate autonomous issue state.")
    parser.add_argument("--issue", required=True, help="issue identifier, for example PAY-142")
    parser.add_argument("--state-dir", help="state directory (default .smart-delegate/issues)")
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="create state for a new issue")
    init.add_argument("--objective", required=True)
    init.add_argument("--repo")
    init.add_argument("--profile", choices=PROFILES, default="standard")
    init.add_argument("--revision", default="")
    init.add_argument("--implementer", required=True,
                      help="implementer name(s), comma separated; never the reviewer or verifier")
    init.add_argument("--criteria", help="criteria JSON or Markdown list")
    init.add_argument("--ci-required", action=argparse.BooleanOptionalAction, default=True)
    init.add_argument("--pr-required", action=argparse.BooleanOptionalAction, default=True)
    init.add_argument("--delivery", choices=("merge-ready", "merged"), default="merge-ready")
    init.add_argument("--max-correction-cycles", type=int, default=3)
    init.add_argument("--max-delegates", type=int, default=3)
    init.add_argument("--max-model-cost-usd", type=float, default=None)
    init.add_argument("--deadline")
    init.add_argument("--force", action="store_true")
    init.set_defaults(func=cmd_init)

    phase = sub.add_parser("set-phase", help="set the execution phase")
    phase.add_argument("phase", choices=PHASES)
    phase.set_defaults(func=cmd_phase)

    revision = sub.add_parser("set-revision", help="pin a new revision and invalidate stale evidence")
    revision.add_argument("revision")
    revision.set_defaults(func=cmd_revision)

    listing = sub.add_parser("criteria", help="list acceptance criteria")
    listing.set_defaults(func=cmd_criteria_list)

    add = sub.add_parser("criteria-add", help="add one acceptance criterion")
    add.add_argument("--text", required=True)
    add.add_argument("--check", default="")
    add.add_argument("--by", default="coordinator")
    add.set_defaults(func=cmd_criteria_add)

    verdict = sub.add_parser("criteria-verdict", help="record a verifier verdict")
    verdict.add_argument("--id", required=True)
    verdict.add_argument("--verdict", required=True, choices=("pass", "fail", "not-verified", "PASS", "FAIL"))
    verdict.add_argument("--evidence", default="")
    verdict.add_argument("--revision", default="")
    verdict.add_argument("--by", default="")
    verdict.set_defaults(func=cmd_criteria_verdict)

    amend = sub.add_parser("criteria-amend", help="change a criterion with justification and independent approval")
    amend.add_argument("--id", required=True)
    amend.add_argument("--text")
    amend.add_argument("--check")
    amend.add_argument("--justification", required=True)
    amend.add_argument("--approved-by", required=True)
    amend.set_defaults(func=cmd_criteria_amend)

    review = sub.add_parser("review", help="record an independent review verdict")
    review.add_argument("--verdict", required=True, choices=("approve", "request-changes"))
    review.add_argument("--revision", default="")
    review.add_argument("--reviewer", required=True)
    review.add_argument("--blocking", action="append")
    review.add_argument("--nonblocking", action="append")
    review.add_argument("--question", action="append")
    review.set_defaults(func=cmd_review)

    ci = sub.add_parser("ci", help="record required CI status")
    ci.add_argument("--status", required=True, choices=("green", "failing", "pending", "unknown", "pass", "fail"))
    ci.add_argument("--revision", default="")
    ci.add_argument("--detail", default="")
    ci.add_argument("--required", action=argparse.BooleanOptionalAction, default=None)
    ci.add_argument("--reason", help="required when disabling a previously required check")
    ci.set_defaults(func=cmd_ci)

    pr = sub.add_parser("pr", help="record pull request state and delivery policy")
    pr.add_argument("--url", default="")
    pr.add_argument("--state", required=True, choices=PR_STATES)
    pr.add_argument("--delivery", choices=("merge-ready", "merged"))
    pr.add_argument("--required", action=argparse.BooleanOptionalAction, default=None)
    pr.add_argument("--reason", help="required when disabling a previously required PR")
    pr.set_defaults(func=cmd_pr)

    authorize = sub.add_parser("authorize-merge", help="record explicit merge authorization")
    authorize.add_argument("--by", required=True, help="human, config key, or policy that authorized it")
    authorize.set_defaults(func=cmd_authorize_merge)

    budget = sub.add_parser("budget", help="read or update execution limits")
    budget.add_argument("--max-correction-cycles", type=int)
    budget.add_argument("--max-delegates", type=int)
    budget.add_argument("--deadline")
    budget.add_argument("--max-model-cost-usd", type=float)
    budget.add_argument("--model-cost-usd", type=float)
    budget.add_argument("--reason")
    budget.set_defaults(func=cmd_budget)

    record = sub.add_parser("record", help="record a delegate, correction, or attempt")
    record.add_argument("kind", choices=("delegate", "correction", "attempt"))
    record.add_argument("--name")
    record.add_argument("--profile")
    record.add_argument("--model")
    record.add_argument("--summary")
    record.add_argument("--result", choices=("ok", "failed", "partial"))
    record.set_defaults(func=cmd_record)

    block = sub.add_parser("block", help="record a genuine blocker")
    block.add_argument("--kind", required=True, choices=BLOCKER_KINDS)
    block.add_argument("--problem", required=True)
    block.add_argument("--attempted", action="append")
    block.add_argument("--options", action="append")
    block.add_argument("--next-action", required=True)
    block.set_defaults(func=cmd_block)

    unblock = sub.add_parser("unblock", help="clear a blocker and resume")
    unblock.add_argument("--phase", choices=(
        "intake", "discovery", "criteria", "implement", "review", "verify", "pr", "ci"),
        default="implement")
    unblock.set_defaults(func=cmd_unblock)

    gate = sub.add_parser("gate", help="check completion evidence")
    gate.set_defaults(func=cmd_gate)

    status = sub.add_parser("status", help="print execution state")
    status.add_argument("--json", action="store_true")
    status.set_defaults(func=cmd_status)

    report = sub.add_parser("report", help="render a concise completion or blocker report")
    report.add_argument("--write", action="store_true")
    report.set_defaults(func=cmd_report)
    return parser


def main():
    args = build_parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
