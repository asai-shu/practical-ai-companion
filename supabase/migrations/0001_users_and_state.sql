-- 入試 英単語 ナイン：ログインと学習記録の保存用のテーブル（まだどのプロジェクトにも適用していない）
-- 方針：ニックネーム＋パスキー。メールアドレスや本名は保存しない。

create table if not exists public.app_users (
  id uuid primary key default gen_random_uuid(),
  nickname text not null check (char_length(nickname) between 1 and 20),
  recovery_code_hash text not null,          -- 復旧コードのハッシュ（元の値は保存しない）
  created_at timestamptz not null default now()
);

create table if not exists public.passkeys (
  credential_id text primary key,            -- パスキーのID（base64url）
  user_id uuid not null references public.app_users(id) on delete cascade,
  public_key bytea not null,                 -- 公開鍵（秘密鍵は利用者の端末から出ない）
  counter bigint not null default 0,
  transports text[],
  created_at timestamptz not null default now()
);
create index if not exists passkeys_user_id_idx on public.passkeys(user_id);

create table if not exists public.user_state (
  user_id uuid primary key references public.app_users(id) on delete cascade,
  state jsonb not null default '{}'::jsonb,  -- 学習記録・単語帳・ブックマーク（アプリの保存内容そのまま）
  updated_at timestamptz not null default now()
);

-- 行レベルのアクセス制限：本人だけが自分の記録を読み書きできる。
-- Edge Functions が発行するトークン（JWT）の sub に app_users.id を入れる前提。
alter table public.app_users enable row level security;
alter table public.passkeys enable row level security;
alter table public.user_state enable row level security;

create policy "本人だけが自分の情報を読める" on public.app_users
  for select using (id = (select auth.uid()));

create policy "本人だけが自分の記録を読める" on public.user_state
  for select using (user_id = (select auth.uid()));
create policy "本人だけが自分の記録を作れる" on public.user_state
  for insert with check (user_id = (select auth.uid()));
create policy "本人だけが自分の記録を更新できる" on public.user_state
  for update using (user_id = (select auth.uid())) with check (user_id = (select auth.uid()));

-- passkeys には利用者向けのポリシーを作らない（Edge Functions だけが service role で読み書きする）。
