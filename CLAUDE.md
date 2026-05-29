# CLAUDE.md — mlModelCore (Cloud Run YOLOv8 物体検出)

## このファイルの責任範囲

Cloud Run で動作する Python 物体検出サーバ (`main.py`, `Dockerfile`)、および周辺の GCP 設定 (Eventarc / Artifact Registry / Secret Manager) に関する事項を扱います。
横断的なルール (本番直結 / Git ワークフロー / CLAUDE.md 更新ルール / アーキテクチャ全体) は `../CLAUDE.md` を (Git 手順の詳細は `../docs/GIT-WORKFLOW.md`)、フロントエンド・Functions の詳細は `../takumi-craft-works/CLAUDE.md` を参照してください。

---

## ランタイム情報

| 対象 | 内容 |
|---|---|
| Python | コンテナ内は **3.10** (`Dockerfile`)。**ローカル PC に Python を入れる必要はない** |
| Docker | コンテナビルドは Cloud Build がクラウド側で実行するため、ローカル Docker は不要 |
| `gcloud` CLI | Cloud Run / Eventarc / Secret Manager 操作用。この PC から実行可能 |

### `mlModelCore` のローカル単体検証
`main.py` を手元で動かしたい・`Dockerfile` をローカルビルドしたい場合は、**GCP 上の AI Notebook インスタンス**で作業する運用です。この PC からは Docker を使った検証は想定していません。

---

## 主要ファイル

| パス | 役割 |
|---|---|
| `Dockerfile` | Python 3.10 + ultralytics(YOLOv8) + システムライブラリ |
| `main.py` | Flask アプリ。Eventarc から POST を受け取って YOLOv8 推論し、結果を Storage に保存 |
| `requirements.txt` | Python 依存 |
| `yolov8n.pt` | YOLO モデルウェイト (Docker build 時に再 DL される) |
| `gcloudCommand.txt` | Cloud Run / Artifact Registry / Eventarc / Secret Manager のセットアップ手順 |
| `detectionGateway.ipynb` / `testYolo.ipynb` / `dockerTest.py` | 開発・検証用 (AI Notebook 上で使用) |

---

## 改名禁止リスト

以下の識別子は他のサービス・コードと結合しているため、**変更すると即座に動作が壊れます**。

| 識別子 | 種類 | 結合先 |
|---|---|---|
| `origineImages` | Storage プレフィックス (入力) | `main.py` + `takumi-craft-works/functions/index.js` |
| `detectedImages` | Storage プレフィックス (出力) | `main.py` + `takumi-craft-works/functions/index.js` |
| `FIREBASE_KEY` | Cloud Run 環境変数名 | `main.py` の `os.environ["FIREBASE_KEY"]` / `gcloudCommand.txt` 手順6 の `--update-secrets` |

Storage プレフィックスは `takumi-craft-works/functions/index.js` でも使用されているため、変更する場合は両リポジトリ同時改修が必要です。

---

## ⚠️ セキュリティ既知事項

このリポジトリは Public のため、**現状のセキュリティ課題・攻撃面・対策案は CLAUDE.md には記載しません**。すべて Git 管理外の `../SECURITY-NOTES.md` に集約しています。

- Claude は改修着手前に `../SECURITY-NOTES.md` を読み、書かれた「Claude が改修する際の最低ライン」を必ず遵守
- セキュリティ課題を新たに発見した場合、CLAUDE.md ではなく **`../SECURITY-NOTES.md` に追記** (このファイルは Public リポジトリにコミットされるため攻撃情報を書かない)
- 課題が解消した時も `../SECURITY-NOTES.md` の「🟢 解消済み」セクションに移動

---

## デプロイコマンド

すべて**ユーザー承認後**に実行します (最重要ルール参照)。Cloud Build がクラウド側でビルドするため、**ローカル Docker 不要**。

```bash
# 1. 新イメージをビルドして Artifact Registry に push
gcloud builds submit \
  --tag asia-northeast1-docker.pkg.dev/myproducts-488109/<repo>/<image>

# 2. ビルド済みイメージで Cloud Run サービスを更新
gcloud run deploy <service> \
  --image asia-northeast1-docker.pkg.dev/myproducts-488109/<repo>/<image> \
  --region asia-northeast1 \
  --platform managed
# (詳細パラメータは gcloudCommand.txt 手順6 参照)
```

初回構築時の Artifact Registry / Service Account / Secret Manager / Eventarc セットアップ手順は `gcloudCommand.txt` に記載。

---

## ログ・状態確認

```bash
# Cloud Run のログ (直近100件)
gcloud run services logs read <service-name> \
  --region asia-northeast1 --limit 100

# Cloud Run の現状 (URL / 稼働リビジョン)
gcloud run services describe <service-name> \
  --platform managed --region asia-northeast1

# 稼働中・過去のリビジョン一覧
gcloud run revisions list \
  --service=<service-name> --region=asia-northeast1

# Eventarc トリガー一覧
gcloud eventarc triggers list --location=asia-northeast1
```

Storage オブジェクトの確認は **GCP コンソール**から行うのが速い。

---

## ロールバック手順

### Cloud Run サービス
- 過去リビジョン一覧を取得 → トラフィックを過去リビジョンへ切り戻し:
  ```bash
  gcloud run revisions list --service=<service> --region=asia-northeast1
  gcloud run services update-traffic <service> \
    --region=asia-northeast1 \
    --to-revisions <REVISION_NAME>=100
  ```
- リビジョンは Cloud Run 側で保持されているため、過去バージョンへの切り戻しは**新規ビルド不要で即時可能**

### Storage データ
- **ロールバック不可**。破壊的操作の前に必ずバックアップを取る:
  ```bash
  gsutil -m cp -r gs://<bucket>/<prefix> gs://<backup-bucket>/
  ```

---

## Cloud Run 改修時の注意

- `main.py` の入力/出力フォルダ名 (`origineImages` / `detectedImages`) は `takumi-craft-works/functions/index.js` と完全一致させる (改名禁止リスト参照)
- イメージ再ビルドは `gcloud builds submit` で時間がかかる (YOLO モデル含む)
- Eventarc トリガーは Storage バケット単位。バケット名を変更する場合は `gcloudCommand.txt` の手順8 を参照して再作成
- Cloud Run の memory / timeout / max-instances などのリソース設定は `gcloud run deploy` のフラグで指定 (`gcloudCommand.txt` 手順6 参照)

→ 改修後は `../CLAUDE.md` の **Git ワークフロー（要点）** と詳細手順 `../docs/GIT-WORKFLOW.md` に従って進めます: commit → build (`gcloud builds submit`) → デプロイ (`gcloud run deploy`) → push → merge。
