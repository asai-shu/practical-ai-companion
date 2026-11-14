-- 入試 英単語 ナイン：パスキー＋認証アプリ（TOTP）の2段階認証（2026-11-14 に nyushi-eitango-nine へ適用）
-- 方針：ブラウザはデータベースに直接触れない。すべて Edge Function「nine-auth」（service role）を通す。
--       だから、どの表も anon / authenticated には権限を与えない（RLS も有効にしたまま、ポリシーなし）。

-- 利用者：2段階認証の秘密の情報は暗号化して持つ（暗号化のかぎは Vault に置く）
alter table public.app_users
  add column if not exists totp_secret_enc  text,              -- 有効にした認証アプリの秘密（暗号化済み）
  add column if not exists totp_pending_enc text,              -- 設定の途中の秘密（6桁のコードを確かめたら上へ移す）
  add column if not exists totp_enabled     boolean not null default false,
  add column if not exists totp_last_step   bigint  not null default 0;   -- 同じ6桁のコードを2回使わせないため
create unique index if not exists app_users_recovery_code_hash_key on public.app_users (recovery_code_hash);

-- パスキー：公開鍵は base64url の文字列で持つ（まだ1件も入っていない表なので型を変えてよい）
alter table public.passkeys alter column public_key type text using encode(public_key, 'base64');
alter table public.passkeys add column if not exists last_used_at timestamptz;

-- WebAuthn の確認用の値（チャレンジ）。1回使ったら消す。5分で期限切れ
create table if not exists public.webauthn_challenges (
  id          uuid primary key default gen_random_uuid(),
  challenge   text not null,
  kind        text not null check (kind in ('register', 'login', 'add')),
  user_id     uuid references public.app_users(id) on delete cascade,
  data        jsonb not null default '{}'::jsonb,
  expires_at  timestamptz not null default now() + interval '5 minutes'
);

-- ログイン中の記録。トークンそのものは保存せず、ハッシュだけ持つ
create table if not exists public.sessions (
  token_hash   text primary key,
  user_id      uuid not null references public.app_users(id) on delete cascade,
  full_access  boolean not null default false,     -- false＝パスキーは通ったが、まだ6桁のコードが必要
  created_at   timestamptz not null default now(),
  last_seen_at timestamptz not null default now(),
  expires_at   timestamptz not null
);
create index if not exists sessions_user_id_idx on public.sessions (user_id);

-- 試行回数の記録（総当たりを防ぐ）
create table if not exists public.auth_attempts (
  id     bigint generated always as identity primary key,
  bucket text not null,
  at     timestamptz not null default now()
);
create index if not exists auth_attempts_bucket_at_idx on public.auth_attempts (bucket, at);

alter table public.webauthn_challenges enable row level security;
alter table public.sessions            enable row level security;
alter table public.auth_attempts       enable row level security;

revoke all on public.app_users, public.passkeys, public.user_state,
              public.webauthn_challenges, public.sessions, public.auth_attempts
  from anon, authenticated;

-- 2段階認証の秘密を暗号化するかぎ：Vault に入れ、service role だけが取り出せる関数を通す
do $$
begin
  if not exists (select 1 from vault.secrets where name = 'nine_totp_key') then
    perform vault.create_secret(encode(extensions.gen_random_bytes(32), 'base64'), 'nine_totp_key', 'nine-auth: TOTP秘密の暗号化キー');
  end if;
end $$;

create or replace function public.nine_totp_key()
returns text
language sql
security definer
set search_path = ''
as $$ select decrypted_secret from vault.decrypted_secrets where name = 'nine_totp_key' limit 1 $$;
revoke execute on function public.nine_totp_key() from public, anon, authenticated;
grant  execute on function public.nine_totp_key() to service_role;
