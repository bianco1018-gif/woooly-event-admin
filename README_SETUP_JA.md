# WOOOLY イベント管理システム

## 仕組み

Streamlit管理画面でイベントを追加・編集・削除
→ GitHubの `site/data/events.json` を更新
→ GitHub ActionsがStarServerへ `events.json` と `event.js` を自動アップロード
→ `woooly_calender.html` がJSONを読み込んで表示

現在の `woooly_calender.html` はすでに `js/event.js` を読み込んでいるため、基本的にHTML変更は不要です。

## 1. GitHubリポジトリを作る

例: `woooly-event-admin`

このZIPの中身をリポジトリのルートへアップロードしてください。

## 2. GitHub Fine-grained Personal Access Token

対象リポジトリだけにアクセスできる Fine-grained token を作ります。
必要権限は Repository permissions → Contents → Read and write です。

## 3. Streamlit Community Cloud

GitHubを接続し、このリポジトリの `streamlit_app.py` をデプロイします。

## 4. Streamlit Secrets

アプリ設定のSecretsへ以下を登録します。

```toml
ADMIN_PASSWORD = "管理画面用の強いパスワード"
GITHUB_TOKEN = "github_pat_xxxxxxxxx"
GITHUB_OWNER = "GitHubユーザー名"
GITHUB_REPO = "woooly-event-admin"
GITHUB_BRANCH = "main"
EVENTS_PATH = "site/data/events.json"
```

## 5. GitHub Actions Secrets

GitHub → Settings → Secrets and variables → Actions に次の3つを登録します。

- `FTP_BASE_URL`
- `FTP_USERNAME`
- `FTP_PASSWORD`

`FTP_BASE_URL` は、StarServerで `index.html` と `woooly_calender.html` が置かれている公開フォルダまでのFTP URLです。

例:

```text
ftp://FTPホスト名/公開フォルダ
```

FTPSが使える場合は `ftps://...` にします。

## 6. 初回公開

GitHub → Actions → `Deploy WOOOLY event data` → Run workflow を実行します。
成功するとStarServerに次ができます。

```text
data/events.json
js/event.js
```

このWorkflowはサイト全体を同期せず、上記2ファイルだけをアップロードします。既存HTMLや画像を削除しません。

## 7. イベント追加

Streamlit管理画面で「追加」タブを開き、イベント名・日付・時間・会場などを入力して「GitHubへ保存して公開」を押します。

GitHubへの保存後、ActionsがStarServerへ自動転送します。

## events.json例

```json
[
  {
    "id": "20260920-01",
    "name": "安城まちなかマルシェ",
    "date": "2026-09-20",
    "start": "10:00",
    "end": "15:00",
    "venue": "アンフォーレ",
    "address": "愛知県安城市御幸本町504-1",
    "note": "ハンドメイド作品を販売します。",
    "url": "https://example.com/"
  }
]
```

## 注意

- `.streamlit/secrets.toml` はGitHubへアップロードしないでください。
- GitHub TokenやFTPパスワードをPython/YAMLへ直接書かないでください。
- 最初はActionsを手動実行し、FTP先が正しいことを確認してください。
