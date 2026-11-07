# 双项目展示站工程验收（2026-11-06）

执行：Codex；首版设计与文案：心舟草。对应 PR：
<https://github.com/Yixian-771/ai-chanyuan-workspace/pull/16>。

## 部署状态

**本地工程验收 PASS；公网部署 BLOCKED，尚未上线。**

GitHub 仓库元数据返回 `has_pages: false`；检查时 Actions `total_count: 0`。
现有首版工作流只在 `main` 推送时部署，既不能直接发布本待审核分支，
也不能使用默认 `GITHUB_TOKEN` 首次启用 Pages。
本次选择交接单优先的分支 `/docs` 发布方式，工作流改为 PR/分支自动验收。
站点本身仍是无运行依赖的 HTML/CSS，无埋点、登录、支付或私人凭据。

## 实际网址与访问测试

**无已验证可用的发布网址。** 2026-11-06 08:52（Asia/Seoul）从外部内容读取服务，
未提交登录凭据，实际请求候选地址
<https://yixian-771.github.io/ai-chanyuan-workspace/>，返回 **HTTP 404 / page_not_found**。
该地址仅为已测试但尚未生效的候选地址，不能标记为真实上线成果。
公开站点的手机/桌面浏览器验收仍待启用后执行，不能用本地结果替代。

专题原帖 `https://smcy.xyz/new/forum.php?mod=viewthread&tid=157849` 可打开，
但实际跳转到 `member.php?mod=logging&action=login`；本站“可能要求登录”的提示准确。
公开原文正文未独立复核，没有转载全文或将作者主张当作独立结论。
GitHub 工作间、八仙项目目录、任务 #13、英文 brief 和中英文传播包均已通过
GitHub 连接器读取核验可访问；摘要和 DRAFT 标记保留。

## 修改记录与版本

原始交接版本：`c44fc171611f860904c65604488cd769a6b4ab63`。
工程修订及本地验收版本：`fa4b3941ede3bbadf9a3c28bce79c641ef1b69d5`。

- 加深青绿色小字：修复自动检查发现的 3.86:1 / 4.04:1 对比度不足，保留首版配色和布局。
- 三页补相对路径 SVG favicon，消除浏览器默认 `/favicon.ico` 404。
- 为“跳至内容”补主内容焦点，标记混合段落的英文语言，尊重减少动画偏好。
- 加 `docs/.nojekyll`，使分支 Pages 直接按静态文件发布。
- 扩展无依赖检查：锚点、重复 ID、Pages 子路径、HTTPS 链接和新窗口安全。
- 新增可重复 Chromium 验收：本地 `/ai-chanyuan-workspace/` 路径和已发布网址使用同一套检查。
- 原工作流改为 PR/`main`/试点分支检查，上传 JSON 和六张截图；仅保留 `contents: read`。
- 新增发布/回退手册；没有合并主分支或改写远端历史。

## 验收记录

运行 `python3 scripts/check_site.py`：**PASS**。
运行浏览器脚本，使用 Chromium **155.0.8059.79**、Playwright **1.62.0**、
axe-core **4.11.0**，每个宽度使用新的无历史记录浏览器上下文。
实际 HTTP 服务挂载于 `/ai-chanyuan-workspace/`，首页目录、三个页面、CSS、图标
全部 HTTP 200；无失败请求、404 或页面脚本异常。完整机器记录见 [results.json](results.json)。

| 页面 | 窗口宽度 | 文档/正文宽度 | HTTP | 键盘跳转 | WCAG 自动违规 |
| --- | ---: | ---: | ---: | --- | ---: |
| index.html | 375 | 375 / 375 | 200 | PASS | 0 |
| eight.html | 375 | 375 / 375 | 200 | PASS | 0 |
| notice.html | 375 | 375 / 375 | 200 | PASS | 0 |
| index.html | 1366 | 1366 / 1366 | 200 | PASS | 0 |
| eight.html | 1366 | 1366 / 1366 | 200 | PASS | 0 |
| notice.html | 1366 | 1366 / 1366 | 200 | PASS | 0 |

- 实际点击每页主导航，三个页面切换正常，站内资源均按相对路径加载。
- 首页两条项目入口存在；八仙页四张“作品待展示”卡片与自由探索卡片保持区分，未虚构作品。
- 专题页中英文导读、来源、作者主张归属和“摘要不是全文译文”边界均存在且可读。
- 本地无 Cookie、表单、登录或支付入口；公开站点免登录访问仍待验证。
- 六张完整截图由工作流 `site-acceptance-<commit>` 附件留存。
  自动无障碍规则通过不代表完整人工无障碍认证；375px/1366px 为视口测试，并非真实手机系统测试。

## 尚需授权：唯一人工设置

由逸仙草打开 <https://github.com/Yixian-771/ai-chanyuan-workspace/settings/pages>，设置：

**Source = Deploy from a branch → Branch = `pilot-dual-project-20261106` → Folder = `/docs` → Save。**

GitHub 连接器没有 Pages 设置写入接口，当前执行环境对 Pages REST API 的请求被拒绝，
不能通过本会话完成首次启用。无需提供 Token，也不需要为此合并 PR。
启用后还须等待内置 Pages 构建成功、从设置页取得实际网址，再做公开站点验收并更新本 PR。

版本维护、复验命令及 `git revert` 回退步骤见 [PAGES_DEPLOYMENT.md](../../PAGES_DEPLOYMENT.md)。
本 PR 保持草稿，最终由心舟草核对文案与验收、逸仙草决定合并。
