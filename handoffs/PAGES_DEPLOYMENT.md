# 双项目静态站：最小发布与回退

本方案使用 GitHub Pages 自带的 **Deploy from a branch**，直接发布 `docs/`；
无需后端、付费托管、私人 Token 或仓库 Secret。GitHub 自带的 Pages 构建负责发布，
`.github/workflows/deploy-pages.yml` 负责静态检查、375px/1366px 浏览器检查和验收附件。

## 首次启用：唯一需要所有者操作的设置

打开 <https://github.com/Yixian-771/ai-chanyuan-workspace/settings/pages>：

**Build and deployment → Source: Deploy from a branch → Branch:
`pilot-dual-project-20261106` → Folder: `/docs` → Save。**

这一步会公开该分支 `docs/` 下的内容，并触发 GitHub 自带的 `pages build and deployment`。
不需要合并 PR #16，也不要为此添加私人凭据。
当前发布分支应保留；待心舟审核、逸仙决定合并后，再将同一设置的分支切为 `main`，
继续发布 `/docs`。

## 发布后验证

1. 等待仓库 Actions 中 GitHub 自带的 Pages 构建成功，从 **Settings → Pages**
   复制实际显示的访问网址。构建成功和网址存在不能代替实际访问测试。
2. 用未登录的浏览器打开首页、`eight.html`、`notice.html`；确认 CSS 和图标正常。
3. 使用该实际网址复用同一浏览器检查（需要 Playwright 和 Chromium）：

   ```sh
   python3 scripts/check_site_browser.py --base-url '实际网址/' --output-dir work/public-site-check
   ```

4. 将实际网址、Pages 构建链接、发布 commit、HTTP 状态和 375px/1366px 结果补充到 PR #16。
   未通过前保持 `BLOCKED`，不要将标准格式的候选地址当作已上线地址。

## 日常检查

最小检查无依赖：

```sh
python3 scripts/check_site.py
```

完整本地验收（检查工具不属于网站运行依赖）：

```sh
python3 -m pip install playwright==1.62.0
python3 -m playwright install chromium
npm install --prefix work/a11y --no-package-lock --no-save axe-core@4.11.0
python3 scripts/check_site_browser.py --axe-path work/a11y/node_modules/axe-core/axe.min.js
```

若已有系统 Chromium，可增加 `--browser-executable /usr/bin/chromium`。
脚本默认在 `/ai-chanyuan-workspace/` 子路径下启动本地 HTTP 服务，使用新的浏览器上下文，
检查三页、资源响应、全部站内导航、键盘跳转和横向溢出，输出 JSON 和六张完整截图。
指定 axe 后同时检查 WCAG 2.0/2.1 A/AA 自动规则；自动检查不能代替人工无障碍审阅。

## 版本与回退

- 心舟原始交接版本：`c44fc171611f860904c65604488cd769a6b4ab63`。
- 本次小修、工作流和验收证据都通过 PR #16 的提交追踪，不改写主分支历史。
- Pages 启用后，同一发布分支每次提交会自动重新发布 `docs/`。
- 回退网页：在独立分支对不合适的网站提交执行 `git revert <commit>`，通过 PR 审核后
  更新当前发布分支，等待 Pages 重建并重新访问验证。不要 force-push 或硬重置发布分支。
- 紧急停止公开：由所有者在同一 **Settings → Pages** 页面执行 **Unpublish site**。
