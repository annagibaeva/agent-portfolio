-- Idempotent. Created in dependency order.
create extension if not exists "pgcrypto";

create table if not exists competitors (
  id uuid primary key default gen_random_uuid(),
  name text unique not null,
  feed_url text,
  html_url text not null,
  css_hint text,
  active boolean not null default true,
  created_at timestamptz default now()
);

create table if not exists runs (
  id uuid primary key default gen_random_uuid(),
  started_at timestamptz default now(),
  finished_at timestamptz,
  status text not null,
  competitors_ok int default 0,
  competitors_failed int default 0,
  new_entries int default 0,
  tokens int default 0,
  outcome text
);

create table if not exists changelog_entries (
  id uuid primary key default gen_random_uuid(),
  competitor_id uuid references competitors(id),
  title text not null,
  body text,
  entry_date date,
  url text,
  content_hash text not null,
  body_hash text not null,
  first_seen_run uuid references runs(id),
  last_updated_run uuid references runs(id),
  created_at timestamptz default now(),
  unique (competitor_id, content_hash)
);

create table if not exists commentary (
  id uuid primary key default gen_random_uuid(),
  entry_id uuid references changelog_entries(id),
  run_id uuid references runs(id),
  kind text not null check (kind in ('per_change','synthesis')),
  so_what text,
  tag text check (tag in ('Threat','Parity gap','Table stakes','Noise')),
  confidence numeric check (confidence between 0 and 1),
  synthesis jsonb,
  created_at timestamptz default now()
);
