# AI 口播视频创作（手机端 MVP）

一个面向手机浏览器的 AI 口播视频创作 MVP：粘贴原文或字幕，经 DeepSeek 改写，使用 MiniMax 克隆/合成语音，再调用 HiHoo 生成数字人对口型视频。

## 功能边界

- 文案改写：DeepSeek 直连。
- 声音克隆与配音：MiniMax 直连，密钥仅保存在 Django 后端。
- 数字人对口型：HiHoo 直连。
- 抖音链接不会被自动解析。请粘贴视频原文或字幕，这是为了避免依赖未经授权且不稳定的网页提取能力。

## 本地启动

```powershell
Copy-Item backend/.env.example backend/.env
# 编辑 backend/.env，填写 API Key
.\.venv\Scripts\python.exe backend\manage.py migrate
.\.venv\Scripts\python.exe backend\manage.py runserver

cd frontend
npm install
npm run dev
```

详细变量、API 来源和上线安全要求请见 [API 配置说明](docs/API配置.md)。

## 安全与许可

- 不要提交 `backend/.env`、数据库、媒体文件或生产日志；根目录 `.gitignore` 已排除它们。
- 前端不得写入或调用任何第三方 API Key，所有供应商请求由后端发起。
- 正式上线必须关闭 `DJANGO_DEBUG`、关闭匿名登录、配置 HTTPS 对象存储，并更换 `DJANGO_SECRET_KEY`。
- 本项目采用 PolyForm Noncommercial License 1.0.0，仅限非商业用途。详见 [LICENSE.md](LICENSE.md)。

## 验证

```powershell
.\.venv\Scripts\python.exe backend\manage.py test apps.creator apps.accounts
cd frontend; npm run build
```
