# API 配置说明

本项目的 API Key 只填写在服务器的 `backend/.env` 中，绝不能写进 Vue 前端、Git 仓库、截图、Word 文档或聊天记录。

## 1. 创建本地配置

```powershell
Copy-Item backend/.env.example backend/.env
```

将 `backend/.env` 中下列空值填为自己的 Key：

```text
DEEPSEEK_API_KEY=
MINIMAX_API_KEY=
HIHOO_API_KEY=
HIHOO_SIGN_SK=
```

`backend/.env` 已被 Git 忽略。若 Key 曾被提交或发送，请立刻在供应商平台删除并新建 Key。

## 2. 文案改写：DeepSeek

- 来源：[DeepSeek 开放平台 API Keys](https://platform.deepseek.com/api_keys)。
- 配置：`DEEPSEEK_API_KEY`，默认地址为 `https://api.deepseek.com`，默认模型为 `deepseek-chat`。
- 用法：用户粘贴原文或字幕，后端调用 `chat/completions` 生成口播改写稿。
- 注意：DeepSeek 不负责解析抖音分享链接，因此不要把链接当作文案提交。

## 3. 声音克隆与配音：MiniMax

- 来源：[MiniMax API Key 管理](https://platform.minimax.io/user-center/basic-information/interface-key)。
- 配置：`MINIMAX_API_KEY`，默认地址为 `https://api.minimax.io/v1`，默认模型为 `speech-2.8-hd`。
- 本项目调用 MiniMax 的 `voice_clone` 和 `t2a_v2` 接口。声音克隆仅限本人声音或已取得明确授权的声音。
- 官方约束：克隆源音频应为 MP3/M4A/WAV，至少 10 秒、不超过 5 分钟、文件不大于 20 MB；克隆后未使用的音色可能被供应商清理。以 MiniMax 控制台与最新官方文档为准。

## 4. 数字人对口型：HiHoo

- 来源：HiHoo/创客服务商后台提供的 API 资料和 Key。
- 配置：`HIHOO_API_KEY`；如账户要求签名，再填写 `HIHOO_SIGN_SK` 并设置 `HIHOO_ENABLE_SIGN=true`。
- 正式环境还必须设置 `PUBLIC_BASE_URL` 和 S3 兼容对象存储配置，确保音频、视频能被 HiHoo 以公网 HTTPS 地址访问。

## 5. 上线前检查

```text
DJANGO_DEBUG=false
ALLOW_PROVIDER_MOCKS=false
ALLOW_ANONYMOUS_AUTH=false
DJANGO_SECRET_KEY=<随机长密钥>
DJANGO_ALLOWED_HOSTS=<真实域名>
PUBLIC_BASE_URL=https://<真实域名>
MEDIA_STORAGE_BACKEND=object
```

不要使用本机磁盘或临时隧道作为生产媒体存储。对象存储访问密钥同样只应放在服务器环境变量或 `backend/.env` 中。
