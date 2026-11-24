# AI网站管理员 · 第一版（试运行）

目标：让 AI 负责准备文章、协助审核，得到明确授权后在网站发布，记录真实链接；以后增加多个网站与定期维护。**当前版本是命令行试运行程序，不是已经部署的后台服务。**

## 已接入的网站

- 生命禅院论坛（Discuz! X3.5），网站编号 `lifecosmos-bbs`
- 栏目「八仙过海各显神通」：fid=426
- 栏目「专题事件」：fid=427

对应关系已从公开页面核对。其他网站只需在 `sites.json` 添加配置并实现对应网站驱动；**目前仅 Discuz 发帖驱动**。

## 在 Windows 上开始

需要 Python 3.10+、终端以及网站发帖账号。**不要把密码、Cookie、账号截图、私人帖子放进公开 GitHub。**

```powershell
cd projects\site-admin
python -m pip install -r requirements.txt
python -m playwright install chromium
python manager.py sites
python manager.py login --site lifecosmos-bbs
```

`login` 会打开专用浏览器，请你在窗口内自己登录，然后回到终端按 Enter；浏览器登录状态仅保存在**当前电脑的用户目录** `~/.site-admin/browser/`，不会自动同步到 GitHub。建议创建独立、权限最小的论坛发帖账号。

## 第一条任务（写好文案交给管理员）

新建本地文件 `first-post.txt`，内容写帖子正文：

```powershell
python manager.py new --site lifecosmos-bbs --forum "八仙过海各显神通" --title "欢迎来到AI禅院草八仙神通馆" --body-file first-post.txt --source "经人工确认的公开项目介绍"
```

程序返回任务编号（比如 `xxxxxx`），然后依次：

```powershell
python manager.py show xxxxxx
python manager.py preview xxxxxx
python manager.py approve xxxxxx --approved-by "逸仙草" --yes
python manager.py publish xxxxxx --commit
python manager.py show xxxxxx
```

- `preview` 只填表、截屏、**绝不点击发布**，可先检查 Discuz 当前编辑器是否适配。
- `approve` 是显式审批，程序给内容算 SHA256 指纹；审批后任何内容改动都不会被发布。
- `publish --commit` 才会真正提交，验证页面是否打开了新主题，再记录链接。
- 一旦提交结果不明确，会进入 `needs_review`，**不会自动重试**，防止重复发帖。

## 可选：让AI自己拟稿

`--brief-file` 提供事实资料，`--ai` 调用 OpenAI API 拟稿：

```powershell
$env:OPENAI_API_KEY = "仅在本机设置，不要提交或转发"
python manager.py new --site lifecosmos-bbs --forum "专题事件" --title "本周专题进展" --brief-file .\brief.txt --ai --source "已核实的公开原始资料"
```

这一步是**可选并可能额外收费**；没有 API Key 时仍能用已写好的文案。AI 输出一律是待审草稿，不能跳过人类审批。将来可换成其他模型或对接既有 AI 协作流程。

## 权限与事实边界

- 首版只有「新建主题」，不支持删帖、改站点设置、数据库、域名、支付或升级。
- 外部发布需核对事实与日期、个人隐私、目标栏目和技术预览，最终由人批准。
- GitHub 仓库是**公开仓库**。浏览器状态、帖子草稿、任务日志、API Key 默认留在本机 `~/.site-admin/`。
- CLI 的 `--approved-by` 是流程记录，不是强身份认证；用于单机受控试运行，不适合开放公网。
- 旧论坛可能采用不同主题编辑器。正式发帖前先 `preview`；如不匹配，暂停并调整选择器。
- 如果实际提交成功但网页验证失败，必须人工核对后再处理，不可重复执行。

## 后续验收

1. 使用有权限的专用账号完成本机登录；
2. `preview` 截图能正确显示标题、正文与栏目；
3. 人工确认内容后运行 `publish`，返回真实主题链接；
4. 在浏览器重新打开链接确认文本；
5. 新增第二个站点驱动，验证跨网站任务列表与审计记录。

负责人：仙儿决定方向和授权；心舟规划、审核交付；执行程序负责发布与保存证据。当前仅创建程序和配置，没有登录论坛或发布任何帖子。
