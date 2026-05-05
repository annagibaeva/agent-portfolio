#!/usr/bin/env bash
# PreToolUse hook for the db-reader subagent.
#
# Reads a JSON payload on stdin (Claude Code PreToolUse contract) describing a
# pending Bash tool call, and exits 0 to allow or 2 to block. On block, stderr
# is surfaced back to the model so it knows why.
#
# Allowlist: command must invoke one of the supported read-only DB CLIs and
# the SQL body must contain no write/DDL/session-mutating tokens.

set -euo pipefail

payload="$(cat)"

# Extract the command string. jq is the right tool; fall back to a grep if jq
# is missing on the host so the hook still fails closed rather than open.
if command -v jq >/dev/null 2>&1; then
  cmd="$(printf '%s' "$payload" | jq -r '.tool_input.command // empty')"
else
  echo "validate-readonly-query: jq not installed — failing closed" >&2
  exit 2
fi

if [[ -z "$cmd" ]]; then
  echo "validate-readonly-query: no command field in payload — failing closed" >&2
  exit 2
fi

# Reject shell chaining outright. One statement, one invocation. This also
# stops `psql -c 'SELECT 1' && psql -c 'DROP TABLE x'` style smuggling.
if [[ "$cmd" =~ (\&\&|\|\||\;|\`|\$\() ]]; then
  echo "BLOCKED: shell chaining/substitution not allowed in db-reader (found one of && || ; \` \$()" >&2
  exit 2
fi

# Allowlist of binaries this agent may invoke. Anything else is denied — the
# agent is for DB reads, not general shell.
allowed_bin_re='^[[:space:]]*(psql|mysql|sqlite3|bq|duckdb|clickhouse-client|mongosh)([[:space:]]|$)'
if ! [[ "$cmd" =~ $allowed_bin_re ]]; then
  echo "BLOCKED: db-reader may only invoke psql, mysql, sqlite3, bq, duckdb, clickhouse-client, or mongosh." >&2
  exit 2
fi

# Lowercase copy for keyword scanning. We don't try to be a SQL parser — we
# just look for write/DDL keywords as whole words. False positives are
# acceptable; false negatives are not.
lower="${cmd,,}"

# Strip single- and double-quoted string literals so a literal like
# 'DROP something' inside a SELECT doesn't trip the scanner. Greedy is fine
# here — if quoting is weird enough to confuse this regex, block it.
stripped="$(printf '%s' "$lower" | sed -E "s/'[^']*'//g; s/\"[^\"]*\"//g")"

# Strip SQL comments (-- to end of line, /* */ blocks).
stripped="$(printf '%s' "$stripped" | sed -E 's|--[^"\n]*||g; s|/\*[^*]*\*+([^/*][^*]*\*+)*/||g')"

deny_keywords=(
  insert update delete merge upsert replace truncate
  create alter drop rename
  grant revoke
  copy load
  call exec execute
  lock vacuum reindex cluster
  attach detach
  "set global" "set session" "set role"
  "into outfile" "into dumpfile"
)

for kw in "${deny_keywords[@]}"; do
  # \b word boundaries so "selected" doesn't match "select" prefix.
  if [[ "$stripped" =~ (^|[^a-z_])${kw}([^a-z_]|$) ]]; then
    echo "BLOCKED: query contains write/DDL keyword: '${kw}'" >&2
    exit 2
  fi
done

# bq-specific: block subcommands that mutate or load data.
if [[ "$lower" =~ ^[[:space:]]*bq[[:space:]] ]]; then
  if [[ "$lower" =~ bq[[:space:]]+(cp|load|mk|rm|update|insert|extract[[:space:]]+--destination) ]]; then
    echo "BLOCKED: bq subcommand mutates or exports data." >&2
    exit 2
  fi
fi

# psql/mysql -c with multiple statements: refuse if a stripped semicolon
# remains *inside* the SQL body. We approximate by counting semicolons in the
# stripped form — one trailing ; is fine, more than that is multi-statement.
semis="$(printf '%s' "$stripped" | tr -cd ';' | wc -c | tr -d ' ')"
if (( semis > 1 )); then
  echo "BLOCKED: multi-statement SQL not allowed (found ${semis} semicolons)." >&2
  exit 2
fi

exit 0
