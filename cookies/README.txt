把浏览器导出的 cookies.txt 放这里（Netscape 格式，制表符分隔），文件名对应期刊：
  te.txt    -> economist.com   （经济学人正文需要，订阅用户导出即可）
  ny.txt    -> newyorker.com
  time.txt  -> time.com

导出方法（任选）：
1) Chrome/Edge 装扩展 "Cookie-Editor" -> 打开目标站点 -> Export -> Netscape 格式保存；
2) 开发者工具 Console 里跑 copy(document.cookie) 只拿到非 HttpOnly 的部分，
   对 Cloudflare 的 cf_clearance 无效，所以推荐用扩展导出。

放好后直接跑 main.py 即可，程序会自动带上并按 3 次重试。
