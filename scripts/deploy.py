#!/usr/bin/env python3
"""보고서 HTML -> AES-GCM 암호화 -> root/<key>.json 생성 + manifest.json 갱신.

index.html의 deriveKey()/decryptPayload()와 정확히 대칭:
  PBKDF2WithHmacSHA256(진입코드, salt, 100000회) -> AES-256-GCM 키
  AES-GCM(랜덤 12바이트 iv)로 평문 HTML 암호화 (태그는 ciphertext 끝에 자동 포함)

사용법: deploy.py <key> <date_label> <html_path> <passcode> [--commit-desc TEXT]
  key: 'YYYYMMDD'(일간) / 'WYYYYMMDD'(주간, 시작일) / 'MYYYYMM'(월간)
"""
import base64
import json
import os
import secrets
import sys
from datetime import datetime, timezone

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ITER = 100000


def encrypt(plaintext: str, passcode: str):
    salt = secrets.token_bytes(16)
    iv = secrets.token_bytes(12)
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=ITER)
    key = kdf.derive(passcode.encode("utf-8"))
    ct = AESGCM(key).encrypt(iv, plaintext.encode("utf-8"), None)
    b64 = lambda b: base64.b64encode(b).decode("ascii")
    return {
        "v": 1,
        "alg": "AES-GCM",
        "kdf": "PBKDF2-SHA256",
        "iter": ITER,
        "salt": b64(salt),
        "iv": b64(iv),
        "ct": b64(ct),
    }


def update_manifest(key, date_label):
    path = os.path.join(REPO, "manifest.json")
    m = json.load(open(path, encoding="utf-8"))
    reports = [r for r in m["reports"] if r["key"] != key]
    reports.append({"key": key, "date": date_label})

    def sort_key(r):
        k = r["key"]
        if k.startswith("W"):
            return (0, k)
        if k.startswith("M"):
            return (1, k)
        return (2, k)

    # day는 최신(큰 날짜)이 위로, week/month는 각각 최신 시작일이 위로 오도록 내림차순 재정렬
    days = sorted([r for r in reports if not r["key"].startswith(("W", "M"))], key=lambda r: r["key"], reverse=True)
    weeks = sorted([r for r in reports if r["key"].startswith("W")], key=lambda r: r["key"], reverse=True)
    months = sorted([r for r in reports if r["key"].startswith("M")], key=lambda r: r["key"], reverse=True)
    m["reports"] = weeks + months + days
    m["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.") + f"{datetime.now(timezone.utc).microsecond // 1000:03d}Z"
    json.dump(m, open(path, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"manifest.json 갱신: {key} ({date_label})")


if __name__ == "__main__":
    key, date_label, html_path, passcode = sys.argv[1:5]
    plaintext = open(html_path, encoding="utf-8").read()
    payload = encrypt(plaintext, passcode)
    payload["date"] = date_label
    payload["created"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.") + f"{datetime.now(timezone.utc).microsecond // 1000:03d}Z"
    out_path = os.path.join(REPO, f"{key}.json")
    json.dump(payload, open(out_path, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"{out_path} 생성 완료 ({len(plaintext)}자 평문 -> {len(payload['ct'])}자 암호문)")
    update_manifest(key, date_label)
