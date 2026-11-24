# eMagzines 本地版

把 **The New Yorker / TIME**（以及可选的 **The Economist**）最新一期抓到本地，一次生成
**Markdown + PDF + EPUB + 封面 + 索引**，带**手动点击抓取**和**定时自动抓取**两套脚本。

> 当前配置：**只抓 The New Yorker 和 TIME**，经济学人已关闭（`config.yaml` 里
> `magazines.te.enabled: false`）。抓取代码仍然完整保留，改回 `true` 即可恢复。

基于 [plsy1/emagzines](https://github.com/plsy1/emagzines)（原版用 GitHub Actions + Calibre
把期刊发到 Release）改造而来：去掉云端依赖，改成 Windows 上双击就能用、全本地落盘、
并且补上了原版没有的 Markdown 输出与计划任务管理。

---

## 一分钟上手

> 最省事：双击根目录的 **`启动菜单.bat`**，所有功能都在一个菜单里。

1. 装依赖（只需一次，双击也行）：

   ```bat
   scripts\安装依赖.bat
   ```

   或者手动：`pip install -r requirements.txt`

2. 抓取：双击 **`scripts\立即抓取.bat`** → 选 `1`（三种都抓）。

3. 看产物：`library\` 目录，或直接打开 `library\INDEX.md`。

4. 想让它每天自动跑：双击 **`scripts\设置定时任务.bat`**，回车用默认时间（08:30）或输入 `07:30`。
   之后随时双击 **`scripts\查看定时任务.bat`** 看状态，**`scripts\删除定时任务.bat`** 取消。

---

## 产物长什么样

```
library/
├─ INDEX.md                                    ← 全部期号总索引（自动生成）
├─ the-economist/
│  └─ 2026-11-19/
│     ├─ the-economist-2026-11-19.md           ← 整期 Markdown（带 front-matter + 目录）
│     ├─ the-economist-2026-11-19.pdf          ← 排版好的 PDF
│     ├─ the-economist-2026-11-19.epub         ← EPUB3，可丢进 Kindle/Apple Books
│     ├─ cover.jpg                             ← 封面（抓不到就用排版生成的封面）
│     ├─ meta.json                             ← 期号/篇目/文件清单，供索引与二次开发用
│     └─ articles/                             ← 每篇文章单独的 .md（方便丢进 Obsidian）
├─ the-new-yorker/2026-11-30/…
└─ time/2026-11-24/…
```

日志在 `logs\emagzines-YYYYMMDD.log`。

---

## 脚本清单

| 脚本 | 作用 |
| --- | --- |
| `启动菜单.bat` | 根目录总菜单：抓取 / 设置定时 / 查看定时 / 删除定时 / 装依赖 / 打开产物。 |
| `scripts\立即抓取.bat` | **手动点击抓取**。菜单里可选：三种都抓 / 只抓某一本 / 不出 PDF。跑完自动打开产物目录。 |
| `scripts\设置定时任务.bat` | **设置定时任务**。注册 Windows 计划任务 `eMagzines-Daily`，每天固定时间静默抓一次。 |
| `scripts\查看定时任务.bat` | **查看定时任务**。任务状态、上次运行结果、下次运行时间、本地库概况、最近 20 行日志。 |
| `scripts\删除定时任务.bat` | 取消定时任务。 |
| `scripts\安装依赖.bat` | 装 `requirements.txt`。 |
| `scripts\setup_cron.sh` / `view_cron.sh` / `remove_cron.sh` | Linux / macOS 的等价物（crontab）。 |

底层两个 PowerShell 脚本也可以直接用：

```powershell
# 手动抓取，只要经济学人和纽约客，不生成 PDF
powershell -File scripts\run_fetch.ps1 -Only te,ny -NoPdf

# 指定期号（能取到就用）
powershell -File scripts\run_fetch.ps1 -Only te -Date 2026-11-19

# 注册/查看/删除计划任务
powershell -File scripts\setup_task.ps1 -Time 07:30
powershell -File scripts\status_task.ps1
powershell -File scripts\remove_task.ps1
```

---

## 命令行（`main.py`）

```bat
python main.py                    :: 三种期刊最新一期
python main.py --only te          :: 只抓 The Economist
python main.py --only te,time     :: 抓两本
python main.py --date 2026-11-19  :: 指定期号
python main.py --limit 10         :: 每期最多 10 篇
python main.py --no-pdf           :: 只出 md + epub
python main.py --index            :: 只重建 INDEX.md
python main.py --list             :: 看本地库现有内容
python main.py --open             :: 跑完打开产物目录
python main.py --scheduled        :: 定时模式（日志只写文件）
```

---

## 配置 `config.yaml`

```yaml
global:
  max_articles: 25        # 每期最多收录多少篇
  pdf_engine: auto        # auto：有 Calibre 用 Calibre，没有就用 Chrome/Edge 无头打印
  per_article_md: true    # 额外输出 articles/*.md
  inline_images: false    # 正文插图是否塞进 EPUB/PDF

magazines:
  te:   { enabled: false, feed: "https://www.economist.com/latest/rss.xml", reader_proxy: "" }   # 已按要求关闭
  ny:   { enabled: true, feed: "https://www.newyorker.com/feed/magazine/rss" }
  time: { enabled: true, feed: "https://time.com/feed/" }

schedule:
  daily_time: "08:30"     # 定时任务默认时间
  task_name: "eMagzines-Daily"
```

> 当前只抓 **The New Yorker** 和 **TIME**。经济学人已用 `enabled: false` 关掉，
> `main.py`、定时任务、菜单都会自动跳过它；想恢复把它改回 `true` 即可。

「最新一期」怎么判定：

- **The Economist**：拿 `latest` + `the-world-this-week` 两个官方 RSS，按链接里的日期分组，
  在最近 8 天里挑「覆盖栏目最全、篇数最多」的那天作为本期正刊（特刊如 *The world ahead*
  只覆盖少数栏目，不会被误当成一期）。
- **The New Yorker**：杂志 RSS 的频道标题本身就写着期号（如 `November 30 & December 7, 2026`），
  再按 `/magazine/2026/11/30/…` 的日期取本期文章。
- **TIME**：RSS 直接给全文，按期号日期取最新 N 篇。

---

## 全文能拿到多少？（重要）

| 期刊 | 默认效果 | 说明 |
| --- | --- | --- |
| TIME | **全文** | RSS 的 `content:encoded` 就是完整正文，最稳。 |
| The New Yorker | **全文** | 逐篇抓文章页再抽正文，实测整期可用。个别订阅专属文章会退化成摘要并在 md 里标注。 |
| The Economist | **摘要 + 完整目录** | economist.com 的文章页有 Cloudflare 人机校验，且正文是订阅墙。无 cookie 时只能拿到 RSS 摘要。 |

想让经济学人也拿到全文，二选一：

1. **带订阅身份的 cookies**（推荐，订阅用户适用）
   用浏览器插件（Cookie-Editor 之类）把 `economist.com` 的 cookies 导出成 Netscape 格式，
   存成 `cookies/te.txt`，脚本会自动带上并重试。
2. **阅读器代理**
   在 `config.yaml` 里给 `te` 配 `reader_proxy`（例如你自己部署的 `https://r.jina.ai/`），
   直连被拒时脚本会走 `reader_proxy + 原始URL`。

两种都没配时，程序不会报错退出，而是把该期做成「完整目录 + 每篇摘要」，
并在 README 同级的 md 里明确标注 `（摘要）`。

---

## PDF 是怎么生成

1. 有 [Calibre](https://calibre-ebook.com/) → 用 `ebook-convert` 把 EPUB 转 PDF（排版最稳）。
2. 没有 Calibre → 用本机 Chrome / Edge 的无头模式打印（`--print-to-pdf`），零额外安装。
   实测 Windows 自带 Edge 就够用，A4、带封面页和目录页。

脚本会自动探测两条路径，`pdf_engine` 可强制指定 `calibre` 或 `chromium`。

---

## 和上游的差别

| | 上游 plsy1/emagzines | 本项目 |
| --- | --- | --- |
| 运行位置 | GitHub Actions（需 fork + Token + WARP） | 本机，双击即用 |
| 抓取引擎 | 只用 Calibre recipe | RSS + 正文抽取为主，Calibre 可选 |
| 产物 | PDF / EPUB | **PDF / EPUB / Markdown / 封面 / meta.json / 总索引** |
| 定时 | Actions cron | **Windows 计划任务（一键设置/查看/删除）+ cron** |
| 分发 | GitHub Release | 本地 `library/` 目录 |
| 经济学人 | 依赖 recipe | RSS 定刊期，支持 cookies / reader_proxy 补全文 |

原版的 `.github/workflows` 与 Calibre recipe 用法仍可参考上游仓库；本项目 LICENSE 沿用上游。

---

## 常见问题

**Q：双击 bat 一闪就没了？**
在 `scripts\` 目录里按住 Shift 右键 → 「在此处打开 PowerShell 窗口」，运行
`powershell -File run_fetch.ps1` 看完整报错。

**Q：提示没有 Python？**
装 Python 3.10+，安装时勾选 *Add python.exe to PATH*。

**Q：PDF 生成失败？**
看 `logs\` 里的日志。若机器上既没有 Calibre 也没有 Chrome/Edge，会保留
`*.print.html`，用浏览器打开后 Ctrl+P 存成 PDF 即可。

**Q：定时任务没跑？**
双击 `scripts\查看定时任务.bat`：`状态` 应为 `Ready`，`上次结果` 为 `0` 表示成功。
任务只在当前用户登录时运行（不需要管理员权限）；想开机即跑请在「任务计划程序」里改触发器。

**Q：想换抓取时间？**
重新双击 `scripts\设置定时任务.bat` 输入新时间即可（同名任务会被覆盖）。

**Q：`scripts\*.ps1` 里的中文乱码 / 报语法错误？**
Windows PowerShell 5.1 读无 BOM 的 .ps1 会按 GBK 解码。每个 .bat 启动前都会静默运行
`python scripts/_bootstrap.py` 自动补 BOM；如果你自己改过 ps1，用 VSCode 另存为
「UTF-8 with BOM」即可，或手动执行一次 `python scripts\_bootstrap.py`。

---

## 目录结构

```
emagzines/
├─ main.py                 命令行入口
├─ config.yaml             全部可调项
├─ requirements.txt
├─ mags/                   三种期刊各自的抓取逻辑
│  ├─ base.py              RSS 解析、正文抽取、刊期判定
│  ├─ economist.py
│  ├─ newyorker.py
│  └─ time.py
├─ lib/
│  ├─ epub.py              零依赖 EPUB3 生成器
│  ├─ pdf.py               Calibre / Chrome 双引擎 PDF
│  ├─ pipeline.py          落盘：md / epub / pdf / meta
│  ├─ index.py             INDEX.md 索引
│  ├─ cover.py             封面下载 / 排版生成
│  ├─ http.py              会话、重试、cookies
│  ├─ textutil.py          HTML→Markdown、正文清洗
│  ├─ config.py, log.py
├─ scripts/                bat + ps1 + sh
├─ cookies/                （可选）放导出的 cookies.txt
├─ library/                产物
└─ logs/                   日志
```

---

## 说明

仅用于个人学习与技术研究。抓取、存储、传播请自行遵守目标站点的条款与当地版权法规；
订阅内容请使用自己的合法订阅身份访问。
