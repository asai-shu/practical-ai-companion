// 入試 英単語 ナイン：ログイン（パスキー）＋2段階認証（認証アプリ・TOTP）＋学習記録の保存
//
// 安全のための決まりごと
// - ブラウザはデータベースに直接触れない。ここ（service role）だけが読み書きする
// - パスキーの検証は SimpleWebAuthn、6桁のコードは otpauth を使う（自分で暗号の処理を書かない）
// - 指紋・顔・PIN での本人確認（userVerification）を必須にする
// - トークン・復旧コードは、元に戻せない形（SHA-256）でしか保存しない
// - 2段階認証の秘密は AES-GCM で暗号化して保存する。かぎは Vault にある
// - 6桁のコード・復旧コードは、短い時間に何回も試せないようにする。同じ6桁のコードは2回使えない
// - 呼んでよいのは、下の ORIGINS のページからだけ
//
// 公開するドメインが決まったら、RP_ID と ORIGINS を書き換えて、もう一度デプロイする
// （RP_ID を変えると、それまでに作ったパスキーは使えなくなる）

import { createClient } from "npm:@supabase/supabase-js@2.49.1";
import {
  generateAuthenticationOptions,
  generateRegistrationOptions,
  verifyAuthenticationResponse,
  verifyRegistrationResponse,
} from "npm:@simplewebauthn/server@13.1.1";
import { isoBase64URL } from "npm:@simplewebauthn/server@13.1.1/helpers";
import * as OTPAuth from "npm:otpauth@9.3.6";
import QRCode from "npm:qrcode@1.5.4";

const RP_ID = "localhost";
const RP_NAME = "入試 英単語 ナイン";
const ORIGINS = ["http://localhost:8765"];
const SESSION_DAYS = 30;              // ログインしたままでいられる日数
const PENDING_MINUTES = 10;           // パスキーは通ったが、6桁のコードを待っている間
const MAX_STATE_BYTES = 512 * 1024;   // 学習記録の大きさの上限

const db = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!, {
  auth: { persistSession: false, autoRefreshToken: false },
});

class HttpError extends Error {
  constructor(public status: number, public code: string, message: string) { super(message); }
}
const fail = (status: number, code: string, message: string): never => { throw new HttpError(status, code, message); };

// ---------- 小さな道具 ----------
const enc = new TextEncoder();
const randomBytes = (n: number) => crypto.getRandomValues(new Uint8Array(n));
const b64url = (u: Uint8Array) => isoBase64URL.fromBuffer(u);
async function sha256hex(s: string) {
  const h = new Uint8Array(await crypto.subtle.digest("SHA-256", enc.encode(s)));
  return [...h].map((b) => b.toString(16).padStart(2, "0")).join("");
}
function cleanNickname(v: unknown) {
  if (typeof v !== "string") fail(400, "bad_nickname", "ニックネームを入れてください。");
  // 制御文字・幅のない文字・文字の向きを変える文字は取り除く（見た目をごまかす名前を防ぐ）
  const hidden = (n: number) => n < 32 || n === 127 || (n >= 0x200b && n <= 0x200f) || (n >= 0x2028 && n <= 0x202e) || (n >= 0x2066 && n <= 0x2069) || n === 0xfeff;
  const s = [...(v as string).normalize("NFC")].filter((c) => !hidden(c.codePointAt(0)!)).join("").trim();
  if (s.length < 1 || s.length > 20) fail(400, "bad_nickname", "ニックネームは1〜20文字にしてください。");
  return s;
}
// 復旧コード：まぎらわしい文字（0/O、1/I/L）を除いた32種類の文字で20文字（約100ビット）。4文字ごとに区切って見せる
const RC_ALPHA = "ABCDEFGHJKMNPQRSTUVWXYZ23456789";
function newRecoveryCode() {
  const b = randomBytes(20);
  const s = [...b].map((x) => RC_ALPHA[x % RC_ALPHA.length]).join("");
  return s.match(/.{4}/g)!.join("-");
}
const normRecovery = (v: string) => v.toUpperCase().replace(/[^A-Z0-9]/g, "");

// 2段階認証の秘密の暗号化（AES-GCM）。かぎは Vault から取り出す
let aesKey: CryptoKey | null = null;
async function getAesKey() {
  if (aesKey) return aesKey;
  const { data, error } = await db.rpc("nine_totp_key");
  if (error || !data) fail(500, "server", "サーバーの設定に問題があります。");
  aesKey = await crypto.subtle.importKey("raw", isoBase64URL.toBuffer(String(data), "base64"), "AES-GCM", false, ["encrypt", "decrypt"]);
  return aesKey;
}
async function seal(text: string) {
  const iv = randomBytes(12);
  const ct = new Uint8Array(await crypto.subtle.encrypt({ name: "AES-GCM", iv }, await getAesKey(), enc.encode(text)));
  return b64url(iv) + "." + b64url(ct);
}
async function unseal(sealed: string) {
  const [iv, ct] = sealed.split(".");
  const pt = await crypto.subtle.decrypt({ name: "AES-GCM", iv: isoBase64URL.toBuffer(iv) }, await getAesKey(), isoBase64URL.toBuffer(ct));
  return new TextDecoder().decode(pt);
}
const totpOf = (secretB32: string, label: string) =>
  new OTPAuth.TOTP({ issuer: RP_NAME, label, algorithm: "SHA1", digits: 6, period: 30, secret: OTPAuth.Secret.fromBase32(secretB32) });

// 6桁のコードを確かめる。前後30秒のずれまで許す。同じコード（同じ時間の区切り）は2回使えない
async function checkTotp(user: Record<string, unknown>, code: unknown, field: "totp_secret_enc" | "totp_pending_enc") {
  if (typeof code !== "string" || !/^[0-9]{6}$/.test(code.trim())) fail(400, "bad_code", "6桁の数字を入れてください。");
  const sealed = user[field] as string | null;
  if (!sealed) fail(400, "no_totp", "認証アプリが設定されていません。");
  const totp = totpOf(await unseal(sealed!), String(user.nickname));
  const delta = totp.validate({ token: (code as string).trim(), window: 1 });
  if (delta === null) return false;
  const step = Math.floor(Date.now() / 1000 / 30) + delta;
  // 使い回し防止：記録より新しい区切りのときだけ書き換える（同時に2回送られても、通るのは1回だけ）
  const { data: upd } = await db.from("app_users").update({ totp_last_step: step }).eq("id", user.id).lt("totp_last_step", step).select("id");
  return !!upd && upd.length === 1;
}

// 試行回数の制限：bucket ごとに、windowSec 秒の間に max 回まで
async function limit(bucket: string, max: number, windowSec: number) {
  const since = new Date(Date.now() - windowSec * 1000).toISOString();
  const { count } = await db.from("auth_attempts").select("id", { count: "exact", head: true }).eq("bucket", bucket).gte("at", since);
  if ((count ?? 0) >= max) fail(429, "too_many", "試した回数が多すぎます。しばらく待ってから、もう一度試してください。");
  await db.from("auth_attempts").insert({ bucket });
}

// ---------- ログイン中の記録 ----------
async function newSession(userId: string, full: boolean) {
  const token = b64url(randomBytes(32));
  const ms = full ? SESSION_DAYS * 864e5 : PENDING_MINUTES * 6e4;
  const { error } = await db.from("sessions").insert({
    token_hash: await sha256hex(token), user_id: userId, full_access: full, expires_at: new Date(Date.now() + ms).toISOString(),
  });
  if (error) fail(500, "server", "ログインの記録に失敗しました。");
  return token;
}
async function getSession(req: Request, needFull = true) {
  const token = req.headers.get("x-session") || "";
  if (!/^[A-Za-z0-9_-]{40,60}$/.test(token)) fail(401, "no_session", "ログインしてください。");
  const hash = await sha256hex(token);
  const { data: s } = await db.from("sessions").select("*").eq("token_hash", hash).maybeSingle();
  if (!s || new Date(s.expires_at) < new Date()) fail(401, "no_session", "ログインの期限が切れました。もう一度ログインしてください。");
  if (needFull && !s!.full_access) fail(403, "need_totp", "認証アプリの6桁のコードを入れてください。");
  const { data: user } = await db.from("app_users").select("*").eq("id", s!.user_id).maybeSingle();
  if (!user) fail(401, "no_session", "ログインしてください。");
  await db.from("sessions").update({ last_seen_at: new Date().toISOString() }).eq("token_hash", hash);
  return { session: s!, user: user!, hash };
}

// ---------- WebAuthn の確認用の値（1回きり・5分） ----------
async function saveChallenge(kind: string, challenge: string, userId: string | null, data: Record<string, unknown> = {}) {
  const { data: row, error } = await db.from("webauthn_challenges").insert({ kind, challenge, user_id: userId, data }).select("id").single();
  if (error) fail(500, "server", "準備に失敗しました。");
  return row!.id as string;
}
async function takeChallenge(id: unknown, kind: string) {
  if (typeof id !== "string" || !/^[0-9a-f-]{36}$/.test(id)) fail(400, "bad_challenge", "もう一度最初からやり直してください。");
  const { data: row } = await db.from("webauthn_challenges").delete().eq("id", id).eq("kind", kind).select("*").maybeSingle();
  if (!row || new Date(row.expires_at) < new Date()) fail(400, "bad_challenge", "時間切れです。もう一度最初からやり直してください。");
  return row!;
}

const regOptions = (nickname: string, userId: string, exclude: { id: string; transports?: string[] }[] = []) =>
  generateRegistrationOptions({
    rpName: RP_NAME, rpID: RP_ID, userName: nickname, userDisplayName: nickname,
    userID: enc.encode(userId), attestationType: "none",
    excludeCredentials: exclude.map((c) => ({ id: c.id, transports: c.transports as never })),
    authenticatorSelection: { residentKey: "required", userVerification: "required" },
  });
async function verifyReg(response: unknown, expectedChallenge: string) {
  let v;
  try {
    v = await verifyRegistrationResponse({
      response: response as never, expectedChallenge, expectedOrigin: ORIGINS, expectedRPID: RP_ID, requireUserVerification: true,
    });
  } catch (_) { fail(400, "passkey_failed", "パスキーを確かめられませんでした。"); }
  if (!v!.verified || !v!.registrationInfo) fail(400, "passkey_failed", "パスキーを確かめられませんでした。");
  return v!.registrationInfo!.credential;
}
async function storePasskey(userId: string, cred: { id: string; publicKey: Uint8Array; counter: number; transports?: string[] }) {
  const { error } = await db.from("passkeys").insert({
    credential_id: cred.id, user_id: userId, public_key: b64url(cred.publicKey), counter: cred.counter, transports: cred.transports ?? null,
  });
  if (error) fail(409, "passkey_exists", "このパスキーは、すでに登録されています。");
}

// ---------- それぞれの操作 ----------
type Body = Record<string, unknown>;
const actions: Record<string, (req: Request, b: Body, ip: string) => Promise<unknown>> = {
  // 新しく登録：① ニックネームを受け取り、パスキーを作るための値を返す
  async reg_options(_req, b, ip) {
    await limit("ip:" + ip + ":reg", 10, 3600);
    const nickname = cleanNickname(b.nickname);
    const userId = crypto.randomUUID();
    const options = await regOptions(nickname, userId);
    const challengeId = await saveChallenge("register", options.challenge, null, { user_id: userId, nickname });
    return { challengeId, options };
  },
  // 新しく登録：② 作ったパスキーを確かめて、利用者を作る。復旧コードはここで1回だけ返す
  async reg_verify(_req, b) {
    const ch = await takeChallenge(b.challengeId, "register");
    const cred = await verifyReg(b.response, ch.challenge);
    const userId = String(ch.data.user_id), nickname = String(ch.data.nickname);
    const recoveryCode = newRecoveryCode();
    const { error } = await db.from("app_users").insert({ id: userId, nickname, recovery_code_hash: await sha256hex(normRecovery(recoveryCode)) });
    if (error) fail(500, "server", "登録に失敗しました。");
    await storePasskey(userId, cred);
    return { token: await newSession(userId, true), recoveryCode, nickname };
  },
  // ログイン：① パスキーを使うための値（どのアカウントかは端末が選ぶ）
  async login_options(_req, _b, ip) {
    await limit("ip:" + ip + ":login", 60, 600);
    const options = await generateAuthenticationOptions({ rpID: RP_ID, userVerification: "required" });
    return { challengeId: await saveChallenge("login", options.challenge, null), options };
  },
  // ログイン：② パスキーを確かめる。2段階認証を設定している人は、まだ「途中」のログイン
  async login_verify(_req, b, ip) {
    await limit("ip:" + ip + ":login", 60, 600);
    const ch = await takeChallenge(b.challengeId, "login");
    const resp = b.response as { id?: string };
    if (!resp || typeof resp.id !== "string") fail(400, "passkey_failed", "パスキーを確かめられませんでした。");
    const { data: pk } = await db.from("passkeys").select("*").eq("credential_id", resp.id).maybeSingle();
    if (!pk) fail(401, "passkey_unknown", "このパスキーは登録されていません。");
    let v;
    try {
      v = await verifyAuthenticationResponse({
        response: b.response as never, expectedChallenge: ch.challenge, expectedOrigin: ORIGINS, expectedRPID: RP_ID, requireUserVerification: true,
        credential: { id: pk!.credential_id, publicKey: isoBase64URL.toBuffer(pk!.public_key, "base64url"), counter: Number(pk!.counter), transports: pk!.transports ?? undefined },
      });
    } catch (_) { fail(401, "passkey_failed", "パスキーを確かめられませんでした。"); }
    if (!v!.verified) fail(401, "passkey_failed", "パスキーを確かめられませんでした。");
    await db.from("passkeys").update({ counter: v!.authenticationInfo.newCounter, last_used_at: new Date().toISOString() }).eq("credential_id", pk!.credential_id);
    const { data: user } = await db.from("app_users").select("id, nickname, totp_enabled").eq("id", pk!.user_id).single();
    return { token: await newSession(user!.id, !user!.totp_enabled), needTotp: !!user!.totp_enabled, nickname: user!.nickname };
  },
  // ログイン：③ 6桁のコード（2段階認証を設定している人だけ）
  async login_totp(req, b) {
    const { session, user, hash } = await getSession(req, false);
    if (session.full_access) return { ok: true };
    await limit("user:" + user.id + ":totp", 5, 600);
    if (!(await checkTotp(user, b.code, "totp_secret_enc"))) fail(401, "bad_code", "コードが違います。認証アプリの今の6桁を入れてください。");
    await db.from("sessions").delete().eq("token_hash", hash);       // 途中の記録は捨てて、新しく発行する
    return { token: await newSession(user.id, true) };
  },
  // 復旧：パスキーが使えないとき。復旧コード（＋2段階認証を設定している人は6桁のコード）
  async recover(_req, b, ip) {
    await limit("ip:" + ip + ":recover", 5, 3600);
    if (typeof b.recoveryCode !== "string") fail(400, "bad_recovery", "復旧コードを入れてください。");
    const { data: user } = await db.from("app_users").select("*").eq("recovery_code_hash", await sha256hex(normRecovery(b.recoveryCode as string))).maybeSingle();
    if (!user) fail(401, "bad_recovery", "復旧コードが違います。");
    if (user!.totp_enabled) {
      await limit("user:" + user!.id + ":totp", 5, 600);
      if (!(await checkTotp(user!, b.code, "totp_secret_enc"))) fail(401, "bad_code", "認証アプリの6桁のコードが違います。");
    }
    // 復旧コードは使い捨て。新しいものに取り替え、ほかの端末のログインはすべて終わらせる
    const recoveryCode = newRecoveryCode();
    await db.from("app_users").update({ recovery_code_hash: await sha256hex(normRecovery(recoveryCode)) }).eq("id", user!.id);
    await db.from("sessions").delete().eq("user_id", user!.id);
    return { token: await newSession(user!.id, true), recoveryCode, nickname: user!.nickname };
  },
  // 自分の情報
  async me(req) {
    const { user } = await getSession(req);
    const { data: pks } = await db.from("passkeys").select("created_at, last_used_at").eq("user_id", user.id).order("created_at");
    return { nickname: user.nickname, totpEnabled: user.totp_enabled, passkeys: pks ?? [] };
  },
  // 別の端末のパスキーを足す
  async add_options(req) {
    const { user } = await getSession(req);
    const { data: pks } = await db.from("passkeys").select("credential_id, transports").eq("user_id", user.id);
    const options = await regOptions(user.nickname, user.id, (pks ?? []).map((p) => ({ id: p.credential_id, transports: p.transports ?? undefined })));
    return { challengeId: await saveChallenge("add", options.challenge, user.id), options };
  },
  async add_verify(req, b) {
    const { user } = await getSession(req);
    const ch = await takeChallenge(b.challengeId, "add");
    if (ch.user_id !== user.id) fail(400, "bad_challenge", "もう一度最初からやり直してください。");
    await storePasskey(user.id, await verifyReg(b.response, ch.challenge));
    return { ok: true };
  },
  // 2段階認証：① 新しい秘密を作る（まだ有効にはしない）。QRコードを返す
  async totp_setup(req) {
    const { user } = await getSession(req);
    if (user.totp_enabled) fail(400, "already", "認証アプリはすでに設定されています。");
    const secret = new OTPAuth.Secret({ size: 20 });
    await db.from("app_users").update({ totp_pending_enc: await seal(secret.base32) }).eq("id", user.id);
    const uri = totpOf(secret.base32, user.nickname).toString();
    const qrSvg = await QRCode.toString(uri, { type: "svg", errorCorrectionLevel: "M", margin: 2 });
    return { secret: secret.base32.match(/.{1,4}/g)!.join(" "), uri, qrSvg };
  },
  // 2段階認証：② 認証アプリの6桁を確かめてから有効にする（読み取りまちがいで締め出されないように）
  async totp_enable(req, b) {
    const { user } = await getSession(req);
    await limit("user:" + user.id + ":totp", 5, 600);
    if (!(await checkTotp(user, b.code, "totp_pending_enc"))) fail(401, "bad_code", "コードが違います。認証アプリに出ている今の6桁を入れてください。");
    await db.from("app_users").update({ totp_secret_enc: user.totp_pending_enc, totp_pending_enc: null, totp_enabled: true }).eq("id", user.id);
    return { ok: true };
  },
  // 2段階認証をやめる（今の6桁のコードが必要）
  async totp_disable(req, b) {
    const { user } = await getSession(req);
    await limit("user:" + user.id + ":totp", 5, 600);
    if (!(await checkTotp(user, b.code, "totp_secret_enc"))) fail(401, "bad_code", "コードが違います。");
    await db.from("app_users").update({ totp_secret_enc: null, totp_enabled: false, totp_last_step: 0 }).eq("id", user.id);
    return { ok: true };
  },
  // 復旧コードを作り直す（2段階認証を設定している人は6桁のコードが必要）
  async recovery_new(req, b) {
    const { user } = await getSession(req);
    if (user.totp_enabled) {
      await limit("user:" + user.id + ":totp", 5, 600);
      if (!(await checkTotp(user, b.code, "totp_secret_enc"))) fail(401, "bad_code", "コードが違います。");
    }
    const recoveryCode = newRecoveryCode();
    await db.from("app_users").update({ recovery_code_hash: await sha256hex(normRecovery(recoveryCode)) }).eq("id", user.id);
    return { recoveryCode };
  },
  // 学習記録
  async state_get(req) {
    const { user } = await getSession(req);
    const { data } = await db.from("user_state").select("state, updated_at").eq("user_id", user.id).maybeSingle();
    return { state: data?.state ?? null, updatedAt: data?.updated_at ?? null };
  },
  async state_put(req, b) {
    const { user } = await getSession(req);
    if (!b.state || typeof b.state !== "object" || Array.isArray(b.state)) fail(400, "bad_state", "記録の形が正しくありません。");
    if (enc.encode(JSON.stringify(b.state)).length > MAX_STATE_BYTES) fail(413, "too_big", "記録が大きすぎます。");
    const { error } = await db.from("user_state").upsert({ user_id: user.id, state: b.state, updated_at: new Date().toISOString() });
    if (error) fail(500, "server", "記録の保存に失敗しました。");
    return { ok: true };
  },
  async logout(req) {
    const token = req.headers.get("x-session") || "";
    if (token) await db.from("sessions").delete().eq("token_hash", await sha256hex(token));
    return { ok: true };
  },
  async logout_all(req) {
    const { user } = await getSession(req);
    await db.from("sessions").delete().eq("user_id", user.id);
    return { ok: true };
  },
  // アカウントを消す（学習記録・パスキー・ログインの記録も一緒に消える）
  async delete_account(req, b) {
    const { user } = await getSession(req);
    if (user.totp_enabled) {
      await limit("user:" + user.id + ":totp", 5, 600);
      if (!(await checkTotp(user, b.code, "totp_secret_enc"))) fail(401, "bad_code", "コードが違います。");
    }
    if (b.confirm !== user.nickname) fail(400, "confirm", "確認のため、ニックネームを正しく入れてください。");
    await db.from("app_users").delete().eq("id", user.id);
    return { ok: true };
  },
};

// ---------- 入り口 ----------
function cors(origin: string | null) {
  const h: Record<string, string> = {
    "Content-Type": "application/json; charset=utf-8",
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
    "Vary": "Origin",
  };
  if (origin && ORIGINS.includes(origin)) {
    h["Access-Control-Allow-Origin"] = origin;
    h["Access-Control-Allow-Methods"] = "POST, OPTIONS";
    h["Access-Control-Allow-Headers"] = "content-type, x-session";
    h["Access-Control-Max-Age"] = "600";
  }
  return h;
}

Deno.serve(async (req) => {
  const origin = req.headers.get("origin");
  const headers = cors(origin);
  if (req.method === "OPTIONS") return new Response(null, { status: origin && ORIGINS.includes(origin) ? 204 : 403, headers });
  try {
    if (req.method !== "POST") fail(405, "method", "使えない呼び方です。");
    if (!origin || !ORIGINS.includes(origin)) fail(403, "origin", "このページからは使えません。");
    const raw = await req.text();
    if (raw.length > MAX_STATE_BYTES + 4096) fail(413, "too_big", "送られた内容が大きすぎます。");
    let body: Body;
    try { body = JSON.parse(raw); } catch (_) { body = {}; }
    const fn = typeof body.action === "string" ? actions[body.action] : undefined;
    if (!fn) fail(400, "action", "使えない操作です。");
    const ip = (req.headers.get("x-forwarded-for") || "").split(",")[0].trim() || "unknown";
    // ときどき、期限切れの記録を片づける
    if (Math.random() < 0.05) {
      const now = new Date().toISOString();
      await db.from("webauthn_challenges").delete().lt("expires_at", now);
      await db.from("sessions").delete().lt("expires_at", now);
      await db.from("auth_attempts").delete().lt("at", new Date(Date.now() - 864e5).toISOString());
    }
    const result = await fn!(req, body, ip);
    return new Response(JSON.stringify(result), { status: 200, headers });
  } catch (e) {
    if (e instanceof HttpError) return new Response(JSON.stringify({ error: e.code, message: e.message }), { status: e.status, headers });
    console.error(e);
    return new Response(JSON.stringify({ error: "server", message: "サーバーでエラーが起きました。" }), { status: 500, headers });
  }
});
