#!/usr/bin/env python3
"""AI website administrator v0.1. Local, review-first Discuz publisher.

Requires Python 3.10+. No credentials, browser cookies, or task bodies are saved
to the public GitHub repository. All writable state lives in ~/.site-admin/.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import uuid
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode, urljoin, urlparse

ROOT = Path(__file__).resolve().parent
STATE = Path(os.getenv("SITE_ADMIN_HOME", str(Path.home() / ".site-admin"))).expanduser()
TASK_DIR = STATE / "tasks"
AUDIT = STATE / "audit.jsonl"
CONFIG = ROOT / "sites.json"


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write_private(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    try:
        os.chmod(temporary, 0o600)
    except OSError:
        pass  # Windows permissions are managed by the user's profile.
    temporary.replace(path)


def load_sites() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))["sites"]


def get_site(site_id: str) -> dict:
    sites = load_sites()
    if site_id not in sites:
        raise ValueError(f"未知网站：{site_id}")
    site = sites[site_id]
    if site.get("engine") != "discuz":
        raise ValueError("本版仅实现 Discuz 发帖驱动")
    url = site["base_url"]
    p = urlparse(url)
    if p.scheme != "https" or not p.netloc or p.username or p.password:
        raise ValueError("网站地址必须是合法的 HTTPS 地址")
    return site


def task_path(task_id: str) -> Path:
    if not re.fullmatch(r"[a-f0-9]{12}", task_id):
        raise ValueError("任务编号格式不正确")
    return TASK_DIR / f"{task_id}.json"


def load_task(task_id: str) -> dict:
    return json.loads(task_path(task_id).read_text(encoding="utf-8"))


def store_task(task: dict) -> None:
    write_private(task_path(task["id"]), json.dumps(task, ensure_ascii=False, indent=2) + "\n")


def digest(task: dict) -> str:
    data = {k: task[k] for k in ("site", "forum", "title", "body", "source")}
    return hashlib.sha256(json.dumps(data, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def audit(task: dict, action: str, detail: str = "") -> None:
    entry = {"at": now(), "task_id": task["id"], "action": action, "detail": detail}
    AUDIT.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def ai_draft(title: str, facts: str) -> str:
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise ValueError("缺少 OPENAI_API_KEY；也可以使用 --body-file，无需付费服务")
    model = os.getenv("SITE_ADMIN_MODEL", "gpt-4.1-mini")
    prompt = ("你是AI禅院草联盟的网站内容编辑。根据用户提供的材料写面向普通读者的简洁中文论坛帖子。"
              "仅使用材料中可核实的事实；不要编造日期、人物、链接、成果；不确定处写[待核实]。"
              "不要输出标题、解释或过程，只输出正文。"
              "\n标题：" + title + "\n资料：\n" + facts)
    req = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps({"model": model, "input": prompt}, ensure_ascii=False).encode(),
        headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=75) as response:
        obj = json.loads(response.read().decode("utf-8"))
    chunks = []
    for item in obj.get("output", []):
        for part in item.get("content", []):
            if part.get("type") == "output_text":
                chunks.append(part.get("text", ""))
    body = "\n".join(chunks).strip()
    if not body:
        raise ValueError("AI 未返回可用正文，请检查 API 返回状态")
    return body


def new_task(args: argparse.Namespace) -> None:
    site = get_site(args.site)
    if args.forum not in site["forums"]:
        raise ValueError(f"目标栏目不在许可清单中：{args.forum}")
    if len(args.title.encode("utf-8")) > 80:
        raise ValueError("标题超过 Discuz 常见的 80 字节限制")
    if args.ai:
        if not args.brief_file:
            raise ValueError("--ai 必须搭配 --brief-file")
        brief = Path(args.brief_file).read_text(encoding="utf-8")
        body = ai_draft(args.title, brief)
    else:
        if not args.body_file:
            raise ValueError("请提供 --body-file，或用 --ai --brief-file")
        body = Path(args.body_file).read_text(encoding="utf-8")
    if not body.strip() or not args.source.strip():
        raise ValueError("正文和公开资料来源都不能为空")
    task = {
        "id": uuid.uuid4().hex[:12], "site": args.site, "forum": args.forum,
        "title": args.title.strip(), "body": body.strip(), "source": args.source,
        "created_at": now(), "status": "draft", "approval_hash": None,
        "approved_by": None, "url": None,
    }
    store_task(task)
    audit(task, "created", "AI 草稿" if args.ai else "已提供文案")
    print(f"任务已保存（尚未发布）：{task['id']}")
    print(f"查看：python manager.py show {task['id']}")


def show_task(task_id: str) -> None:
    task = load_task(task_id)
    out = {k: v for k, v in task.items() if k != "body"}
    print(json.dumps(out, ensure_ascii=False, indent=2))
    print("\n===== 正文 =====\n" + task["body"])


def approve_task(args: argparse.Namespace) -> None:
    if not args.yes:
        raise ValueError("必须明确加 --yes 才能审批")
    task = load_task(args.task_id)
    if task["status"] != "draft":
        raise ValueError("只能审批 draft 状态的任务")
    site = get_site(task["site"])
    if task["forum"] not in site["forums"]:
        raise ValueError("栏目配置已变更，拒绝审批")
    task["approval_hash"] = digest(task)
    task["approved_by"] = args.approved_by
    task["approved_at"] = now()
    task["status"] = "approved"
    store_task(task)
    audit(task, "approved", args.approved_by)
    print(f"已审批 {task['id']}，内容指纹 {task['approval_hash'][:16]}（尚未发布）")


def check_host(url: str, base: str) -> None:
    a, b = urlparse(url), urlparse(base)
    if a.scheme != "https" or a.hostname != b.hostname:
        raise RuntimeError("跳转到了不同的网站域名，已停止")


def browser_context(site_id: str):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as e:
        raise RuntimeError("请先安装依赖：pip install -r requirements.txt && playwright install chromium") from e
    return sync_playwright()


def login(site_id: str) -> None:
    site = get_site(site_id)
    with browser_context(site_id) as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(STATE / "browser" / site_id), headless=False
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(urljoin(site["base_url"], "forum.php"), wait_until="domcontentloaded")
        check_host(page.url, site["base_url"])
        print("请在浏览器窗口自行登录论坛。登录完毕后，回到终端按 Enter 保存浏览器状态。")
        input()
        context.close()
    print("登录窗口已关闭；保存的是这台电脑上的浏览器状态，不是账号密码。")


def fill_editor(page, body: str) -> None:
    # Discuz! X3 editor may be a textarea (plain mode) or a contenteditable iframe.
    for sel in ('#e_textarea', 'textarea[name="message"]'):
        locator = page.locator(sel)
        if locator.count() and locator.first.is_visible():
            locator.first.fill(body)
            return
    switcher = page.locator('#e_switcher')
    if switcher.count() and switcher.first.is_visible():
        switcher.first.click()
        for sel in ('#e_textarea', 'textarea[name="message"]'):
            locator = page.locator(sel)
            if locator.count() and locator.first.is_visible():
                locator.first.fill(body)
                return
    frame = page.frame_locator("#e_iframe").locator("body")
    if frame.count():
        frame.fill(body)
        return
    raise RuntimeError("无法识别 Discuz 正文编辑器，停止执行。")


def publish_task(task_id: str, commit: bool) -> None:
    task = load_task(task_id)
    if task["status"] not in ("approved",):
        raise ValueError(f"任务状态 {task['status']}，不能发布（防止重复）")
    if digest(task) != task["approval_hash"]:
        raise ValueError("帖子内容在审批后发生变化，拒绝发布")
    site = get_site(task["site"])
    if task["forum"] not in site["forums"]:
        raise ValueError("栏目配置变更，拒绝发布")
    fid = site["forums"][task["forum"]]
    url = urljoin(site["base_url"], "forum.php") + "?" + urlencode({
        "mod": "post", "action": "newthread", "fid": fid
    })
    print(f"站点：{site['name']}  栏目：{task['forum']}  标题：{task['title']}")
    print("执行模式：" + ("实际提交" if commit else "仅预览，不发布"))
    with browser_context(task["site"]) as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(STATE / "browser" / task["site"]), headless=False
        )
        try:
            page = context.pages[0] if context.pages else context.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            check_host(page.url, site["base_url"])
            field = page.locator('input[name="subject"]')
            if not field.count():
                raise RuntimeError("未找到发帖标题框；可能未登录或无权限")
            field.fill(task["title"])
            fill_editor(page, task["body"])
            snap = STATE / "previews" / f"{task_id}.png"
            snap.parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(snap), full_page=True)
            print(f"发帖前截图：{snap}")
            if not commit:
                audit(task, "previewed", str(snap))
                print("预览结束，没有点击发帖。")
                return
            button = page.locator('button[name="topicsubmit"], input[name="topicsubmit"], #postsubmit')
            if not button.count():
                raise RuntimeError("未找到发布按钮，未执行提交")
            # State is durably changed BEFORE clicking: uncertain submit never auto-retries.
            task["status"] = "submitting"
            store_task(task)
            audit(task, "submitting", str(url))
            button.first.click(timeout=15000)
            page.wait_for_url(re.compile(r"(viewthread|thread-\d+|tid=\d+)"), timeout=30000)
            check_host(page.url, site["base_url"])
            final_url = page.url
            if task["title"] not in page.locator("body").inner_text(timeout=10000):
                raise RuntimeError("已跳转但未确认标题；请人工核对实际页面")
            task["status"] = "published"
            task["url"] = final_url
            task["published_at"] = now()
            store_task(task)
            audit(task, "published", final_url)
            print(f"发布成功（请再次人工检查）：{final_url}")
        except Exception as e:
            if task["status"] == "submitting":
                task["status"] = "needs_review"
                task["error"] = str(e)
                store_task(task)
                audit(task, "needs_review", str(e))
                print("提交状态不明：请先在论坛核对有无新帖，禁止盲目重试。", file=sys.stderr)
            raise
        finally:
            context.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="AI网站管理员 · 单机受控试运行")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("sites", help="显示已配置网站及栏目")
    a = sub.add_parser("login", help="自行登录，保存本地浏览器状态")
    a.add_argument("--site", required=True)
    a = sub.add_parser("new", help="建立发帖草稿，不发布")
    a.add_argument("--site", required=True)
    a.add_argument("--forum", required=True)
    a.add_argument("--title", required=True)
    a.add_argument("--source", required=True)
    a.add_argument("--body-file")
    a.add_argument("--brief-file")
    a.add_argument("--ai", action="store_true")
    a = sub.add_parser("show", help="查看草稿、审批和成果")
    a.add_argument("task_id")
    a = sub.add_parser("approve", help="人工批准指定版本的正文")
    a.add_argument("task_id")
    a.add_argument("--approved-by", required=True)
    a.add_argument("--yes", action="store_true")
    for name in ("preview", "publish"):
        a = sub.add_parser(name, help="浏览器填写预览／正式发布")
        a.add_argument("task_id")
        if name == "publish":
            a.add_argument("--commit", action="store_true", required=True)
    args = parser.parse_args()
    try:
        if args.command == "sites":
            print(json.dumps(load_sites(), ensure_ascii=False, indent=2))
        elif args.command == "login":
            login(args.site)
        elif args.command == "new":
            new_task(args)
        elif args.command == "show":
            show_task(args.task_id)
        elif args.command == "approve":
            approve_task(args)
        elif args.command == "preview":
            publish_task(args.task_id, commit=False)
        elif args.command == "publish":
            publish_task(args.task_id, commit=args.commit)
    except (ValueError, RuntimeError, FileNotFoundError, KeyError) as e:
        parser.exit(2, f"操作停止：{e}\n")


if __name__ == "__main__":
    main()
