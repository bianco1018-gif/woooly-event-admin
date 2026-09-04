import base64
import hashlib
import hmac
import json
from datetime import date, datetime
from typing import Any

import requests
import streamlit as st

st.set_page_config(page_title="WOOOLY イベント管理", page_icon="📅", layout="centered")
API_ROOT = "https://api.github.com"


def require_secret(name: str) -> str:
    try:
        value = str(st.secrets[name]).strip()
    except Exception:
        st.error(f"Streamlit Secrets に `{name}` が設定されていません。")
        st.stop()
    if not value:
        st.error(f"Streamlit Secrets の `{name}` が空です。")
        st.stop()
    return value


def check_admin_password() -> None:
    expected = require_secret("ADMIN_PASSWORD")
    if st.session_state.get("authenticated"):
        return

    st.title("WOOOLY イベント管理")
    st.caption("管理者用ページ")
    entered = st.text_input("管理パスワード", type="password")
    if st.button("ログイン", type="primary", use_container_width=True):
        entered_hash = hashlib.sha256(entered.encode()).digest()
        expected_hash = hashlib.sha256(expected.encode()).digest()
        if hmac.compare_digest(entered_hash, expected_hash):
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("パスワードが違います。")
    st.stop()


def github_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {require_secret('GITHUB_TOKEN')}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def repo_config() -> tuple[str, str, str, str]:
    owner = require_secret("GITHUB_OWNER")
    repo = require_secret("GITHUB_REPO")
    branch = str(st.secrets.get("GITHUB_BRANCH", "main")).strip() or "main"
    path = str(st.secrets.get("EVENTS_PATH", "site/data/events.json")).strip()
    return owner, repo, branch, path


@st.cache_data(ttl=20, show_spinner=False)
def load_events_from_github(cache_key: str = "") -> tuple[list[dict[str, Any]], str]:
    owner, repo, branch, path = repo_config()
    response = requests.get(
        f"{API_ROOT}/repos/{owner}/{repo}/contents/{path}",
        headers=github_headers(),
        params={"ref": branch},
        timeout=20,
    )
    if response.status_code == 404:
        return [], ""
    response.raise_for_status()
    payload = response.json()
    raw = base64.b64decode(payload["content"]).decode("utf-8-sig")
    events = json.loads(raw) if raw.strip() else []
    if not isinstance(events, list):
        raise ValueError("events.json は配列形式である必要があります。")
    return events, payload.get("sha", "")


def save_events_to_github(events: list[dict[str, Any]], sha: str, message: str) -> None:
    owner, repo, branch, path = repo_config()
    content = json.dumps(events, ensure_ascii=False, indent=2) + "\n"
    body: dict[str, Any] = {
        "message": message,
        "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
        "branch": branch,
    }
    if sha:
        body["sha"] = sha

    response = requests.put(
        f"{API_ROOT}/repos/{owner}/{repo}/contents/{path}",
        headers=github_headers(),
        json=body,
        timeout=20,
    )
    if response.status_code not in (200, 201):
        raise RuntimeError(f"GitHubへの保存に失敗しました: {response.status_code} {response.text}")


def normalize_event(raw: dict[str, Any]) -> dict[str, str]:
    keys = ["id", "name", "date", "start", "end", "venue", "address", "note", "url"]
    return {key: str(raw.get(key, "")).strip() for key in keys}


def new_event_id(event_date: date, current_events: list[dict[str, Any]]) -> str:
    prefix = event_date.strftime("%Y%m%d")
    existing = {str(e.get("id", "")) for e in current_events if str(e.get("id", "")).startswith(prefix)}
    number = 1
    while f"{prefix}-{number:02d}" in existing:
        number += 1
    return f"{prefix}-{number:02d}"


def time_text(value: Any) -> str:
    if value is None:
        return ""
    if hasattr(value, "strftime"):
        return value.strftime("%H:%M")
    return str(value)


def event_label(event: dict[str, Any]) -> str:
    return f'{event.get("date", "")}｜{event.get("name", "(名称なし)")}｜{event.get("venue", "")}'


check_admin_password()
st.title("📅 WOOOLY イベント管理")
st.caption("イベントを入力して公開すると、GitHub経由でStarServerへ自動反映します。")

try:
    events, current_sha = load_events_from_github()
except Exception as exc:
    st.error(f"GitHubからイベント情報を取得できませんでした。\n\n{exc}")
    st.stop()

add_tab, edit_tab, delete_tab, list_tab = st.tabs(["➕ 追加", "✏️ 編集", "🗑️ 削除", "📋 一覧"])

with add_tab:
    st.subheader("イベントを追加")
    with st.form("add_event_form"):
        name = st.text_input("イベント名 *", placeholder="例：安城まちなかマルシェ")
        event_date = st.date_input("開催日 *", value=date.today())
        c1, c2 = st.columns(2)
        with c1:
            start = st.time_input("開始時刻", value=None)
        with c2:
            end = st.time_input("終了時刻", value=None)
        venue = st.text_input("会場 *", placeholder="例：アンフォーレ")
        address = st.text_input("住所", placeholder="例：愛知県安城市御幸本町504-1")
        note = st.text_area("補足", placeholder="雨天時の案内、販売内容など")
        url = st.text_input("イベントURL", placeholder="https://...")
        submitted = st.form_submit_button("GitHubへ保存して公開", type="primary", use_container_width=True)

    if submitted:
        if not name.strip() or not venue.strip():
            st.error("イベント名と会場は必須です。")
        else:
            new_event = {
                "id": new_event_id(event_date, events),
                "name": name.strip(),
                "date": event_date.isoformat(),
                "start": time_text(start),
                "end": time_text(end),
                "venue": venue.strip(),
                "address": address.strip(),
                "note": note.strip(),
                "url": url.strip(),
            }
            updated = [normalize_event(e) for e in events] + [new_event]
            updated.sort(key=lambda e: (e["date"], e["start"], e["id"]))
            try:
                save_events_to_github(updated, current_sha, f'イベント追加: {new_event["name"]} ({new_event["date"]})')
                load_events_from_github.clear()
                st.success("保存しました。GitHub ActionsからStarServerへ自動公開されます。")
            except Exception as exc:
                st.error(str(exc))

with edit_tab:
    st.subheader("イベントを編集")
    if not events:
        st.info("編集できるイベントがありません。")
    else:
        labels = [event_label(e) for e in events]
        selected_index = st.selectbox("編集するイベント", range(len(events)), format_func=lambda i: labels[i])
        selected = normalize_event(events[selected_index])
        try:
            initial_date = datetime.strptime(selected["date"], "%Y-%m-%d").date()
        except Exception:
            initial_date = date.today()

        with st.form("edit_event_form"):
            edit_name = st.text_input("イベント名 *", value=selected["name"])
            edit_date = st.date_input("開催日 *", value=initial_date)
            edit_start = st.text_input("開始時刻", value=selected["start"], placeholder="10:00")
            edit_end = st.text_input("終了時刻", value=selected["end"], placeholder="15:00")
            edit_venue = st.text_input("会場 *", value=selected["venue"])
            edit_address = st.text_input("住所", value=selected["address"])
            edit_note = st.text_area("補足", value=selected["note"])
            edit_url = st.text_input("イベントURL", value=selected["url"])
            edit_submit = st.form_submit_button("変更を保存して公開", type="primary", use_container_width=True)

        if edit_submit:
            if not edit_name.strip() or not edit_venue.strip():
                st.error("イベント名と会場は必須です。")
            else:
                replacement = {
                    "id": selected["id"] or new_event_id(edit_date, events),
                    "name": edit_name.strip(),
                    "date": edit_date.isoformat(),
                    "start": edit_start.strip(),
                    "end": edit_end.strip(),
                    "venue": edit_venue.strip(),
                    "address": edit_address.strip(),
                    "note": edit_note.strip(),
                    "url": edit_url.strip(),
                }
                updated = [normalize_event(e) for e in events]
                updated[selected_index] = replacement
                updated.sort(key=lambda e: (e["date"], e["start"], e["id"]))
                try:
                    save_events_to_github(updated, current_sha, f'イベント編集: {replacement["name"]} ({replacement["date"]})')
                    load_events_from_github.clear()
                    st.success("変更を保存しました。StarServerへ自動公開されます。")
                except Exception as exc:
                    st.error(str(exc))

with delete_tab:
    st.subheader("イベントを削除")
    if not events:
        st.info("削除できるイベントがありません。")
    else:
        delete_index = st.selectbox("削除するイベント", range(len(events)), format_func=lambda i: event_label(events[i]), key="delete_select")
        target = normalize_event(events[delete_index])
        st.warning(f'「{target["name"]}」({target["date"]}) を削除します。')
        confirm = st.checkbox("削除することを確認しました")
        if st.button("削除して公開", type="primary", disabled=not confirm, use_container_width=True):
            updated = [normalize_event(e) for i, e in enumerate(events) if i != delete_index]
            try:
                save_events_to_github(updated, current_sha, f'イベント削除: {target["name"]} ({target["date"]})')
                load_events_from_github.clear()
                st.success("削除しました。StarServerへ自動公開されます。")
            except Exception as exc:
                st.error(str(exc))

with list_tab:
    st.subheader("現在のイベント")
    if not events:
        st.info("イベントはまだ登録されていません。")
    else:
        rows = []
        for e in sorted([normalize_event(e) for e in events], key=lambda x: (x["date"], x["start"]), reverse=True):
            rows.append({
                "開催日": e["date"],
                "イベント名": e["name"],
                "時間": "〜".join([v for v in (e["start"], e["end"]) if v]),
                "会場": e["venue"],
                "住所": e["address"],
            })
        st.dataframe(rows, use_container_width=True, hide_index=True)

st.divider()
if st.button("GitHubから最新データを再読み込み", use_container_width=True):
    load_events_from_github.clear()
    st.rerun()
