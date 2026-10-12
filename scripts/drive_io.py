#!/usr/bin/env python3
"""Google Drive OAuth helper for GitHub Actions.

Requires refresh-token OAuth credentials with Drive read access for downloads and
Drive write access for uploads. Never prints tokens, signed URLs, or authorization headers.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://www.googleapis.com/drive/v3"
UPLOAD = "https://www.googleapis.com/upload/drive/v3/files"


def request_json(url: str, token: str, method: str = "GET", body: dict | None = None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": "Bearer " + token,
        "Content-Type": "application/json; charset=utf-8",
    })
    with urllib.request.urlopen(req, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def access_token() -> str:
    required = ["GOOGLE_DRIVE_CLIENT_ID", "GOOGLE_DRIVE_CLIENT_SECRET", "GOOGLE_DRIVE_REFRESH_TOKEN"]
    missing = [key for key in required if not os.environ.get(key)]
    if missing:
        raise RuntimeError("Missing repository secrets: " + ", ".join(missing))
    payload = urllib.parse.urlencode({
        "client_id": os.environ["GOOGLE_DRIVE_CLIENT_ID"],
        "client_secret": os.environ["GOOGLE_DRIVE_CLIENT_SECRET"],
        "refresh_token": os.environ["GOOGLE_DRIVE_REFRESH_TOKEN"],
        "grant_type": "refresh_token",
    }).encode()
    req = urllib.request.Request("https://oauth2.googleapis.com/token", data=payload,
                                 headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            token_data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:500]
        raise RuntimeError(f"Google OAuth refresh failed ({exc.code}): {detail}") from exc
    token = token_data.get("access_token")
    if not token:
        raise RuntimeError("Google OAuth refresh returned no access token.")
    return token


def find_reference(token: str) -> dict:
    folder_id = os.environ.get("GOOGLE_DRIVE_FOLDER_ID")
    specific_id = os.environ.get("GOOGLE_DRIVE_REFERENCE_FILE_ID")
    if specific_id:
        return request_json(f"{API}/files/{urllib.parse.quote(specific_id)}?fields=id,name,mimeType,size,md5Checksum,parents", token)
    if not folder_id:
        raise RuntimeError("Set GOOGLE_DRIVE_FOLDER_ID to the Drive folder named فيديوهات.")
    name = os.environ.get("GOOGLE_DRIVE_REFERENCE_NAME", "Red vs Black 2023 (by MicroMist)_720p.mp4")
    escaped_name = name.replace("\\", "\\\\").replace("'", "\\'")
    q = f"'{folder_id}' in parents and name = '{escaped_name}' and trashed = false"
    query = urllib.parse.urlencode({"q": q, "pageSize": "100", "fields": "files(id,name,mimeType,size,md5Checksum,parents)"})
    result = request_json(f"{API}/files?{query}", token)
    files = result.get("files", [])
    if not files:
        raise RuntimeError("The reference video was not found in the configured Drive folder.")
    video_files = [f for f in files if f.get("mimeType", "").startswith("video/")]
    if not video_files:
        raise RuntimeError("The matching Drive item is not a video.")
    return sorted(video_files, key=lambda f: (f.get("name", ""), f.get("id", "")))[0]


def download_reference(args):
    token = access_token()
    metadata = find_reference(token)
    if not metadata.get("mimeType", "").startswith("video/"):
        raise RuntimeError("The reference file is not a video binary.")
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    url = f"{API}/files/{urllib.parse.quote(metadata['id'])}?alt=media"
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + token})
    try:
        with urllib.request.urlopen(req, timeout=90) as response, path.open("wb") as out:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                out.write(chunk)
    except Exception:
        path.unlink(missing_ok=True)
        raise
    if path.stat().st_size < 100_000:
        path.unlink(missing_ok=True)
        raise RuntimeError("The downloaded reference file is unexpectedly small.")
    expected_size = int(metadata.get("size") or 0)
    if expected_size and path.stat().st_size != expected_size:
        path.unlink(missing_ok=True)
        raise RuntimeError("Downloaded file size does not match Drive metadata.")
    if args.metadata_output:
        Path(args.metadata_output).write_text(json.dumps({
            "id": metadata.get("id"), "name": metadata.get("name"),
            "mimeType": metadata.get("mimeType"), "size": path.stat().st_size,
            "source_frames_or_audio_copied_to_output": False,
        }, indent=2), encoding="utf-8")
    print(f"Downloaded reference metadata verified: {metadata.get('name')} ({path.stat().st_size} bytes)")


def resumable_upload(token: str, path: Path, parent_id: str, name: str) -> dict:
    metadata = {"name": name, "mimeType": "video/mp4", "parents": [parent_id]}
    init = urllib.request.Request(
        UPLOAD + "?" + urllib.parse.urlencode({"uploadType": "resumable", "fields": "id,name,mimeType,size,webViewLink,parents"}),
        data=json.dumps(metadata).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": "Bearer " + token,
            "Content-Type": "application/json; charset=UTF-8",
            "X-Upload-Content-Type": "video/mp4",
            "X-Upload-Content-Length": str(path.stat().st_size),
        },
    )
    with urllib.request.urlopen(init, timeout=60) as resp:
        session_url = resp.headers.get("Location")
    if not session_url:
        raise RuntimeError("Google Drive did not provide a resumable upload URL.")
    total = path.stat().st_size
    chunk_size = 8 * 1024 * 1024
    offset = 0
    with path.open("rb") as src:
        while offset < total:
            data = src.read(min(chunk_size, total - offset))
            end = offset + len(data) - 1
            req = urllib.request.Request(session_url, data=data, method="PUT", headers={
                "Content-Type": "video/mp4",
                "Content-Length": str(len(data)),
                "Content-Range": f"bytes {offset}-{end}/{total}",
            })
            try:
                with urllib.request.urlopen(req, timeout=120) as resp:
                    response_text = resp.read().decode("utf-8", "replace")
                    status = resp.status
            except urllib.error.HTTPError as exc:
                if exc.code == 308:
                    offset = end + 1
                    continue
                detail = exc.read().decode("utf-8", "replace")[:500]
                raise RuntimeError(f"Drive upload failed ({exc.code}): {detail}") from exc
            offset = end + 1
            if offset >= total:
                try:
                    return json.loads(response_text)
                except Exception as exc:
                    raise RuntimeError("Drive upload returned invalid final metadata.") from exc
            if status not in (200, 201, 308):
                raise RuntimeError(f"Unexpected Drive upload status: {status}")
    raise RuntimeError("Drive upload ended without final file metadata.")


def upload_final(args):
    token = access_token()
    folder = os.environ.get("GOOGLE_DRIVE_OUTPUT_FOLDER_ID") or os.environ.get("GOOGLE_DRIVE_FOLDER_ID")
    if not folder:
        raise RuntimeError("Set GOOGLE_DRIVE_OUTPUT_FOLDER_ID or GOOGLE_DRIVE_FOLDER_ID.")
    path = Path(args.input)
    if not path.is_file() or path.stat().st_size < 1_000_000:
        raise RuntimeError("Final MP4 is missing or too small to upload.")
    name = args.name or path.name
    metadata = resumable_upload(token, path, folder, name)
    print(json.dumps({
        "id": metadata.get("id"), "name": metadata.get("name"),
        "mimeType": metadata.get("mimeType"), "size": metadata.get("size"),
        "webViewLink": metadata.get("webViewLink"), "parents": metadata.get("parents"),
    }, indent=2))


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    dl = sub.add_parser("download-reference")
    dl.add_argument("--output", required=True)
    dl.add_argument("--metadata-output")
    up = sub.add_parser("upload-final")
    up.add_argument("--input", required=True)
    up.add_argument("--name")
    args = parser.parse_args()
    if args.command == "download-reference":
        download_reference(args)
    else:
        upload_final(args)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"DRIVE_PIPELINE_ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
