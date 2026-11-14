-- 入試 英単語 ナイン：ブラウザから使える権限を、必要なものだけに絞る（2026-11-14 に nyushi-eitango-nine へ適用）
-- anon（ログインしていない人）は、どの表にも触れない。
-- authenticated（ログインした人）は、自分の利用者情報を読むことと、自分の学習記録の読み書きだけ（行は RLS で本人に限る）。
-- passkeys（パスキーの公開鍵）は、Edge Functions が service role で扱うだけで、ブラウザからは読めないようにする。

revoke all on public.app_users  from anon, authenticated;
revoke all on public.passkeys   from anon, authenticated;
revoke all on public.user_state from anon, authenticated;

grant select on public.app_users to authenticated;
grant select, insert, update on public.user_state to authenticated;

comment on table public.passkeys is 'パスキーの公開鍵。Edge Functions（service role）だけが読み書きする。ブラウザ向けの権限・ポリシーは意図して付けていない。';
